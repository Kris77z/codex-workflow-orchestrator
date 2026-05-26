# Codex Subagents 优化器

一份用于优化 Codex 工作流的本地 Skill。它会安装一套可复用的 Codex Subagents 默认配置，让 Codex 在复杂任务中按职责分工：主 Agent 负责判断和决策，Subagents 负责并行取证、审查、复现和文档核对。

适合想把 Codex 用得更工程化的人：先查证，再判断，再动手。

## 解决什么问题

日常使用 Codex 时，复杂任务很容易出现这些问题：

- 没看清真实代码链路就开始改。
- 没看日志、payload、fallback path 就判断根因。
- PR 或上线前缺少独立风险审查。
- 第三方 API / SDK 行为靠记忆判断。
- UI bug 没有复现步骤、console、network、截图证据。
- 多个项目之间缺少统一的 Codex 协作规则。

这份 Skill 的目标是把这些高频动作固化成 5 个通用 Subagents，并提供一键安装脚本。

## 默认安装的 Subagents

### `code_explorer`

只读代码链路梳理 Agent。

用于改代码前确认真实入口、调用链、字段流转、影响文件和风险点。它不会改代码，只负责把事实查清楚。

### `risk_reviewer`

上线或 PR 前风险审查 Agent。

聚焦真实 bug、行为回归、安全风险、数据兼容问题和缺失测试。适合在提交、合并、上线前多一层独立 review。

### `log_investigator`

日志和运行链路排查 Agent。

专门看日志、request payload、response、fallback path、代理链、runner 状态。要求给出根因判断和最小修复建议，避免只复述错误表象。

### `docs_checker`

官方文档 / API 契约核对 Agent。

用于查 OpenAI、SDK、第三方 API、框架行为等官方来源，避免凭记忆判断版本、参数和行为差异。

### `ui_reproducer`

UI / browser 复现 Agent。

用于复现前端 bug，采集操作步骤、实际表现、期望表现、console error、network 请求和截图证据。

## 安装

把这个仓库 clone 到本地 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/Kris77z/codex-subagents-optimizer.git ~/.codex/skills/codex-subagents-optimizer
```

然后运行安装脚本：

```bash
python3 ~/.codex/skills/codex-subagents-optimizer/scripts/install_subagents.py
```

安装脚本会：

- 备份已有的 `~/.codex/config.toml`
- 写入或合并全局 `[agents]` 配置
- 创建 5 个全局 Subagents 到 `~/.codex/agents/`

默认写入的全局配置：

```toml
[agents]
max_threads = 6
max_depth = 1
job_max_runtime_seconds = 1800
```

## 给项目补充 AGENTS.md 规则

如果还想给某个项目补充 Subagents 协作规则：

```bash
python3 ~/.codex/skills/codex-subagents-optimizer/scripts/install_subagents.py --project /path/to/repo
```

如果项目里已经有重复的 `.codex` 配置，并且确认要清理：

```bash
python3 ~/.codex/skills/codex-subagents-optimizer/scripts/install_subagents.py --project /path/to/repo --remove-project-codex
```

先预览会改什么：

```bash
python3 ~/.codex/skills/codex-subagents-optimizer/scripts/install_subagents.py --project /path/to/repo --dry-run
```

## 在 Codex 里使用

可以直接让 Codex 使用这个 Skill：

```text
使用 $codex-subagents-optimizer 为当前环境配置一套务实的 Codex subagents。
```

日常任务可以这样调用：

```text
先不要改代码。请用 code_explorer 梳理真实链路，再由 risk_reviewer 审查风险，最后你汇总结论和建议。
```

```text
这个线上异常先查根因。请用 log_investigator 看日志、payload、fallback path，你汇总根因，不要先改。
```

```text
这个 PR 准备上线。请并行使用 code_explorer、risk_reviewer、docs_checker 审查，最后给 Go/No-Go。
```

```text
这个 UI bug 先复现。请用 ui_reproducer 采集浏览器证据，再找对应代码路径，最后决定最小修复。
```

## 推荐协作规则

安装脚本可以自动给项目 `AGENTS.md` 追加这段规则：

```md
## Subagents 使用规则

- 默认单 Agent 执行；只有任务可并行、需要独立审查、需要复现取证时才启用 subagents。
- 改代码前，复杂任务优先让 `code_explorer` 只读梳理真实链路。
- 上线、PR、跨模块改动，使用 `risk_reviewer` 做独立审查。
- 日志、payload、fallback、代理链问题，使用 `log_investigator`。
- 涉及第三方 API、SDK、OpenAI、框架版本行为，使用 `docs_checker` 查官方来源。
- UI 问题先用 `ui_reproducer` 复现并采集证据，再决定是否修改。
- Subagent 默认不提交、不推送、不做破坏性操作。
- 主 Agent 必须汇总证据后再给最终结论。
```

## 设计原则

- 主 Agent 负责理解需求、控制范围、最终决策。
- Subagents 负责独立取证、审查、复现、查文档。
- 默认只读，除 UI 取证外不改代码。
- 不提交、不推送、不做破坏性操作。
- 所有结论必须基于真实文件、日志、请求链或官方来源。
- 控制并发和递归，避免 token 和时间失控。

## 校验

安装后可以运行：

```bash
python3 - <<'PY'
import tomllib
from pathlib import Path

home = Path.home() / ".codex"
for path in [home / "config.toml", *sorted((home / "agents").glob("*.toml"))]:
    with path.open("rb") as f:
        tomllib.load(f)
    print(f"OK {path}")
PY
```

看到 `OK` 即表示 TOML 配置可正常解析。

## 许可证

MIT
