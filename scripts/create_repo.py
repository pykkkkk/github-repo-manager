#!/usr/bin/env python3
"""create_repo.py -- create a new GitHub repository (the publish entry point).

Intended flow (see references/publish-audit.md):
  1. python scripts/publish_audit.py --root <dir>     # community / copyright / license
  2. ask the user which license to publish under
  3. python scripts/create_repo.py --name <repo> ... --yes
  4. python scripts/push_repo.py  --repo <owner>/<repo> ... --yes

Dry-run by default (prints the payload); add --yes to actually create.
The token is read from the environment only (GH_TOKEN / GITHUB_TOKEN).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_API = "https://api.github.com"


def build_payload(name, description=None, private=False, auto_init=False,
                  license_template=None):
    """Pure function -- returns the request body for POST /user/repos."""
    payload = {"name": name, "private": bool(private), "auto_init": bool(auto_init)}
    if description:
        payload["description"] = description
    if license_template:
        payload["license_template"] = license_template
    return payload


def load_token(name=None):
    for n in ([name] if name else ["GH_TOKEN", "GITHUB_TOKEN"]):
        if os.environ.get(n):
            return os.environ[n]
    return None


def mask(s):
    return s[:4] + "***" + s[-2:] if s and len(s) > 8 else "***"


def api_post(url, token, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "github-repo-manager")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode("utf-8"))
        except Exception:
            j = None
        return e.code, j
    except Exception as e:
        return 0, {"message": "network error: %s" % e}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Create a new GitHub repository")
    ap.add_argument("--name", required=True)
    ap.add_argument("--description", default=None)
    ap.add_argument("--private", action="store_true", help="create as private")
    ap.add_argument("--auto-init", action="store_true",
                    help="initialise with a default branch (default: create empty)")
    ap.add_argument("--license", default=None,
                    help="GitHub license template, e.g. mit, apache-2.0, gpl-3.0")
    ap.add_argument("--org", default=None, help="create under this organisation")
    ap.add_argument("--token-env", default=None)
    ap.add_argument("--api-base", default=DEFAULT_API)
    ap.add_argument("--yes", action="store_true", help="actually create (default: dry-run)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)

    payload = build_payload(a.name, a.description, a.private, a.auto_init, a.license)
    url = a.api_base.rstrip("/") + "/" + (
        f"orgs/{a.org}/repos" if a.org else "user/repos")

    if not a.yes:
        print("DRY-RUN. POST", url)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("Re-run with --yes to create.")
        return 0

    token = load_token(a.token_env)
    if not token:
        print("ACTION REQUIRED: no GitHub token found (GH_TOKEN / GITHUB_TOKEN).")
        print("  -> ASK THE USER to paste a token, then export it as GH_TOKEN and re-run.")
        return 3

    s, j = api_post(url, token, payload)
    if s not in (200, 201):
        print("FAILED", s, (j or {}).get("message"))
        return 1
    print("CREATED", s, j.get("full_name"), j.get("html_url"))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"full_name": j.get("full_name"), "html_url": j.get("html_url"),
                       "default_branch": j.get("default_branch")}, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
