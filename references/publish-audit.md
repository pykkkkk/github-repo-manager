# Publish audit — the pre-publication gate

*中文要点：发布新仓库前先审计——社区规则 / 版权 / 许可证；技能只把关，决定权在用户。*

Run `scripts/publish_audit.py --root .` **before** creating a new public
repository or making a private project public. It reports, and returns the
questions the skill must ask. It never chooses a license for the user.

## What it checks

### 1. Community / ToS risk
- Filenames that suggest disallowed content (`keygen`, `crack`, `exploit`,
  `malware`, `phishing`, `stealer`, `botnet`, `ransomware`, `trojan`, `ddos`, …)
- Executables / scripts (`*.exe`, `*.dll`, `*.so`, `*.bat`, `*.ps1`, …) that
  deserve a manual look
- Oversized files (> 50 MB) that should not live in Git

### 2. Credentials
- `.env`, `id_rsa`, `credentials`, `.npmrc`, `.pypirc`, … — must never ship

### 3. Copyright / license
- Existing `LICENSE` / `COPYING` / `NOTICE` files and the license they match
  (MIT / Apache-2.0 / GPL-3.0 / BSD-3-Clause / unknown)
- Third-party / vendored directories (`node_modules`, `vendor`, `third_party`, …)
- Source files carrying `Copyright (c)`, `SPDX-License-Identifier`, … headers

## What the skill must then do

1. Present the findings plainly.
2. **Ask the user which license to publish under** (MIT / Apache-2.0 /
   GPL-3.0 / proprietary / other) — do not decide.
3. If third-party code is present, ask the user to confirm attribution and
   license compatibility.
4. Proceed only after blocking flags (community, credentials) are resolved
   **and** the user has chosen a license.

## License quick guide

| License | Use when |
|---|---|
| MIT | Maximum reuse, minimal conditions (most open-source tooling) |
| Apache-2.0 | Like MIT, plus an explicit patent grant |
| GPL-3.0 | You want derivatives to stay open (copyleft) |
| BSD-3-Clause | Permissive, no endorsement clause |
| Proprietary | You are not granting reuse rights |

Conflict rule of thumb: permissive code (MIT/BSD/Apache) may be included in a
GPL project, but GPL code may **not** be relicensed as MIT. Flag any mixture
and let the user resolve it.
