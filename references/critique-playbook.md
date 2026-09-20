# Critique playbook — pushing back when an instruction is risky

*中文要点：指令有误必须当场指出，用三段式——风险识别 / 推荐做法 / 原方案风险。*

Whenever an instruction is risky, do **not** silently comply and do **not**
silently refuse. Respond in this fixed shape:

```
⚠️ Risk        : <what is dangerous, in one line>
✅ Recommended : <the safer, standard alternative>
📉 Consequence : <concrete downside of the original request>
```

Then wait for the user to confirm. The user owns the repository; the final
decision is theirs, but the warning is mandatory.

## Catalogue

| # | Risky instruction | Flag & recommended alternative |
|---|---|---|
| 1 | Force-push to `main` / protected branch | Refuse by default → branch + PR |
| 2 | Bump major version for a doc-only change | SemVer violation → use patch/minor |
| 3 | Push a set containing `.env` / token / key | secret_scan blocks → remove + rotate the secret |
| 4 | Mass-delete tags / releases / branches | Irreversible → require explicit double confirmation |
| 5 | Delete the repository | Strongly refuse → explain total, unrecoverable loss |
| 6 | Push to an unexpected owner/repo | Stop → confirm `owner/repo` matches intent |
| 7 | Long/scheduled job with a near-expiry token | Warn → renew the token first |
| 8 | Commit large binaries / huge files | Warn → Git LFS or external storage |
| 9 | "Push everything" without review | Force a dry-run listing first |
| 10 | Skip secret scan via `--no-secret-scan` | Warn → require explicit acknowledgement |
| 11 | Insufficient token scope (e.g. `public_repo` on a private repo) | Diagnose the 403 → request the missing scope |
| 12 | Rewrite history on a shared branch | Warn → impacts collaborators; prefer new commits |
| 13 | Add a GPL license to an MIT project | Surface the conflict → ask the user to decide |
| 14 | Publish a repo with unattributed third-party code | Trigger `publish_audit.py` → resolve attribution first |

## Worked example (#1)

User: "just force-push my fix to main."

```
⚠️ Risk        : main is the shared default branch; force-push rewrites its history.
✅ Recommended : push to a branch and open a PR, or fast-forward only.
📉 Consequence : collaborators' clones break, commits are lost, and it may be
                 blocked by branch protection.
```

## Worked example (#2)

User: "I fixed a typo, bump v1.0.0 to v2.0.0."

```
⚠️ Risk        : a major bump signals breaking changes that don't exist here.
✅ Recommended : bump the patch (v1.0.1) for a docs-only change. Per this
                 conversation's rule, only bump when explicitly requested.
📉 Consequence : downstream users over-react to a false breaking change.
```

## Tone

State the risk factually, not alarmingly. Offer the alternative first. Do not
moralise; do not repeat the warning after the user has acknowledged it.
