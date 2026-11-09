#!/usr/bin/env python3
"""Structural checks: skill/agent frontmatter, plugin manifest, CHANGELOG parity, vendor pins.

Usage: validate.py [ROOT]   (exit 1 on any finding)
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MODELS = {"haiku", "sonnet", "opus", "fable", "inherit"}


def frontmatter(path: Path) -> dict[str, str] | None:
    m = FRONTMATTER.match(path.read_text())
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        if line[:1].isspace() or ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip().strip("'\"")
    return out


def yaml_plain_scalar_errors(path: Path, rel: str) -> list[str]:
    """Stdlib stand-in for a YAML parser on the one mistake that bit us: a plain (unquoted)
    value containing ': ' or ' #' is invalid YAML, and skills.sh silently drops that skill."""
    m = FRONTMATTER.match(path.read_text())
    out = []
    for line in (m.group(1).splitlines() if m else []):
        if line[:1].isspace() or ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        if v[:1] in ("'", '"', "|", ">", "[", "{", ""):
            continue
        if ": " in v or v.endswith(":") or " #" in v:
            out.append(f"{rel}: '{k.strip()}' is a plain YAML scalar containing ': ' or ' #'; quote the value")
    return out


def check_doc(path: Path, expected: str, rel: str) -> list[str]:
    fm = frontmatter(path)
    if fm is None:
        return [f"{rel}: missing frontmatter"]
    out = yaml_plain_scalar_errors(path, rel)
    if fm.get("name") != expected:
        out.append(f"{rel}: name {fm.get('name')!r} != {expected!r}")
    if not NAME.match(expected):
        out.append(f"{rel}: name {expected!r} is not kebab-case")
    desc = fm.get("description", "")
    if not desc:
        out.append(f"{rel}: empty description")
    elif len(desc) > 1024:
        out.append(f"{rel}: description {len(desc)} chars > 1024")
    return out


def validate(root: Path) -> list[str]:
    errs: list[str] = []
    skills = sorted(d for d in (root / "skills").iterdir() if d.is_dir())
    if not skills:
        errs.append("skills/: no skills")
    for d in skills:
        f = d / "SKILL.md"
        if not f.exists():
            errs.append(f"skills/{d.name}: no SKILL.md")
            continue
        errs += check_doc(f, d.name, f"skills/{d.name}/SKILL.md")
        if len(f.read_text().splitlines()) > 200:
            errs.append(f"skills/{d.name}/SKILL.md: over 200 lines; move detail to references/")
        if not (d / "references" / "gotchas.md").exists():
            errs.append(f"skills/{d.name}: missing references/gotchas.md (feedback loop target)")

    for f in sorted((root / "agents").glob("*.md")):
        rel = f"agents/{f.name}"
        errs += check_doc(f, f.stem, rel)
        model = (frontmatter(f) or {}).get("model")
        if model not in MODELS:
            errs.append(f"{rel}: model {model!r} not pinned to one of {sorted(MODELS)}")

    try:
        mkt = json.loads((root / ".claude-plugin" / "marketplace.json").read_text())
        plugins = mkt["plugins"]
        assert mkt["name"] and mkt["owner"]["name"] and len(plugins) == 1
        plugin = plugins[0]
        if plugin.get("source") != "./":
            errs.append("marketplace.json: plugin source must be './' (one tree serves both channels)")
        heading = re.search(r"^## \[(\d+\.\d+\.\d+)\]", (root / "CHANGELOG.md").read_text(), re.M)
        if not heading or heading.group(1) != plugin.get("version"):
            errs.append(f"marketplace.json version {plugin.get('version')!r} != latest CHANGELOG release")
    except (OSError, KeyError, AssertionError, json.JSONDecodeError) as e:
        errs.append(f"marketplace.json: {type(e).__name__}: {e}")

    vt = root / "skills" / "de-vendors" / "vendors.toml"
    if vt.exists():
        for key, v in tomllib.loads(vt.read_text()).get("vendor", {}).items():
            where = f"vendors.toml [{key}]"
            if not REPO.match(v.get("repo", "")):
                errs.append(f"{where}: bad repo")
            if not SHA.match(v.get("sha", "")):
                errs.append(f"{where}: sha must be a full 40-char commit")
            if not v.get("license"):
                errs.append(f"{where}: license missing (use 'NONE' if the repo has none)")
            if not v.get("roots"):
                errs.append(f"{where}: roots missing")
    return errs


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    found = validate(root)
    for e in found:
        print(e)
    print(f"validate: {len(found)} finding(s)", file=sys.stderr)
    sys.exit(1 if found else 0)
