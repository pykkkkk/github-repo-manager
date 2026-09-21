<div align="center">

<img src="./assets/icon.png" alt="github-repo-manager" width="150">

# github-repo-manager

**你仓库里的常驻机器人——对安全一丝不苟，对你绝对忠诚，在你即将做出会后悔的操作时及时开口。**

一个用于维护并发布**你自己的** GitHub 仓库的 智能体 **技能（skill）**。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](./CHANGELOG.md)
[![Dependencies](https://img.shields.io/badge/dependencies-none%20(stdlib)-brightgreen.svg)](#)

🌐 **语言：** [English (README.md)](./README.md) · 中文

</div>

---

## 一句话概括

把 GitHub 自动化做**糟**很容易。只会听命推送的机器人是负债；**谨慎地**推送
的机器人是资产。本技能只做一件窄而深的事——维护并发布你的仓库——并由四条不
可妥协的特质支撑：**随环境自适配**、**保护你的凭据**、**只做你要求的事**、**在
危险操作前开口**。不涉及 Packages、Actions 编排、组织管理。一件事，做到透彻。

## 它管理什么

| 领域 | 机器人做什么 |
|---|---|
| **推送变更** | 有 git 用 git，否则用 GitHub **Git Data API**——一次干净、幂等的提交 |
| **Pull Request** | 建分支 → 推送 → 开 PR；**绝不自动合并** |
| **Release 与 Tag** | **仅在你要求时**发版；按需更新 `VERSION` 与 `CHANGELOG` |
| **发布新仓库** | 审计 → 选定许可证 → 建仓 → 初始提交，端到端完成 |
| **连接账号** | 主动向你索取 token、验证后临时使用 |
| **护栏** | 推送前密钥扫描、默认 dry-run、危险指令提示 |

## 四支柱

把它们想成机器人的性格。

| 支柱 | 性格 | 具体表现 |
|---|---|---|
| **普适** | *自适配* | 先探测环境，再按 **git → REST → 失败** 回退链选通道。不写死"必须有 git"。 |
| **安全** | *谨慎* | token 只读环境变量、逐行掩码、绝不落盘；每次推送前扫描密钥。 |
| **忠诚** | *服从* | 仓库是你的。最小行动原则：默认只读；**未经要求不发版、不改版本号**。 |
| **批判** | *诚实* | 动作有风险时**先开口**，固定格式：⚠️ 风险 / ✅ 推荐 / 📉 后果。 |

## 工作流

```
  理解请求  →  探测环境  →  批判审查  →  密钥扫描  →  dry-run  →  推送  →  （发版）
      │           │            │            │            │         │         │
   仓库/文件   git? rest?   有风险?告警   泄密?中止    展示计划   --yes   仅当你要求
```

每一步都可见。**在你加上 `--yes` 之前，不会有任何写入。**

## 机器人会拒绝的事

批判性，也带点趣味。完整清单有 14 条，这里挑三条：

> **你：** "直接把修复 force-push 到 `main`。"
>
> **机器人：**
> ⚠️ *风险* —— `main` 是共享分支，force-push 会重写其历史。
> ✅ *推荐* —— 推到分支并开 PR，或仅做快进。
> 📉 *后果* —— 协作者的本地副本损坏，提交丢失。

> **你：** "我修了个错别字，把 `v1.0.0` 升到 `v2.0.0`。"
>
> **机器人：**
> ⚠️ *风险* —— 主版本号意味着破坏性变更，但这里并没有。
> ✅ *推荐* —— 纯文档改动应升补丁号（`v1.0.1`）。
> 📉 *后果* —— 下游用户会对一个并不存在的"破坏性变更"过度反应。

> **你：** "把所有文件都提交，包括 `.env`。"
>
> **机器人：**
> ⚠️ *风险* —— `.env` 通常存有真实凭据。
> ✅ *推荐* —— 移除该文件并轮换已泄露的密钥。
> 📉 *后果* —— 密钥会在数秒内公开，并被爬虫扫描。

以及——一旦需要 token，它会**主动向你索取**，而不是静默失败或凭空捏造。

## 安装

把本文件夹放入 WorkBuddy 技能目录：

```
~/.workbuddy/skills/github-repo-manager/
```

然后直接对它说：*"推送到 github""发个 release""发布我的仓库""连接我的 github"*。

## 快速开始

```bash
export GH_TOKEN=your_token_here                      # 只放环境变量，切勿写入文件

python scripts/detect_env.py --root .     --net      # 探测可用通道
python scripts/push_repo.py  --repo o/r --root . \
       --files README.md -m "docs: update"           # 预演（默认）
python scripts/push_repo.py  --repo o/r --root . \
       --files README.md -m "docs: update" --yes     # 真正推送

python scripts/create_repo.py --name my-repo --description "..."   # 发布（预演）
python scripts/publish_audit.py --root .             # 公开前的审计
python scripts/selftest.py                           # 离线自检（无需 token）
```

## Token 权限

| Token 类型 | 写权限 |
|---|---|
| Classic PAT | `repo`（私有）/ `public_repo`（仅公开） |
| Fine-grained PAT | 对目标仓库 *Contents: Read and write* |

> `403 "Resource not accessible by personal access token"` 表示 token 已通过鉴
> 权但**缺写权限**——请重新生成，而不是盲目重试。

## 设计说明（给好奇者）

- **零依赖**：纯 Python 标准库，无需 `pip install`。
- **幂等**：blob SHA 与远端一致的文件自动跳过，不产生空提交。
- **感知初始提交**：向全新的空仓库发布，用同一条命令即可完成。
- **凭据即用即弃**：git 通道把 token 作为 HTTP 头注入，绝不写进 remote URL
  或任何配置文件。
- **可自维护**：`update_skill.py check | update`，外加离线 `selftest.py`（29 项）。

## 能力边界（不做）

Packages / Container Registry、Actions *运行*、Issues triage、Discussions /
Wikis、组织与企业 admin、OAuth / GitHub Apps、Copilot。明确拒绝，而非临时发挥。

## 许可证

MIT —— 见 [LICENSE](./LICENSE)。

<div align="center"><sub>在该无聊的地方无聊：安全、诚实、且归你所有。</sub></div>
