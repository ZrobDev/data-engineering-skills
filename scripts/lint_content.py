#!/usr/bin/env python3
"""Content lint: everything in this repo must be small, plain, reviewable text.

Rules exist because of real 2026 skill-poisoning techniques: pipe-to-shell
"prerequisites", base64 payloads, precompiled .pyc, instructions hidden in Office
files, and padding that pushes content past a scanner's window.

Usage: lint_content.py [ROOT]   (exit 1 on any finding)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

MAX_BYTES = 64 * 1024
MAX_LINES = 2000
MAX_LINE_LEN = 400
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
BAD_EXT = {
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin", ".o", ".a", ".class", ".jar", ".whl",
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp", ".rtf", ".pdf",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svgz",
}
PIPE_TO_SHELL = re.compile(r"\b(?:curl|wget|iwr|irm)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da|fi)?sh\b", re.I)
BASE64_BLOB = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")
URL = re.compile(r"https?://[^\s<>()\[\]{}\"'`]+", re.I)
NET_IMPORT = re.compile(
    r"^\s*(?:import|from)\s+(?:urllib|http|socket|requests|httpx|aiohttp|ftplib|smtplib|telnetlib)\b", re.M
)
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def allowlist(root: Path) -> set[str]:
    f = root / "scripts" / "url-allowlist.txt"
    lines = f.read_text().splitlines() if f.exists() else []
    return {ln.strip().lower() for ln in lines if ln.strip() and not ln.startswith("#")}


def host_ok(host: str, allowed: set[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == a or host.endswith("." + a) for a in allowed)


def tool_findings(rel: str, text: str) -> list[str]:
    m = FRONTMATTER.match(text)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        key, _, val = line.partition(":")
        key = key.strip()
        if key == "hooks":
            out.append(f"{rel}: frontmatter declares hooks")
        if key not in ("allowed-tools", "tools"):
            continue
        tokens = [t.strip().strip("'\"[]") for t in re.split(r",(?![^()]*\))|\s(?![^()]*\))", val)]
        if any(t.replace(" ", "") == "Bash(*)" for t in tokens):
            out.append(f"{rel}: {key} grants Bash(*)")
        if key == "allowed-tools" and "Bash" in tokens:
            out.append(f"{rel}: allowed-tools pre-approves bare Bash; scope it, e.g. Bash(git status:*)")
    return out


def lint(root: Path) -> list[str]:
    allowed = allowlist(root)
    findings: list[str] = []
    for p in sorted(root.rglob("*")):
        rel_parts = p.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            if p.name == "hooks":
                findings.append(f"{rel}: hooks/ directory (plugin hooks run code on install machines)")
            continue
        if p.name == "hooks.json":
            findings.append(f"{rel}: hooks.json")
        # Repo-level agent config runs hooks or injects instructions into any session opened in a
        # clone. settings.local.json is the gitignored per-user file, so a local run must not fire.
        if p.name == ".mcp.json" or (".claude" in rel_parts and p.name != "settings.local.json"):
            findings.append(f"{rel}: repo-level agent config (.claude/ or .mcp.json)")
        if p.suffix.lower() in BAD_EXT:
            findings.append(f"{rel}: binary/archive/office file type {p.suffix}")
            continue
        data = p.read_bytes()
        if len(data) > MAX_BYTES:
            findings.append(f"{rel}: {len(data)} bytes > {MAX_BYTES}")
        if b"\0" in data:
            findings.append(f"{rel}: NUL byte (binary content)")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(f"{rel}: not UTF-8 text")
            continue
        lines = text.splitlines()
        if len(lines) > MAX_LINES:
            findings.append(f"{rel}: {len(lines)} lines > {MAX_LINES}")
        for n, line in enumerate(lines, 1):
            if len(line) > MAX_LINE_LEN:
                findings.append(f"{rel}:{n}: line {len(line)} chars > {MAX_LINE_LEN}")
            if PIPE_TO_SHELL.search(line):
                findings.append(f"{rel}:{n}: download piped to a shell")
            if BASE64_BLOB.search(line):
                findings.append(f"{rel}:{n}: base64-like blob")
            for url in URL.findall(line):
                try:
                    host = urlsplit(url).hostname or ""  # parsed, so user@host and :port can't spoof it
                except ValueError:
                    host = ""
                if not host_ok(host, allowed):
                    findings.append(f"{rel}:{n}: URL host not in scripts/url-allowlist.txt: {host}")
        if p.suffix == ".md":
            findings += tool_findings(rel, text)
        if p.suffix == ".py" and rel.startswith("skills/") and NET_IMPORT.search(text):
            findings.append(f"{rel}: network module import in a skill script")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    found = lint(root)
    for f in found:
        print(f)
    print(f"lint_content: {len(found)} finding(s)", file=sys.stderr)
    sys.exit(1 if found else 0)
