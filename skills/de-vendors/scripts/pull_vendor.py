#!/usr/bin/env python3
"""Pull official vendor skills into ONE project, pinned and scanned.

  pull_vendor.py list                         vendors in vendors.toml
  pull_vendor.py info VENDOR                  CLI / MCP install lines (printed, never run)
  pull_vendor.py skills VENDOR [--grep TEXT]  skills available at the pinned sha
  pull_vendor.py add VENDOR SKILL... [--project DIR] [--accept-license]
  pull_vendor.py selftest

`add` fetches the repo at the pinned sha with git (no HTTP library), refuses symlinks and
binaries, runs `skill-scanner scan --fail-on-severity high` on every skill, then copies it to
DIR/.claude/skills/<name> and records it in DIR/.claude/de-vendors.lock.json.
Stdlib only. Never installs globally. Never runs a vendor's installer.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent.parent / "vendors.toml"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
BAD_EXT = {".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".jar", ".whl", ".zip", ".tar", ".gz",
           ".tgz", ".7z", ".rar", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf"}
OPEN_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0"}
SCANNER_HINT = "uv tool install cisco-ai-skill-scanner==2.3.2"


def manifest() -> dict:
    return tomllib.loads(MANIFEST.read_text())


def vendor(name: str) -> dict:
    v = manifest()["vendor"].get(name)
    if not v:
        sys.exit(f"unknown vendor {name!r}; run: pull_vendor.py list")
    return v


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def fetch(v: dict, work: Path) -> None:
    git("init", "-q", cwd=work)
    git("remote", "add", "origin", f"https://github.com/{v['repo']}.git", cwd=work)
    git("fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", v["sha"], cwd=work)


def skill_dirs(ls_tree: str, roots: list[str]) -> dict[str, str]:
    """Map skill name -> repo dir, for every <root>/**/<name>/SKILL.md."""
    found: dict[str, str] = {}
    for path in ls_tree.splitlines():
        if not path.endswith("/SKILL.md"):
            continue
        d = path.removesuffix("/SKILL.md")
        if ".." in d.split("/") or d.startswith("/"):
            continue
        if not any(d.startswith(r.rstrip("/") + "/") for r in roots):
            continue
        name = d.rsplit("/", 1)[-1]
        if not NAME.match(name):
            continue
        if name in found and found[name] != d:
            raise SystemExit(f"two skills named {name!r}: {found[name]} and {d}")
        found[name] = d
    return found


def unsafe_files(root: Path) -> list[str]:
    bad = []
    for p in root.rglob("*"):
        if p.is_symlink():
            bad.append(f"symlink {p.relative_to(root)}")
        elif p.is_file() and (p.suffix.lower() in BAD_EXT or b"\0" in p.read_bytes()[:8192]):
            bad.append(f"binary {p.relative_to(root)}")
    return bad


def merge_lock(lock: dict, name: str, entry: dict) -> dict:
    skills = dict(lock.get("skills", {}))
    skills[name] = entry
    return {"skills": dict(sorted(skills.items()))}


def cmd_add(args: argparse.Namespace) -> int:
    v = vendor(args.vendor)
    if v["license"] not in OPEN_LICENSES and not args.accept_license:
        sys.exit(f"{args.vendor}: license is {v['license']!r} (not a known open license). "
                 "Read the repo's terms, then re-run with --accept-license.")
    scanner = shutil.which("skill-scanner")
    if not scanner:
        sys.exit(f"skill-scanner not found. Install it pinned: {SCANNER_HINT}")
    project = Path(args.project).resolve()
    dest_root = project / ".claude" / "skills"
    lock_path = project / ".claude" / "de-vendors.lock.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {"skills": {}}

    with tempfile.TemporaryDirectory(prefix="de-vendors-") as tmp:
        work = Path(tmp)
        fetch(v, work)
        available = skill_dirs(git("ls-tree", "-r", "--name-only", "FETCH_HEAD", cwd=work), v["roots"])
        missing = [s for s in args.skill if s not in available]
        if missing:
            sys.exit(f"not in {args.vendor}@{v['sha'][:12]}: {missing}. Run: pull_vendor.py skills {args.vendor}")
        git("sparse-checkout", "set", "--no-cone", *[f"/{available[s]}/" for s in args.skill], cwd=work)
        git("checkout", "-q", "FETCH_HEAD", cwd=work)

        # Validate every skill before touching the project, so one failure installs nothing.
        for s in args.skill:
            src = work / available[s]
            dest = dest_root / s
            owner = lock["skills"].get(s, {}).get("vendor")
            if dest.exists() and owner != args.vendor:
                sys.exit(f"{dest} exists and is not a {args.vendor} skill from this lock; refusing to overwrite")
            bad = unsafe_files(src)
            if bad:
                sys.exit(f"{s}: refused, " + "; ".join(bad[:5]))
            scan = subprocess.run([scanner, "scan", str(src), "--use-behavioral", "--fail-on-severity", "high"],
                                  capture_output=True, text=True)
            if scan.returncode != 0:
                print(scan.stdout[-4000:], scan.stderr[-2000:], sep="\n")
                sys.exit(f"{s}: skill-scanner reported high/critical findings (exit {scan.returncode}); nothing installed")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        for s in args.skill:
            src, dest = work / available[s], dest_root / s
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            lock = merge_lock(lock, s, {"vendor": args.vendor, "repo": v["repo"], "sha": v["sha"],
                                        "path": available[s], "license": v["license"]})
            lock_path.write_text(json.dumps(lock, indent=2) + "\n")  # per skill: folder and lock never diverge
            print(f"installed {s} -> {dest.relative_to(project)}")
    print(f"lock: {lock_path.relative_to(project)}  (commit it with the skills)")
    print(f"tooling for {args.vendor} (review, then run yourself):\n  cli: {v.get('cli')}\n  mcp: {v.get('mcp')}")
    return 0


def cmd_skills(args: argparse.Namespace) -> int:
    v = vendor(args.vendor)
    with tempfile.TemporaryDirectory(prefix="de-vendors-") as tmp:
        work = Path(tmp)
        fetch(v, work)
        found = skill_dirs(git("ls-tree", "-r", "--name-only", "FETCH_HEAD", cwd=work), v["roots"])
    for name, d in sorted(found.items()):
        if not args.grep or args.grep.lower() in d.lower():
            print(f"{name:45} {d}")
    return 0


def selftest() -> int:
    tree = "skills/a/SKILL.md\nskills/a/ref.md\nskills/b/SKILL.md\nother/c/SKILL.md\nskills/../x/SKILL.md\n"
    assert skill_dirs(tree, ["skills"]) == {"a": "skills/a", "b": "skills/b"}, skill_dirs(tree, ["skills"])
    assert skill_dirs("plugins/p/skills/q/SKILL.md\n", ["plugins/p/skills/"]) == {"q": "plugins/p/skills/q"}
    try:
        skill_dirs("r1/a/SKILL.md\nr2/a/SKILL.md\n", ["r1", "r2"])
        raise AssertionError("duplicate names must fail")
    except SystemExit:
        pass
    lock = merge_lock({"skills": {"z": {"vendor": "v"}}}, "a", {"vendor": "w"})
    assert list(lock["skills"]) == ["a", "z"] and lock["skills"]["a"]["vendor"] == "w"
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "ok.md").write_text("text")
        assert unsafe_files(t) == []
        (t / "x.pyc").write_bytes(b"\0\1")
        (t / "link").symlink_to(t / "ok.md")
        assert len(unsafe_files(t)) == 2, unsafe_files(t)
    for name, v in manifest()["vendor"].items():
        assert re.fullmatch(r"[0-9a-f]{40}", v["sha"]), name
    print("selftest ok")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("info").add_argument("vendor")
    s = sub.add_parser("skills")
    s.add_argument("vendor")
    s.add_argument("--grep")
    a = sub.add_parser("add")
    a.add_argument("vendor")
    a.add_argument("skill", nargs="+")
    a.add_argument("--project", default=".")
    a.add_argument("--accept-license", action="store_true")
    sub.add_parser("selftest")
    args = p.parse_args()

    if args.cmd == "list":
        m = manifest()
        for name, v in m["vendor"].items():
            print(f"{name:16} {v['repo']:40} {v['sha'][:12]}  {v['license']}")
        print("\nMCP-only (no official skills):", ", ".join(m.get("mcp_only", {})))
        return 0
    if args.cmd == "info":
        m = manifest()
        if args.vendor in m.get("mcp_only", {}):
            print(m["mcp_only"][args.vendor])
            return 0
        v = vendor(args.vendor)
        print(f"cli: {v.get('cli')}\nmcp: {v.get('mcp')}")
        return 0
    return {"skills": cmd_skills, "add": cmd_add}.get(args.cmd, lambda _: selftest())(args)


if __name__ == "__main__":
    sys.exit(main())
