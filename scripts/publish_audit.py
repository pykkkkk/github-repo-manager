#!/usr/bin/env python3
"""publish_audit.py -- pre-publish gate for a NEW public repository.

Before a project is published, this checks for:
  1. community / ToS risk  : suspicious names, executables, oversized files
  2. credentials           : files that must never be published
  3. copyright / license   : existing LICENSE files, third-party/vendored code

It never decides for the user. It reports findings and returns the exact
questions the skill should ask (including which license to publish under).

Usage:  python publish_audit.py --root . [--json out.json]
Exit:   0 = no blocking flags, 1 = blocking flags present.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

BINARY_EXTS = {".exe", ".dll", ".so", ".dylib", ".bin", ".msi", ".apk",
               ".jar", ".class", ".scr", ".bat", ".cmd", ".ps1"}
LICENSE_NAMES = {"license", "license.md", "license.txt", "licence",
                 "licence.md", "copying", "copying.txt", "notice", "notice.md"}
SUSPICIOUS_NAME_TOKENS = ("keygen", "crack", "warez", "exploit", "malware",
                          "phishing", "keylogger", "stealer", "botnet",
                          "ransomware", "trojan", "ddos", "credential-dump")
CRED_FILE_NAMES = {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".env",
                   ".env.local", "credentials", "secrets", ".netrc",
                   ".npmrc", ".pypirc", ".dockercfg"}
THIRD_PARTY_DIRS = {"node_modules", "vendor", "third_party", "thirdparty",
                    "deps", "extern"}
LARGE_FILE_BYTES = 50 * 1024 * 1024  # 50 MB

KNOWN_LICENSES = [
    ("MIT", ("mit license", "permission is hereby granted, free of charge")),
    ("Apache-2.0", ("apache license", "version 2.0")),
    ("GPL-3.0", ("gnu general public license", "version 3")),
    ("BSD-3-Clause", ("redistribution and use in source and binary forms",)),
]


def sniff_license(root: str):
    found = []
    try:
        names = os.listdir(root)
    except OSError:
        return found
    for name in names:
        if name.lower() in LICENSE_NAMES:
            try:
                text = open(os.path.join(root, name), encoding="utf-8",
                            errors="replace").read().lower()
            except OSError:
                continue
            kind = "unknown"
            for lic, keys in KNOWN_LICENSES:
                if any(k in text for k in keys):
                    kind = lic
                    break
            found.append({"file": name, "detected": kind})
    return found


def audit(root: str) -> dict:
    community, large, creds, third_party, copyright_files = [], [], [], [], []
    copyright_rx = re.compile(r"(?i)(copyright\s*\(c\)|spdx-license-identifier|"
                              r"licensed under|all rights reserved)")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirnames:
            dirnames.remove(".git")
        rel_dir = os.path.relpath(dirpath, root)
        for d in list(dirnames):
            if d.lower() in THIRD_PARTY_DIRS:
                third_party.append(os.path.join(rel_dir, d).replace("\\", "/"))
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            low = fn.lower()
            ext = os.path.splitext(low)[1]
            if any(t in low for t in SUSPICIOUS_NAME_TOKENS):
                community.append({"file": rel, "why": "name suggests disallowed content"})
            if ext in BINARY_EXTS:
                community.append({"file": rel, "why": "executable/script needs review"})
            if low in CRED_FILE_NAMES:
                creds.append(rel)
            try:
                size = os.path.getsize(full)
                if size > LARGE_FILE_BYTES:
                    large.append({"file": rel, "mb": round(size / 1048576, 1)})
                if ext in (".py", ".js", ".ts", ".go", ".java", ".rb", ".c", ".cpp") and size < 2_000_000:
                    text = open(full, encoding="utf-8", errors="replace").read()
                    if copyright_rx.search(text):
                        copyright_files.append(rel)
            except OSError:
                pass

    licenses = sniff_license(root)
    questions = []
    if not licenses:
        questions.append("No LICENSE file found. Which license do you want to "
                         "publish under? (MIT / Apache-2.0 / GPL-3.0 / proprietary / other)")
    else:
        summary = ", ".join(f"{l['file']}={l['detected']}" for l in licenses)
        questions.append(f"Detected license file(s): {summary}. Confirm this matches your intent.")
    if third_party:
        questions.append("Third-party / vendored code detected. Verify attribution and "
                         "license compatibility before publishing.")
    if copyright_files:
        questions.append(f"{len(copyright_files)} source file(s) carry a copyright/SPDX "
                         "header -- confirm the copyright holder is correct.")

    return {
        "ok": not community and not creds,
        "licenses": licenses,
        "community_flags": community,
        "credential_files": creds,
        "large_files": large,
        "third_party_dirs": third_party,
        "copyright_files": copyright_files,
        "ask_user": questions,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pre-publish audit gate")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    r = audit(os.path.abspath(a.root))
    text = json.dumps(r, ensure_ascii=False, indent=2)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
    if not r["ok"]:
        print("\nBLOCKING: resolve community/credential flags before publishing.")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
