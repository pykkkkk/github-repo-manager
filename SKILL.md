---
name: github-repo-manager
description: Use when the user wants to maintain or publish their OWN GitHub repository — push local file changes (direct to the default branch or via a pull request), create/list releases, bump version and changelog, or connect a GitHub account/token. Adapts to the environment (git CLI, Docker + GitHub MCP, or a pure REST API fallback), runs a pre-push secret scan, enforces a minimum-action loyalty guardrail, and flags risky instructions (force-push, wrong version bumps, secret leaks, destructive operations). Runs a publish audit for community-rule, copyright, and license issues before a new public repo goes live. Does NOT cover GitHub Packages, Actions runs, Issues triage, Discussions, or org admin. Triggers on "push to github", "create a release", "publish my repo", "connect my github", "bump version".
agent_created: true
---

# GitHub Repo Manager

Help the user maintain and publish **their own** GitHub repositories — and
nothing else. Do the narrow job thoroughly: push changes, cut releases,
version them, connect an account, and guard the user against their own risky
instructions.

## The four pillars

1. **Generality** — never assume the environment. Run `scripts/detect_env.py`
   first, then pick a channel from the fallback chain **git → REST → fail**.
   See `references/channels.md`.
2. **Security** — read the token from the environment only, mask it
   everywhere, and run `scripts/secret_scan.py` before every push. See
   `references/security.md`.
3. **Loyalty** — the repository is the user's. Follow the minimum-action
   principle: default read-only, writes only on explicit intent, no
   unrequested releases or version bumps. See `references/governance.md`.
4. **Criticality** — when an instruction is risky, say so before acting, in
   the ⚠️ Risk / ✅ Recommended / 📉 Consequence shape. See
   `references/critique-playbook.md`.

## Standard workflow

1. **Understand the request.** Identify the exact repo, branch, and files.
2. **Detect the environment.**
   `python scripts/detect_env.py --root <dir> [--net]`
   If it reports `need_token: true` (no `GH_TOKEN` / `GITHUB_TOKEN`), **stop and
   ask the user to paste a token** — see "Connecting an account" below. Never
   guess, never fabricate, never proceed without one.
3. **Critique first.** If the request matches a case in
   `references/critique-playbook.md`, surface the warning and wait.
4. **Scan for secrets (pushes).** Automatic inside `push_repo.py`; can also be
   run alone: `python scripts/secret_scan.py --root <dir> --files <...>`.
5. **Preview, then act.** `push_repo.py` is dry-run by default. Show the plan;
   execute only with `--yes`.
6. **Publish a new repo.** Run `python scripts/publish_audit.py --root <dir>`,
   resolve blocking flags, **ask the user which license to use**, then create
   the repo (`python scripts/create_repo.py --name <repo> --description "..." --yes`,
   empty by default) and push. `push_repo.py` creates the initial commit
   automatically when the repository has no branch yet.
7. **Report** what changed: files, commit/PR URL, and any warnings.

## Releases & versioning

- Cut a Release **only when the user explicitly asks**. Daily edits push to the
  branch and stop — leave `VERSION` and `CHANGELOG.md` untouched.
- When asked to release: bump `VERSION`, add a `CHANGELOG.md` entry, tag, and
  create the Release (e.g. `POST /repos/{owner}/{repo}/releases`).

## Connecting an account (ask the user for the token)

There is usually **no token in the environment**. Whenever a task needs
GitHub access and `detect_env.py` (or `push_repo.py`) reports
`need_token: true`, **ask the user directly for a token**. Do not fail
silently, and never invent or reuse an unknown credential.

1. **Ask the user** to paste a token with the right scope:
   - classic PAT — scope `repo` (private) or `public_repo` (public only)
   - fine-grained PAT — repository → **Contents: Read and write** (+ Metadata: Read)
2. **Verify** it authenticates with `GET /user` before using it.
3. **Use it transiently** — pass it as `GH_TOKEN` for this invocation only.
   Never write it to a file, the repo, memory, or logs; it is masked in every
   line of output. On an interactive terminal, `push_repo.py --ask-token`
   can prompt for it with hidden input.
4. Reuse the same token for the rest of the session; ask again only when it
   expires or lacks scope (see `references/troubleshooting.md`).

`examples/quickstart.md` "step 0" is the exact script the user can follow.

## Out of scope

Packages, Actions runs, Issues triage, Discussions/Wikis, org/enterprise
admin, OAuth/GitHub Apps, Copilot. Decline plainly and point elsewhere.

## Self-maintenance

```bash
python scripts/update_skill.py check     # newer release available?
python scripts/update_skill.py update    # download + install (backs up first)
python scripts/selftest.py               # offline validation, no token needed
```

## Files

- `scripts/detect_env.py` — capability probe → `recommended_channel`
- `scripts/push_repo.py` — git/REST pusher, PR mode, secret scan, dry-run
- `scripts/secret_scan.py` — pre-push credential scanner
- `scripts/create_repo.py` — create a new repo (publish entry point, dry-run)
- `scripts/publish_audit.py` — community / copyright / license gate
- `scripts/update_skill.py` — self-update (check / update)
- `scripts/selftest.py` — offline test suite
- `references/` — channels, security, governance, critique-playbook,
  publish-audit, troubleshooting
- `examples/quickstart.md` — copy-paste walkthrough
