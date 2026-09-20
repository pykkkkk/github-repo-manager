# Quickstart

*中文要点：5 步走完「连接 → 预演 → 推送」。*

All commands are pure standard library; run them with any Python 3.10+.
Nothing writes to GitHub until you pass `--yes`.

## 0. Connect a GitHub account (once per session)

Create a token at <https://github.com/settings/tokens>:
- **classic**: scope `repo` (private) or `public_repo` (public only)
- **fine-grained**: *Contents: Read and write* on the target repository

Then expose it in the environment (never in a file):

```bash
# bash / zsh
export GH_TOKEN=your_token_here
# PowerShell
$env:GH_TOKEN = "your_token_here"
```

Verify the token authenticates:

```bash
python scripts/detect_env.py --root . --net
```

`token_env` should name `GH_TOKEN` and `recommended_channel` should be `git`
or `rest`. If `need_token` is `true`, **the skill will ask you for a token** --
paste one, then export it as `GH_TOKEN`. On a terminal you can instead let the
script prompt you with hidden input: `python scripts/push_repo.py ... --ask-token`.

## 1. See what the environment supports

```bash
python scripts/detect_env.py --root .
```

## 2. Preview a push (dry-run, the default)

```bash
python scripts/push_repo.py --repo owner/name --root . \
    --files README.md docs/guide.md -m "docs: update guide"
```

Output lists each file as `create / update / unchanged` — nothing is sent.

## 3. Push for real

```bash
python scripts/push_repo.py --repo owner/name --root . \
    --files README.md docs/guide.md -m "docs: update guide" --yes
```

## 4. Or open a pull request instead

```bash
python scripts/push_repo.py --repo owner/name --root . \
    --files README.md --mode pr --pr-branch update/readme \
    -m "docs: readme" --yes
```

## 5. Before publishing a new repo, audit it

```bash
python scripts/publish_audit.py --root .
```

Resolve any blocking flags, then ask the user which license to use.

## Validate the skill itself

```bash
python scripts/selftest.py      # offline, no token, no network
```

Expected: `RESULT <n>/<n> passed`.
