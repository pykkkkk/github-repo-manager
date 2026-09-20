#!/usr/bin/env python3
"""detect_env.py -- probe environment capabilities for github-repo-manager.

Reports which push channels are available so the skill can adapt:
  git  : local git CLI present AND the working dir has an `origin` remote
  rest : fall back to the GitHub REST (Git Data) API
  none : no usable token in the environment

Never prints token values -- only which env var (if any) holds one.

Usage:
  python detect_env.py --root . [--net] [--api-base URL] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

TOKEN_ENVS = ("GH_TOKEN", "GITHUB_TOKEN")


def token_source():
    for n in TOKEN_ENVS:
        if os.environ.get(n):
            return n
    return None


def git_info(root: str):
    """Return (git_cli_present, remote_url_or_None_or_False)."""
    git = shutil.which("git")
    if not git:
        return False, None
    try:
        r = subprocess.run([git, "-C", root, "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return True, False  # git exists, but not a repo
        r2 = subprocess.run([git, "-C", root, "remote", "get-url", "origin"],
                            capture_output=True, text=True, timeout=10)
        remote = r2.stdout.strip() if r2.returncode == 0 else None
        return True, (remote or False)
    except Exception:
        return True, None


def net_ok(host: str, timeout: int = 4) -> bool:
    try:
        req = urllib.request.Request("https://" + host, method="HEAD")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True  # server reachable
    except Exception:
        return False


def detect(root: str = ".", check_net: bool = False, api_base: str | None = None) -> dict:
    git_cli, remote = git_info(root)
    docker = shutil.which("docker")
    api_base = api_base or os.environ.get("GITHUB_API_URL") or "https://api.github.com"
    tok = token_source()
    result = {
        "root": os.path.abspath(root),
        "git_cli": bool(shutil.which("git")),
        "git_remote": remote or None,
        "docker": docker or None,
        "python": sys.executable,
        "token_env": tok,
        "api_base": api_base,
        "network_ok": None,
        "recommended_channel": None,
    }
    if check_net:
        host = api_base.replace("https://", "").replace("http://", "").split("/")[0]
        result["network_ok"] = net_ok(host)
    if tok is None:
        result["recommended_channel"] = "none (no token in env)"
        result["need_token"] = True
        result["next_action"] = "ask_user_for_token"
        result["ask"] = ("Ask the user to paste a GitHub token -- a classic PAT with "
                         "the 'repo' scope, or a fine-grained PAT with "
                         "'Contents: Read and write' on the target repository.")
    elif git_cli and remote:
        result["recommended_channel"] = "git"
        result["need_token"] = False
    else:
        result["recommended_channel"] = "rest"
        result["need_token"] = False
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description="Detect GitHub push capabilities")
    ap.add_argument("--root", default=".")
    ap.add_argument("--net", action="store_true", help="also probe network")
    ap.add_argument("--api-base")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    r = detect(a.root, a.net, a.api_base)
    text = json.dumps(r, ensure_ascii=False, indent=2)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
