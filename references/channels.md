# Channels — choosing how to talk to GitHub

*中文要点：不假设环境；先探测能力，再按回退链选通道。*

The skill never hard-codes an assumption such as "no git" or "no Docker".
It runs `scripts/detect_env.py` first and picks the best available channel.

## Capability → channel decision

| Environment | `git_cli` | `git_remote` | token in env | Chosen channel |
|---|---|---|---|---|
| Dev machine, repo cloned | yes | origin set | yes | **git** |
| Bare folder, no git CLI | no | — | yes | **rest** |
| Repo cloned, no token | yes | origin set | no | blocked → ask for token |
| Docker available, GitHub MCP connected | any | any | yes | MCP tools for **reads**; writes still via **git**, else **rest** |
| Read-only connector only (403 on writes) | any | any | yes | **rest** with a correctly-scoped PAT |

`detect_env.py` reports `recommended_channel` as one of `git`, `rest`,
`none (no token in env)`.

## git channel (preferred)

- Requires a local clone with an `origin` remote.
- Uses `git add / commit / push` under `--root`.
- Auth: the token is injected **transiently** as an HTTP header
  (`-c http.extraHeader=Authorization: Basic …`) — it is **never** written
  into the remote URL or any config file.
- Best fidelity: preserves history, hooks, and signing.

## rest channel (universal fallback)

- No git, no Docker required — only Python stdlib.
- Uses the **Git Data API** for a single clean commit:
  `blobs → tree(base_tree) → commit(parents=[head]) → PATCH ref`.
- Idempotent: file blob SHAs are compared against the remote tree first, so
  unchanged files are skipped (no empty commits).
- **Empty repository**: when the target branch does not exist yet (a freshly
  created repo), it makes the *initial commit* — a tree without `base_tree`, a
  commit without parents, then `POST /git/refs`. So the same command publishes
  a brand-new repository.
- Handles `403 rate limit` with bounded backoff.

## PR mode (`--mode pr`)

Only when the user explicitly asks for a pull request; the default is a
direct push to `--branch`. PR mode never auto-merges.

1. create `--pr-branch`
2. push the commit to that branch (git: `push -u`; rest: `POST /git/refs`)
3. `POST /repos/{owner}/{repo}/pulls` with title/body
4. report the PR URL — merging is the user's decision

## Enterprise GitHub

Set `--api-base https://<ghe-host>/api/v3` (or the `GITHUB_API_URL` env var)
to target GitHub Enterprise Server.
