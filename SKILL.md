---
name: codex-subagents-optimizer
description: 用于优化 Codex agent 工作流，安装可复用的自定义 subagents、全局 agents 配置和 AGENTS.md 协作规则；适合给自己或他人配置小 Feature 的 coder-reviewer 对抗闭环，以及大 Feature 的方案确认、squad 实现、验收门控流程。
metadata:
  short-description: 配置 Codex agent 工作流
---

# Codex Agent 工作流优化器

使用这个 skill 安装或调整一套务实的 Codex subagents 与工作流配置。

核心原则：小功能用对抗闭环提质量；大功能用阶段门控控风险。

## 安装内容

默认会创建 10 个全局自定义 agents：

- `solution_planner`：大 Feature 方案确认，只做链路、边界、验收标准和测试计划，不写业务代码。
- `squad_lead`：大 Feature 实现阶段的任务拆解和范围控制，维护 squad 状态，不放宽需求边界。
- `feature_coder`：小 Feature 或子任务实现 agent，负责最小改动、必要测试和修复 reviewer blocker。
- `feature_reviewer`：对抗式 reviewer，专门审查 diff、边界、回归、安全和缺失测试。
- `acceptance_checker`：验收 agent，按验收标准逐项验证并给 Go/No-Go 建议。
- `code_explorer`：改代码前只读梳理代码路径、调用链和影响面。
- `risk_reviewer`：合并或上线前只读审查 bug、安全、回归和缺失测试。
- `log_investigator`：只读排查日志、payload、fallback path、代理链等根因。
- `docs_checker`：只读核对官方文档和 API 契约。
- `ui_reproducer`：浏览器/UI 复现和证据采集；允许 workspace-write 仅用于保存取证产物。

同时写入保守的全局 agents 限制：

```toml
[agents]
max_threads = 6
max_depth = 1
job_max_runtime_seconds = 1800
```

## 快速安装

在 skill 目录下运行内置安装脚本：

```bash
python3 scripts/install_subagents.py
```

常用参数：

```bash
python3 scripts/install_subagents.py --codex-home /path/to/.codex
python3 scripts/install_subagents.py --project /path/to/repo
python3 scripts/install_subagents.py --project /path/to/repo --remove-project-codex
python3 scripts/install_subagents.py --dry-run
```

## 小 Feature：Coder ↔ Reviewer 对抗闭环

适合范围明确、改动小、风险中低的任务。

流程：

1. Human 给需求和边界。
2. `feature_coder` 实现最小可行改动。
3. `feature_reviewer` 基于 diff、测试、日志或真实代码路径找问题。
4. `feature_coder` 修复 reviewer blocker。
5. `feature_reviewer` 复审。
6. 主 Agent 输出 human review 摘要。

硬规则：

- 最多 3 轮 coder-reviewer 循环；仍未收敛就交给 human。
- reviewer 不允许只说“看起来没问题”，必须给证据和结论。
- coder 不允许无视 blocker，也不允许扩大需求。
- 最终摘要必须包含：改动、测试、风险、未解决项。

## 大 Feature：方案确认 → Squad 实现 → 验收

适合跨模块、跨仓库、上线风险较高、需求还需要收敛的任务。

阶段 1：方案确认，人主导。

- 启动 `solution_planner`、`code_explorer`、`docs_checker`、`risk_reviewer`。
- 只确认方案，不写业务代码。
- 产出需求边界、真实代码状态、推荐方案、不做什么、验收标准、测试计划、风险清单。
- Human 确认后才能进入实现。

阶段 2：Squad 实现，agent 主导。

- 主 Agent 或 `squad_lead` 拆任务、控范围、维护状态。
- `feature_coder` 负责子任务实现。
- `feature_reviewer` 对每个子任务复审。
- 按需使用 `ui_reproducer`、`log_investigator`、`docs_checker` 补证据。
- 没有 reviewer 复审，不允许声称完成。

阶段 3：验收，人主导。

- 启动 `acceptance_checker` 按阶段 1 的验收标准逐项验证。
- 输出证据、测试结果、剩余风险和 Go/No-Go 建议。
- Human 做最终验收和上线判断。

## AGENTS.md 推荐规则

更新项目 `AGENTS.md` 时，如果项目还没有同等规则，加入或替换下面这段：

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

## 典型调用

```text
这是小 Feature。请按 small_feature_duel 执行：feature_coder 实现，feature_reviewer 对抗审查，最多 3 轮，最后给我 human review 摘要。
```

```text
这是大 Feature。先按 large_feature_squad 的阶段 1 做方案确认，不要改代码。输出需求边界、方案、验收标准、测试计划和风险清单。
```

```text
方案已确认，进入 large_feature_squad 阶段 2。请按子任务实现，每个子任务都经过 feature_reviewer 复审。
```

```text
进入验收。请用 acceptance_checker 按阶段 1 的验收标准逐项验证，最后给 Go/No-Go。
```

最终汇总和决策始终由主 Agent 负责。
