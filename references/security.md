# Security — tokens, secrets, and privacy

*中文要点：token 只经环境变量、绝不落盘；推送前扫密钥；所有输出掩码。*

## 1. Token handling (hard rules)

- **Read only from the environment**: `GH_TOKEN` (preferred) or
  `GITHUB_TOKEN`. Never accept a token as a CLI argument or from a file.
- **Ask the user when none is present.** If neither env var is set, *ask the
  user to paste a token* (the agent asks in conversation;
  `push_repo.py --ask-token` prompts with hidden input on a terminal). Do not
  proceed without one and do not fabricate a credential.
- **Never persist**: no token in scripts, config, README, memory, logs, or the
  remote URL. The git channel injects it as a transient HTTP header.
- **Mask everywhere**: any echoed value is reduced to `ghpxxx***yy`.
- Requested scopes depend on the case:

  | Token type | Needed for writes |
  |---|---|
  | Classic PAT | `repo` (private) / `public_repo` (public only) |
  | Fine-grained PAT | Repository → **Contents: Read and write** (+ Metadata: Read) |

  A `403 "Resource not accessible by personal access token"` means the token
  authenticated but lacks write scope — regenerate it; do not retry blindly.

## 2. Pre-push secret scan

`scripts/secret_scan.py` runs before every push (disable with
`--no-secret-scan`, at your own risk). It flags:

- GitHub tokens (`ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`, `github_pat_`)
- AWS (`AKIA…`), Google (`AIza…`), Slack (`xox…`), Stripe (`sk_live_…`)
- Private-key blocks, JWTs
- Generic `password/api_key/secret/token = …` assignments
- Sensitive filenames: `.env`, `id_rsa`, `credentials`, `.npmrc`, …

Placeholders such as `YOUR_TOKEN`, `example`, `<paste here>` are ignored so
documentation does not trip the scanner. On any finding the push **aborts**.

To whitelist a deliberate false positive (for example a test fixture), append
`# secret-scan: ignore` to that line — the whole line is then skipped.

## 3. Output hygiene

- Diagnostics use `mask()` / `redact()`; full values never reach stdout or the
  `--json` report.
- The action report contains file paths, blob SHAs, and commit SHAs — no
  credentials.

## 4. Privacy

- Only files explicitly listed in `--files` are ever sent. Nothing is
  discovered or uploaded implicitly.
- Never author or commit personal data without the user's explicit intent.
