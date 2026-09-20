#!/usr/bin/env python3
"""update_skill.py -- self-update for the github-repo-manager skill.

Compares the local VERSION against the latest GitHub Release of the skill's
own repository and, on request, downloads + installs the newer version
(with a timestamped backup). Pure standard library.

Override the target repo with the env var GITHUB_REPO_MANAGER_SLUG.

Usage:
  python update_skill.py check     # is a newer release available?
  python update_skill.py update    # download + install latest (backs up first)
  python update_skill.py update --force
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VERSION_FILE = SKILL_DIR / "VERSION"
BACKUP_ROOT = SKILL_DIR.parent / "_backups"
REPO_SLUG = os.environ.get("GITHUB_REPO_MANAGER_SLUG", "pykkkkk/github-repo-manager")
REPO_URL = "https://github.com/" + REPO_SLUG


def parse_ver(s: str):
    s = s.strip().lstrip("vV")
    parts = []
    for p in s.split("."):
        num = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def local_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "0.0.0"


def fetch_latest(timeout: int = 15):
    url = f"https://api.github.com/repos/{REPO_SLUG}/releases/latest"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "github-repo-manager-update")
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": "no release published yet"}
        if e.code in (401, 403):
            return {"error": f"access denied ({e.code}); set GH_TOKEN if the repo is private"}
        return {"error": f"http {e.code}"}
    except Exception as e:  # network down, DNS, TLS, ...
        return {"error": f"network: {e}"}


def cmd_check(args):
    lv = local_version()
    rel = fetch_latest()
    if "error" in rel:
        print(f"local={lv}  check unavailable: {rel['error']}")
        return 0
    rv = rel.get("tag_name", "")
    newer = parse_ver(rv) > parse_ver(lv)
    print(f"local={lv}  latest={rv}  update_available={newer}")
    return 0


def cmd_update(args):
    rel = fetch_latest()
    if "error" in rel:
        print("update failed:", rel["error"])
        return 1
    rv = rel.get("tag_name", "")
    if not args.force and parse_ver(rv) <= parse_ver(local_version()):
        print(f"already up to date (local={local_version()}, latest={rv})")
        return 0
    tarball = rel.get("tarball_url")
    if not tarball:
        print("no tarball url in release payload")
        return 1

    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_ROOT / f"github-repo-manager_{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copytree(SKILL_DIR, backup)

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "pkg.tar.gz")
        urllib.request.urlretrieve(tarball, path)
        with tarfile.open(path) as tf:
            try:
                tf.extractall(td, filter="data")
            except TypeError:  # Python < 3.12
                tf.extractall(td)
        roots = [os.path.join(td, n) for n in os.listdir(td)
                 if os.path.isdir(os.path.join(td, n))]
        src = roots[0] if roots else td
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = SKILL_DIR / item
            if os.path.isdir(s):
                if d.exists():
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

    print(f"updated to {rv}; backup at {backup}. Restart the session to reload.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Self-update for github-repo-manager")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("check", help="check for a newer release")
    p1.set_defaults(func=cmd_check)
    p2 = sub.add_parser("update", help="download and install the latest release")
    p2.add_argument("--force", action="store_true")
    p2.set_defaults(func=cmd_update)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
