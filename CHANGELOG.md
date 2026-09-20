# Changelog

All notable changes to the **github-repo-manager** skill are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-09-20

Initial public release.

### Added
- Four pillars: **generality, security, loyalty, criticality**.
- `scripts/detect_env.py` — environment capability probe with a git/REST
  channel decision; emits `need_token` / `next_action` when no token is present.
- `scripts/push_repo.py` — universal pusher (git-first, REST fallback), PR
  mode, idempotent blob-SHA comparison, **initial-commit support for empty
  repositories**, dry-run by default, rate-limit backoff, and `--ask-token`
  (hidden prompt).
- `scripts/create_repo.py` — create a new repository (publish entry point,
  empty by default, dry-run).
- `scripts/secret_scan.py` — pre-push credential / privacy scanner.
- `scripts/publish_audit.py` — community-rule, copyright, and license gate.
- `scripts/update_skill.py` — self-update (`check` / `update`).
- `scripts/selftest.py` — offline validation suite (no token, no network).
- `references/` — channels, security, governance, critique-playbook (14 risky
  instruction cases), publish-audit, troubleshooting.
- `examples/quickstart.md`, bilingual `README.md` / `README.zh-CN.md`, MIT
  `LICENSE`, and a repository-maintenance robot icon (`assets/icon.png`).

### Behaviour
- **Asks the user for a token** whenever the environment has none.
- **Never bumps a version or cuts a Release unless the user explicitly asks.**
