#!/usr/bin/env python3
"""push_repo.py -- universal GitHub repository pusher.

Channels (auto-selected, or forced with --channel):
  git  : local git CLI + `origin` remote      (preferred when available)
  rest : GitHub Git Data API                  (fallback; no git/docker needed)

Safety defaults (all overridable, all deliberate):
  * dry-run is ON unless --yes is given
  * token is read from an environment variable only (never a file or CLI arg)
  * token is masked in every line of output
  * a pre-push secret scan runs by default (disable with --no-secret-scan)

Workflow:
  default  : push straight to --branch (e.g. main)
  --mode pr: create --pr-branch, push it, then open a pull request (never auto-merges)

Usage:
  python push_repo.py --repo owner/name --root . --files README.md \
      --branch main -m "docs: fix typo" [--yes]
  python push_repo.py --repo owner/name --root . --files a.md b.py \
      --mode pr --pr-branch update/docs -m "docs update" [--yes]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

# secret_scan sits next to this file in scripts/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import secret_scan  # noqa: E402

DEFAULT_API = "https://api.github.com"


class PushError(RuntimeError):
    pass


def mask(s: str) -> str:
    if not s:
        return s
    return s[:4] + "***" + s[-2:] if len(s) > 8 else "***"


def redact(obj, tokens):
    text = json.dumps(obj, ensure_ascii=False)
    for t in tokens:
        if t:
            text = text.replace(t, "***REDACTED***")
    return json.loads(text)


def git_blob_sha(data: bytes) -> str:
    """Git's object hash for a blob (what `git hash-object` returns)."""
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def api(method, path, token, api_base=DEFAULT_API, data=None, retries=3):
    """Call the GitHub REST API. Returns (status_code, parsed_json|None)."""
    url = api_base.rstrip("/") + path
    body = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", "Bearer " + token)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "github-repo-manager")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                raw = r.read()
            return r.status, (json.loads(raw.decode("utf-8")) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                j = json.loads(raw.decode("utf-8")) if raw else None
            except Exception:
                j = {"raw": raw.decode("utf-8", "replace")[:200]}
            msg = (j or {}).get("message", "")
            if e.code == 403 and "rate limit" in msg.lower() and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            return e.code, j
        except Exception as e:
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            return 0, {"message": "network error: %s" % e}


def get_branch_head(token, repo, branch, api_base):
    s, j = api("GET", f"/repos/{repo}/git/ref/heads/{branch}", token, api_base)
    if s != 200:
        raise PushError(f'cannot read branch "{branch}" ({s}): {(j or {}).get("message")}')
    return j["object"]["sha"]


def get_branch_head_optional(token, repo, branch, api_base):
    """Return the branch head SHA, or None when the repository has no such
    branch yet. GitHub signals an empty repository with HTTP 409
    ("Git Repository is empty") and a missing ref with 404."""
    s, j = api("GET", f"/repos/{repo}/git/ref/heads/{branch}", token, api_base)
    if s == 200:
        return j["object"]["sha"]
    msg = (j or {}).get("message", "")
    if s == 404 or (s == 409 and "empty" in msg.lower()):
        return None
    raise PushError(f'cannot read branch "{branch}" ({s}): {msg}')


def get_commit(token, repo, sha, api_base):
    s, j = api("GET", f"/repos/{repo}/git/commits/{sha}", token, api_base)
    if s != 200:
        raise PushError(f"cannot read commit {sha} ({s}): {(j or {}).get('message')}")
    return j


def get_tree_map(token, repo, tree_sha, api_base):
    s, j = api("GET", f"/repos/{repo}/git/trees/{tree_sha}?recursive=1", token, api_base)
    if s != 200:
        raise PushError(f"cannot read tree ({s}): {(j or {}).get('message')}")
    return {e["path"]: e for e in j.get("tree", [])}


def build_plan(root: str, files, remote_map: dict):
    """Classify each local file as create / update / unchanged / missing."""
    ops = []
    for rel in files:
        rel_posix = rel.replace("\\", "/")
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            ops.append({"path": rel_posix, "op": "missing",
                        "note": "local file not found"})
            continue
        with open(full, "rb") as f:
            data = f.read()
        sha = git_blob_sha(data)
        r = remote_map.get(rel_posix)
        if r is None:
            op = "create"
        elif r.get("type") == "blob" and r.get("sha") == sha:
            op = "unchanged"
        else:
            op = "update"
        ops.append({"path": rel_posix, "op": op, "sha": sha, "bytes": len(data)})
    return ops


def git_repo_info(root: str):
    git = shutil.which("git")
    if not git:
        return None
    try:
        r = subprocess.run([git, "-C", root, "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def run_git(root: str, args, token=None):
    git = shutil.which("git")
    if token:
        b64 = base64.b64encode(("x-access-token:" + token).encode()).decode()
        cmd = [git, "-C", root,
               "-c", "http.extraHeader=Authorization: Basic " + b64] + list(args)
    else:
        cmd = [git, "-C", root] + list(args)
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise PushError("git %s failed: %s" % (" ".join(args),
                                                (p.stderr or p.stdout).strip()[:300]))
    return p.stdout.strip()


def push_git(root, files, branch, message, token, mode, pr_branch):
    run_git(root, ["add", "--"] + list(files))
    git = shutil.which("git")
    chk = subprocess.run([git, "-C", root, "diff", "--cached", "--quiet"])
    if chk.returncode == 0:
        return {"channel": "git", "note": "nothing to commit (all unchanged)"}
    run_git(root, ["commit", "-m", message])
    if mode == "pr":
        run_git(root, ["checkout", "-b", pr_branch])
        run_git(root, ["push", "-u", "origin", pr_branch], token=token)
        return {"channel": "git", "branch": pr_branch, "note": "branch pushed"}
    run_git(root, ["push", "origin", branch], token=token)
    return {"channel": "git", "branch": branch, "note": "pushed"}


def push_rest(root, repo, files, branch, message, token, api_base, mode, pr_branch, plan):
    head = get_branch_head_optional(token, repo, branch, api_base)
    if not head:
        # Empty repository: the Git Data API refuses to create blobs before the
        # repo has a commit, so make the first commit through the Contents API
        # (which bootstraps the branch), then continue with the Git Data API.
        if mode == "pr":
            raise PushError("cannot open a pull request into an empty repository")
        first = next((op for op in plan if op["op"] == "create"), None)
        if first is None:
            raise PushError("repository is empty but there is nothing to push")
        with open(os.path.join(root, first["path"]), "rb") as f:
            content = f.read()
        s, j = api("PUT", f"/repos/{repo}/contents/{first['path']}", token, api_base,
                   {"message": message, "content": base64.b64encode(content).decode()})
        if s not in (200, 201):
            raise PushError(f'bootstrap ({first["path"]}) failed ({s}): {(j or {}).get("message")}')
        head = get_branch_head_optional(token, repo, branch, api_base)
        if not head:
            raise PushError("bootstrap did not create the branch")
    commit = get_commit(token, repo, head, api_base)
    base_tree = commit["tree"]["sha"]
    entries = []
    for op in plan:
        if op["op"] not in ("create", "update"):
            continue
        with open(os.path.join(root, op["path"]), "rb") as f:
            content = f.read()
        s, j = api("POST", f"/repos/{repo}/git/blobs", token, api_base,
                   {"content": base64.b64encode(content).decode(), "encoding": "base64"})
        if s not in (200, 201):
            raise PushError(f'blob {op["path"]} failed ({s}): {(j or {}).get("message")}')
        entries.append({"path": op["path"], "mode": "100644", "type": "blob", "sha": j["sha"]})
    if not entries:
        return {"channel": "rest", "note": "nothing to push (all unchanged)"}
    tree_payload = {"tree": entries}
    if base_tree:
        tree_payload["base_tree"] = base_tree
    s, j = api("POST", f"/repos/{repo}/git/trees", token, api_base, tree_payload)
    if s not in (200, 201):
        raise PushError(f'tree failed ({s}): {(j or {}).get("message")}')
    new_tree = j["sha"]
    commit_payload = {"message": message, "tree": new_tree}
    if head:
        commit_payload["parents"] = [head]
    s, j = api("POST", f"/repos/{repo}/git/commits", token, api_base, commit_payload)
    if s not in (200, 201):
        raise PushError(f'commit failed ({s}): {(j or {}).get("message")}')
    new_commit = j["sha"]
    if mode == "pr":
        s, j = api("POST", f"/repos/{repo}/git/refs", token, api_base,
                   {"ref": f"refs/heads/{pr_branch}", "sha": new_commit})
        if s not in (200, 201):
            raise PushError(f'branch create failed ({s}): {(j or {}).get("message")}')
        return {"channel": "rest", "commit": new_commit, "branch": pr_branch,
                "note": "branch ready"}
    if head:
        s, j = api("PATCH", f"/repos/{repo}/git/refs/heads/{branch}", token, api_base,
                   {"sha": new_commit, "force": False})
    else:
        s, j = api("POST", f"/repos/{repo}/git/refs", token, api_base,
                   {"ref": f"refs/heads/{branch}", "sha": new_commit})
    if s not in (200, 201):
        raise PushError(f'ref update failed ({s}): {(j or {}).get("message")}')
    return {"channel": "rest", "commit": new_commit, "branch": branch,
            "note": ("initial commit" if not head else "pushed")}


def open_pr(repo, head_branch, base_branch, title, body, token, api_base):
    s, j = api("POST", f"/repos/{repo}/pulls", token, api_base,
               {"title": title, "head": head_branch, "base": base_branch, "body": body})
    if s not in (200, 201):
        raise PushError(f'open PR failed ({s}): {(j or {}).get("message")}')
    return j["html_url"]


def load_token(name=None):
    names = [name] if name else list(("GH_TOKEN", "GITHUB_TOKEN"))
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None


def prompt_token(label="GitHub token (input hidden, never stored): "):
    """Ask for a token on an interactive terminal (never echoed, never stored)."""
    import getpass
    try:
        return (getpass.getpass(label) or "").strip() or None
    except Exception:
        return None


def _emit(report, path, tokens):
    text = json.dumps(redact(report, tokens), ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Universal GitHub repository pusher")
    ap.add_argument("--repo", help="owner/name (required for the REST channel)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--files", nargs="+", required=True, help="relative file paths")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--message", "-m", default="Update via github-repo-manager")
    ap.add_argument("--channel", choices=["auto", "git", "rest"], default="auto")
    ap.add_argument("--mode", choices=["push", "pr"], default="push")
    ap.add_argument("--pr-branch", default=None)
    ap.add_argument("--pr-title", default=None)
    ap.add_argument("--pr-body", default="")
    ap.add_argument("--token-env", default=None)
    ap.add_argument("--api-base", default=DEFAULT_API)
    ap.add_argument("--no-secret-scan", action="store_true")
    ap.add_argument("--ask-token", action="store_true",
                    help="if no token is in the env, prompt for one (hidden input)")
    ap.add_argument("--yes", action="store_true",
                    help="actually perform writes (default: dry-run)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)

    root = os.path.abspath(a.root)
    token = load_token(a.token_env)
    report = {"root": root, "files": list(a.files), "mode": a.mode,
              "branch": a.branch, "dry_run": not a.yes}

    # 1) pre-push secret scan
    if not a.no_secret_scan:
        findings, scanned = secret_scan.scan(root, a.files)
        report["secret_scan"] = {"ok": not findings, "scanned": len(scanned),
                                 "findings": findings}
        if findings:
            report["aborted"] = "secret scan failed"
            _emit(report, a.json, [token])
            print("ABORTED: secret scan found credentials -- fix before pushing.")
            for f in findings:
                print(f"  - {f['file']}:{f['line']} [{f['rule']}] {f['match']}")
            return 2
    else:
        report["secret_scan"] = {"skipped": True}

    # 2) token
    if not token and a.ask_token:
        token = prompt_token()
    if not token:
        report["aborted"] = "no token in environment"
        report["need_token"] = True
        report["next_action"] = "ask_user_for_token"
        report["ask"] = ("Ask the user to paste a GitHub token -- a classic PAT with "
                         "the 'repo' scope, or a fine-grained PAT with "
                         "'Contents: Read and write' on the target repository. "
                         "Then export it as GH_TOKEN and re-run.")
        _emit(report, a.json, [])
        print("ACTION REQUIRED: no GitHub token found (GH_TOKEN / GITHUB_TOKEN).")
        print("  -> ASK THE USER to paste a token, then export it as GH_TOKEN and re-run.")
        print("  -> Token policy: env only, masked in output, never written to disk.")
        return 3
    report["token"] = "present (" + mask(token) + ")"

    # 3) channel selection
    remote = git_repo_info(root) if a.channel in ("auto", "git") else None
    if a.channel == "auto":
        channel = "git" if (shutil.which("git") and remote) else "rest"
    else:
        channel = a.channel
    report["channel"] = channel
    report["git_remote"] = remote
    if channel == "rest" and not a.repo:
        report["aborted"] = "repo required for REST channel"
        _emit(report, a.json, [token])
        print("ABORTED: --repo owner/name is required for the REST channel.")
        return 4

    # 4) plan
    if channel == "rest":
        try:
            head = get_branch_head_optional(token, a.repo, a.branch, a.api_base)
            if head:
                commit = get_commit(token, a.repo, head, a.api_base)
                remote_map = get_tree_map(token, a.repo, commit["tree"]["sha"], a.api_base)
            else:
                remote_map = {}  # empty repo -> every file is a create / initial commit
                report["empty_repo"] = True
        except PushError as e:
            report["aborted"] = str(e)
            _emit(report, a.json, [token])
            print("ABORTED:", e)
            return 5
        plan = build_plan(root, a.files, remote_map)
    else:
        plan = [{"path": f.replace("\\", "/"), "op": "via-git"} for f in a.files]
    report["plan"] = plan

    if not a.yes:
        _emit(report, a.json, [token])
        print(f"DRY-RUN (channel={channel}). Planned operation:")
        if report.get("empty_repo"):
            print("  (repository is empty -> this push creates the initial commit)")
        for op in plan:
            extra = f" ({op['bytes']} B)" if "bytes" in op else ""
            print(f"  - {op['op']:<9} {op['path']}{extra}")
        print("Re-run with --yes to execute.")
        return 0

    # 5) execute
    try:
        if channel == "git":
            res = push_git(root, a.files, a.branch, a.message, token, a.mode, a.pr_branch)
        else:
            res = push_rest(root, a.repo, a.files, a.branch, a.message, token,
                            a.api_base, a.mode, a.pr_branch, plan)
        report["result"] = res
        if a.mode == "pr":
            head_branch = a.pr_branch or ("update-" + time.strftime("%Y%m%d-%H%M%S"))
            url = open_pr(a.repo, head_branch, a.branch, a.pr_title or a.message,
                          a.pr_body, token, a.api_base)
            report["pr_url"] = url
            print("PR opened:", url)
        else:
            print("Push complete:", res)
    except PushError as e:
        report["aborted"] = str(e)
        _emit(report, a.json, [token])
        print("FAILED:", e)
        return 6

    _emit(report, a.json, [token])
    return 0


if __name__ == "__main__":
    sys.exit(main())
