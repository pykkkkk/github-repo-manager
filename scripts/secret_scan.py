#!/usr/bin/env python3
"""secret_scan.py -- pre-push secret / privacy scanner.

Scans the files that are about to be pushed and reports anything that looks
like a credential, key, or private token. Never prints the full value (masked).

Usage:
  python secret_scan.py --root . --files README.md config.py
  python secret_scan.py --root . --paths src docs --json scan.json

Exit code: 0 = clean, 1 = findings, 2 = usage error.
Pure standard library (no third-party dependencies).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".7z", ".rar", ".exe", ".dll", ".so", ".dylib", ".bin", ".woff",
    ".woff2", ".ttf", ".otf", ".mp3", ".mp4", ".mov", ".avi", ".webp",
    ".class", ".jar", ".pyc", ".o", ".a",
}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
             ".idea", ".vscode", "dist", "build", "_backups"}

# (rule-name, compiled-regex). Ordered by specificity.
RULES = [
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("stripe_key", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("generic_credential", re.compile(
        r"(?i)\b(?:password|passwd|api[_-]?key|secret|access[_-]?token|auth[_-]?token)\b"
        r"\s*[:=]\s*[\"']?[^\s\"']{6,}")),
]

# Filenames that should never be committed even if their content looks clean.
SENSITIVE_NAMES = {
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".env", ".env.local",
    "credentials", "secrets", ".netrc", ".npmrc", ".pypirc", ".dockercfg",
}

# Values containing these markers are treated as placeholders, not real secrets.
PLACEHOLDER_MARKERS = (
    "your", "example", "placeholder", "changeme", "redacted", "xxxx",
    "****", "<", ">", "todo", "dummy", "sample", "env_var", "token_env",
)

# A source line containing any of these markers is skipped (whitelisting a
# deliberate false positive, e.g. a test fixture). Case-insensitive.
IGNORE_MARKERS = ("secret-scan: ignore", "nosec", "gitleaks:allow")


def mask(value: str) -> str:
    v = value.strip()
    if len(v) <= 8:
        return "***"
    return v[:4] + "***" + v[-2:]


def is_placeholder(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in PLACEHOLDER_MARKERS)


def scan_text(name: str, text: str):
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(m in low for m in IGNORE_MARKERS):
            continue
        for rule, rx in RULES:
            for m in rx.finditer(line):
                hit = m.group(0)
                if rule == "generic_credential" and is_placeholder(hit):
                    continue
                findings.append(
                    {"file": name, "line": i, "rule": rule, "match": mask(hit)}
                )
    return findings


def iter_files(root: str, paths):
    for p in paths:
        full = p if os.path.isabs(p) else os.path.join(root, p)
        if os.path.isdir(full):
            for dirpath, dirnames, filenames in os.walk(full):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for fn in filenames:
                    yield os.path.join(dirpath, fn)
        elif os.path.isfile(full):
            yield full


def scan(root: str, paths):
    """Return (findings, scanned_relpaths)."""
    findings = []
    scanned = []
    for full in iter_files(root, paths):
        ext = os.path.splitext(full)[1].lower()
        low = os.path.basename(full).lower()
        rel = os.path.relpath(full, root).replace("\\", "/")
        if ext in BINARY_EXTS:
            continue
        if low in SENSITIVE_NAMES:
            findings.append({"file": rel, "line": 0, "rule": "sensitive_filename",
                             "match": low})
            continue
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        scanned.append(rel)
        findings.extend(scan_text(rel, text))
    return findings, scanned


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pre-push secret scanner")
    ap.add_argument("--root", default=".")
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--paths", nargs="*", default=[])
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args(argv)

    targets = list(args.files) + list(args.paths)
    if not targets:
        print("secret_scan: nothing to scan (pass --files or --paths)")
        return 0

    findings, scanned = scan(args.root, targets)
    out = {"ok": not findings, "scanned_count": len(scanned), "findings": findings}
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    if findings:
        print(f"SECRET SCAN FAILED: {len(findings)} finding(s) in {len(scanned)} file(s)")
        for f in findings:
            print(f"  - {f['file']}:{f['line']} [{f['rule']}] {f['match']}")
        return 1
    print(f"SECRET SCAN OK: {len(scanned)} file(s) clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
