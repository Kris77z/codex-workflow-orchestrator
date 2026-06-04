# Codex Agent 工作流优化器

一份用于优化 Codex 工作流的本地 Skill。它会安装一套可复用的 Codex Subagents 默认配置，并把复杂开发拆成两种更可控的模式：

- 小 Feature：`feature_coder` ↔ `feature_reviewer` 对抗闭环，最后 human review。
- 大 Feature：方案确认 → squad 实现 → 验收，人主要介入阶段 1 和阶段 3。

核心目标：减少上线后问题，让 Codex 不只是“会写代码”，而是按工程流程先查证、再判断、再实现、最后验收。

## 解决什么问题

日常使用 Codex 时，复杂任务很容易出现这些问题：

- 没看清真实代码链路就开始改。
- 小需求缺少 reviewer 对抗，隐藏 bug 容易进主线。
- 大需求一开始就写代码，方案、边界、验收标准都没确认。
- 没看日志、payload、fallback path 就判断根因。
- PR 或上线前缺少独立风险审查。
- 第三方 API / SDK 行为靠记忆判断。
- UI bug 没有复现步骤、console、network、截图证据。
- 验收阶段只有“代码能跑”，没有逐项证据和 Go/No-Go。

这份 Skill 的目标是把这些高频动作固化成可复用的 agents 和工作流。

## 默认安装的 Agents

### 工作流 Agents

#### `solution_planner`

大 Feature 方案确认 Agent。

只做需求边界、现有链路、推荐方案、验收标准、测试计划和风险清单，不写业务代码。

#### `squad_lead`

大 Feature 实现阶段的 squad 控制 Agent。

负责拆任务、排依赖、维护实现状态和风险，不负责放宽需求边界，也不能跳过 reviewer。

#### `feature_coder`

小 Feature 或大 Feature 子任务实现 Agent。

负责最小改动、必要测试、修复 reviewer blocker。它可以写代码，但必须控制范围。

#### `feature_reviewer`

对抗式 Feature Reviewer。

专门审查 diff、边界、回归、安全、数据兼容和缺失测试。不能只说“看起来没问题”，必须给证据和结论。

#### `acceptance_checker`

验收 Agent。

按已确认的验收标准逐项验证，输出测试结果、关键证据、剩余风险和 Go/No-Go 建议。

### 通用取证 Agents

#### `code_explorer`

只读代码链路梳理 Agent。

用于改代码前确认真实入口、调用链、字段流转、影响文件和风险点。

#### `risk_reviewer`

上线或 PR 前风险审查 Agent。

聚焦真实 bug、行为回归、安全风险、数据兼容问题和缺失测试。

#### `log_investigator`

日志和运行链路排查 Agent。

专门看日志、request payload、response、fallback path、代理链、runner 状态。

#### `docs_checker`

官方文档 / API 契约核对 Agent。

用于查 OpenAI、SDK、第三方 API、框架行为等官方来源，避免凭记忆判断版本、参数和行为差异。

#### `ui_reproducer`

UI / browser 复现 Agent。

用于复现前端 bug，采集操作步骤、实际表现、期望表现、console error、network 请求和截图证据。

## 工作流一：小 Feature 对抗闭环

适合范围明确、改动小、风险中低的任务。

```text
Human 给需求和边界
  ↓
feature_coder 实现最小改动
  ↓
feature_reviewer 对抗审查
  ↓
feature_coder 修复 blocker
  ↓
feature_reviewer 复审
  ↓
Human 最后 review
```

硬规则：

- 最多 3 轮 coder-reviewer 循环。
- 仍未收敛就交给 human 判断，不继续空转。
- reviewer 必须基于 diff、测试、日志或真实代码路径提出问题。
- coder 不允许无视 blocker，也不允许扩大需求。
- 最终输出 human review 摘要：改动、测试、风险、未解决项。

推荐提示词：

```text
这是小 Feature。请按 small_feature_duel 执行：feature_coder 实现，feature_reviewer 对抗审查，最多 3 轮，最后给我 human review 摘要。
```

## 工作流二：大 Feature 阶段门控

适合跨模块、跨仓库、上线风险较高、需求需要先收敛的任务。

```text
阶段 1：方案确认，人主导
  ↓
阶段 2：Squad 实现，agent 主导
  ↓
阶段 3：验收，人主导
```

### 阶段 1：方案确认

这个阶段只确认方案，不写业务代码。

推荐使用：

- `solution_planner`
- `code_explorer`
- `docs_checker`
- `risk_reviewer`

必须产出：

- 需求边界
- 当前代码真实状态
- 推荐方案
- 明确不做什么
- 验收标准
- 测试计划
- 风险清单

推荐提示词：

```text
这是大 Feature。先按 large_feature_squad 的阶段 1 做方案确认，不要改代码。输出需求边界、方案、验收标准、测试计划和风险清单。
```

### 阶段 2：Squad 实现

方案被 human 确认后，才进入实现。

推荐使用：

- `squad_lead`
- `feature_coder`
- `feature_reviewer`
- 按需使用 `ui_reproducer`、`log_investigator`、`docs_checker`

硬规则：

- 每个子任务都要经过 reviewer。
- 没有 reviewer 复审，不允许声称完成。
- agent 不允许自己扩大阶段 1 的需求边界。
- 发现方案不成立，要回到 human，而不是强行写完。

推荐提示词：

```text
方案已确认，进入 large_feature_squad 阶段 2。请按子任务实现，每个子任务都经过 feature_reviewer 复审。
```

### 阶段 3：验收

实现完成后按阶段 1 的验收标准逐项验证。

推荐使用：

- `acceptance_checker`
- `risk_reviewer`
- 涉及 UI 时加 `ui_reproducer`
- 涉及日志或线上问题时加 `log_investigator`

必须输出：

- 验收项逐项结果
- 运行的测试或复现步骤
- 关键证据
- 未解决风险
- Go/No-Go 建议

推荐提示词：

```text
进入验收。请用 acceptance_checker 按阶段 1 的验收标准逐项验证，最后给 Go/No-Go。
```

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
- 创建 10 个全局 agents 到 `~/.codex/agents/`

默认写入的全局配置：

```toml
[agents]
max_threads = 6
max_depth = 1
job_max_runtime_seconds = 1800
```

## 给项目补充 AGENTS.md 规则

给某个项目补充或升级 Subagents 协作规则：

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

安装脚本会新增或替换项目 `AGENTS.md` 里的 `## Subagents 使用规则`。

## 推荐协作规则

安装脚本会写入下面这段：

```md
## Subagents 使用规则

- 默认单 Agent 执行；只有任务可并行、需要独立审查、需要复现取证、或进入明确工作流时才启用 subagents。
- 小 Feature 使用 `small_feature_duel`：`feature_coder` 和 `feature_reviewer` 最多 3 轮对抗闭环，最后交给 human review。
- 大 Feature 使用 `large_feature_squad`：先方案确认，再 squad 实现，最后验收；human 主要介入阶段 1 和阶段 3。
- 阶段 1 只确认方案，不写业务代码，必须产出验收标准和测试计划。
- 阶段 2 每个子任务必须经过 reviewer，不能跳过复审。
- 阶段 3 必须按验收标准逐项验证；没有证据不允许给 Go。
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
- 小 Feature 通过 coder-reviewer 对抗提高细节质量。
- 大 Feature 通过阶段门控降低方向和验收风险。
- Subagents 负责独立取证、审查、复现、查文档。
- 默认只读；只有 coder、UI 复现、验收取证允许 workspace-write。
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
