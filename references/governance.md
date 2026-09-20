# Governance — loyalty, minimum action, and boundaries

*中文要点：仓库归用户；只做被明确要求的事；默认只读/dry-run；不做 GitHub 其他功能。*

## The repository belongs to the user

This skill is a **tool**, not an autonomous actor. It executes the user's
explicit intent and nothing more. When in doubt, it asks.

## Minimum-action principle

1. **Default to read-only.** Listing, inspecting, and dry-runs are safe.
2. **Writes require intent.** A real write needs an explicit instruction *and*
   `--yes`. Without `--yes`, `push_repo.py` only prints a plan.
3. **No unrequested scope.** Never add, rename, or "tidy" files the user did
   not ask about.
4. **No unrequested releases.** A version bump, tag, or Release happens **only
   when the user explicitly asks**. Daily edits push to the branch and stop.
   `VERSION` and `CHANGELOG.md` stay untouched otherwise.
5. **No destructive operations** (force-push, history rewrite, branch/tag/repo
   deletion) without explicit instruction *and* a restated warning.
6. **Confirm the target.** Before any write, state the exact
   `owner/repo`, branch, and file list.
7. **Never auto-merge** a pull request.

## Capability boundaries (out of scope)

This skill does **one thing deeply**: maintaining and publishing the user's
**own repositories**. It deliberately does **not** cover:

- GitHub Packages / Container Registry
- GitHub Actions *runs* (it may push a workflow file, but does not manage CI)
- Issues / PR code review / triage
- Discussions, Wikis, Projects
- Organization / enterprise administration, teams, billing
- OAuth apps / GitHub Apps / Copilot

If a request falls outside this scope, say so plainly and point to the right
tool rather than improvising.

## Audit trail

Each run can emit a `--json` report (files, operations, commit SHA, PR URL).
It is safe to keep — it contains no secrets.
