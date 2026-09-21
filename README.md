<div align="center">

<img src="./assets/icon.png" alt="github-repo-manager" width="150"> 

# github-repo-manager

**Your repository's resident robot — rigorous about safety, loyal to you, and honest when you're about to do something you'd regret.**

A **skill** for maintaining and publishing *your own* GitHub repositories.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](./CHANGELOG.md)
[![Dependencies](https://img.shields.io/badge/dependencies-none%20(stdlib)-brightgreen.svg)](#)

🌐 **Language:** English · [中文 (README.zh-CN.md)](./README.zh-CN.md)

</div>

---

## The idea in one paragraph

Automating GitHub is easy to do *badly*. A robot that pushes on command is a
liability; a robot that pushes **carefully** is an asset. This skill is built
around one narrow job — maintaining and publishing your repositories — and four
non-negotiable traits: it **adapts** to whatever machine it runs on, it
**protects** your credentials, it **obeys** your intent and nothing more, and it
**speaks up** when an instruction is dangerous. No Packages, no Actions
plumbing, no org admin. One job, done thoroughly.

## What it manages

| Area | What the robot does |
|---|---|
| **Push changes** | git when available, the GitHub **Git Data API** otherwise — one clean, idempotent commit |
| **Pull requests** | branch → push → open PR; it never auto-merges |
| **Releases & tags** | cut a Release **only when you ask**; bumps `VERSION` + `CHANGELOG` on request |
| **Publish a repo** | audit → choose a license → create → initial commit, end to end |
| **Connect an account** | asks you for a token, verifies it, uses it transiently |
| **Guardrails** | pre-push secret scan, dry-run by default, risky-instruction warnings |

## The four pillars

Think of them as the robot's personality.

| Pillar | Trait | In practice |
|---|---|---|
| **Generality** | *Adaptable* | Probes the environment, then picks a channel along the fallback chain **git → REST → fail**. No hard-coded "you must have git". |
| **Security** | *Discreet* | Token read from the environment only, masked in every line, never written to disk. Scans for secrets before every push. |
| **Loyalty** | *Obedient* | The repo is yours. Minimum-action principle: read-only by default; **no unrequested releases or version bumps**. |
| **Criticality** | *Honest* | If a move is risky, it says so **before** acting — in a fixed ⚠️ / ✅ / 📉 shape. |

## The workflow

```
  understand  →  detect env  →  critique  →  secret-scan  →  dry-run  →  push  →  (release)
       │            │             │             │             │          │         │
   repo/files   git? rest?    risky? warn    leak? abort   show plan   --yes   only if asked
```

Every step is visible. Nothing writes to GitHub until you pass `--yes`.

## Things the robot will say no to

Criticality, with a sense of humour. The full catalogue has 14 entries; three
favourites:

> **You:** "Just force-push my fix to `main`."
>
> **Robot:**
> ⚠️ *Risk* — `main` is shared; a force-push rewrites its history.
> ✅ *Recommended* — push a branch and open a PR, or fast-forward only.
> 📉 *Consequence* — collaborators' clones break and commits are lost.

> **You:** "I fixed a typo — bump `v1.0.0` to `v2.0.0`."
>
> **Robot:**
> ⚠️ *Risk* — a major bump signals breaking changes that don't exist.
> ✅ *Recommended* — a patch bump (`v1.0.1`) for a docs-only change.
> 📉 *Consequence* — downstream users over-react to a phantom break.

> **You:** "Commit everything, including `.env`."
>
> **Robot:**
> ⚠️ *Risk* — `.env` typically holds live credentials.
> ✅ *Recommended* — remove it and rotate the exposed secret.
> 📉 *Consequence* — secrets become public within seconds and are scraped by bots.

And yes — it will also **ask you for a token** the moment one is needed, rather
than failing silently or inventing one.

## Install

Put this folder in your WorkBuddy skills directory:

```
~/.workbuddy/skills/github-repo-manager/
```

Then just talk to it: *"push to github", "create a release", "publish my repo",
"connect my github"*.

## Quickstart

```bash
export GH_TOKEN=your_token_here                      # env only - never a file

python scripts/detect_env.py --root .     --net      # what's available?
python scripts/push_repo.py  --repo o/r --root . \
       --files README.md -m "docs: update"           # dry-run (default)
python scripts/push_repo.py  --repo o/r --root . \
       --files README.md -m "docs: update" --yes     # push for real

python scripts/create_repo.py --name my-repo --description "..."   # publish (dry-run)
python scripts/publish_audit.py --root .             # before going public
python scripts/selftest.py                           # offline validation (no token)
```

## Token scopes

| Token | Write access |
|---|---|
| Classic PAT | `repo` (private) / `public_repo` (public) |
| Fine-grained PAT | *Contents: Read and write* on the target repo |

> `403 "Resource not accessible by personal access token"` means the token
> authenticated but **lacks write scope** — regenerate it. It is never a reason
> to retry blindly.

## Design notes (for the curious)

- **Zero dependencies.** Pure Python standard library — no `pip install`.
- **Idempotent.** Files whose blob SHA matches the remote are skipped; no empty
  commits.
- **Initial-commit aware.** Publishing into a brand-new empty repo works with
  the same command.
- **Transient credentials.** The git channel injects the token as an HTTP
  header, never into the remote URL or any config file.
- **Self-maintaining.** `update_skill.py check | update` plus an offline
  `selftest.py` (29 checks).

## Out of scope

Packages / Container Registry, Actions *runs*, Issues triage, Discussions /
Wikis, organisation & enterprise admin, OAuth / GitHub Apps, Copilot.
Declined plainly, not improvised.

## License

MIT — see [LICENSE](./LICENSE).

<div align="center"><sub>Built to be boring in the ways that matter: safe, honest, and yours.</sub></div>
