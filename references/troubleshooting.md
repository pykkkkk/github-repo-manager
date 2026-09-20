# Troubleshooting

*中文要点：按状态码定位根因；不要盲目重试。*

## Authentication / authorization

| Symptom | Meaning | Fix |
|---|---|---|
| `401 Bad credentials` | token received but invalid/expired | regenerate the token |
| `403 Resource not accessible by personal access token` | token authenticated, **write scope missing** | classic PAT `repo`; fine-grained → Contents: Read and write |
| `403 rate limit` | API quota exhausted | `push_repo.py` retries with backoff; wait otherwise |
| `404 Not Found` on a repo you can read | wrong `owner/repo`, or private repo without access | verify the slug and token access |

## git channel

| Symptom | Fix |
|---|---|
| `git: command not found` | the REST channel is used automatically (`--channel auto`) |
| `nothing to commit` | files are unchanged vs the working tree — nothing to do |
| `fatal: not a git repository` | `--root` is not a clone; use the REST channel |
| push rejected (non-fast-forward) | the remote moved ahead; pull/rebase, or use a branch + PR |
| `Please tell me who you are` | set `git config user.name / user.email` |

## REST channel

| Symptom | Fix |
|---|---|
| `409 Git Repository is empty` on branch read | expected for a brand-new repo — the push creates the initial commit |
| branch read fails | check `--branch` name and token access |
| blob/tree/commit 4xx | the token lacks write scope (see above) |
| unchanged files skipped | expected: idempotent push compares blob SHAs |

## Environment

| Symptom | Fix |
|---|---|
| no token detected | **ask the user** for a token, then export `GH_TOKEN` (or `GITHUB_TOKEN`); or run `push_repo.py --ask-token` |
| network probe fails | offline / proxy / firewall; `detect_env.py --net` to confirm |
| Docker present but unused | Docker only enables the GitHub MCP server; writes still use git or REST |
