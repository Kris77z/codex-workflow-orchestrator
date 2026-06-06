---
name: codex-workflow-orchestrator
description: 用于编排 Codex agent 工作流，安装可复用的自定义 agents、全局 agents 配置和 AGENTS.md 协作规则；适合给自己或他人配置小 Feature 的 coder-reviewer 对抗闭环、大 Feature 的方案确认/squad/验收门控，以及参考 threads 思路做多会话 lane/worktree 编排、独立 review 和 merge gate。
metadata:
  short-description: 配置 Codex workflow 编排规则
---

# Codex Workflow Orchestrator

使用这个 skill 安装或调整一套务实的 Codex agents 与 thread/lane 编排规则。

核心原则：

- 小功能用对抗闭环提质量。
- 大功能用阶段门控控风险。
- 多任务用 thread/lane 编排控所有权、验证和合并门禁。

## 心智模型

这个 skill 分两层：

```text
Orchestrator Thread（主会话，总控）
  -> Worker Thread / Review Thread / Research Thread（任务 lane）
      -> code_explorer / feature_coder / feature_reviewer / docs_checker ...
```

- **Thread/Lane**：一次独立工作线，负责一个 issue、PR、worktree、review、研究角度或 merge gate。
- **Subagent**：thread 内部调用的专家角色，负责查证、实现、审查、复现、验收。

不要把 subagent 当成完整会话编排。subagent 是能力层，thread/lane 是组织层。

## 安装内容

默认会创建 13 个全局自定义 agents：

### 编排与门控

- `thread_planner`：只读拆 lane，输出 lane map、worktree/file ownership、依赖顺序和 stop conditions。
- `merge_gate_reviewer`：只读合并门禁，检查最新 head、CI/checks、diff 范围、review 线程和剩余风险。
- `closure_auditor`：只读收尾审计，区分远端真实状态、本地 stale state、未关闭 review/issue/PR 和清理项。

### 工作流 agents

- `solution_planner`：大 Feature 方案确认，只做链路、边界、验收标准和测试计划，不写业务代码。
- `squad_lead`：大 Feature 实现阶段的任务拆解和范围控制，维护 squad 状态，不放宽需求边界。
- `feature_coder`：小 Feature 或子任务实现 agent，负责最小改动、必要测试和修复 reviewer blocker。
- `feature_reviewer`：对抗式 reviewer，专门审查 diff、边界、回归、安全和缺失测试。
- `acceptance_checker`：验收 agent，按验收标准逐项验证并给 Go/No-Go 建议。

### 通用取证 agents

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

## 工作流一：小 Feature 对抗闭环

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

## 工作流二：大 Feature 阶段门控

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

## 工作流三：多 Thread / Lane 编排

适合多个 issue/PR、并行实现、独立 review、研究拆分、review then merge、跨 worktree 工作。

### 决策模式

- `plan_only`：只拆队列、风险、依赖和并行度，不改代码。
- `execute_direct`：先规划，再执行一个或多个有边界的实现 lane。
- `review_only`：只读审查 PR、diff 或 worktree。
- `research_spec`：按研究角度拆只读 thread，最后合成 spec/issue。
- `clarify_first`：repo、目标、权限或完成标准缺失时先问清楚。

### Lane Map

任何实现前，主 Agent 必须先输出 lane map：

```text
mode:
repo:
base_ref:
global_constraints:
verification_owner:
stop_conditions:
lanes:
- id:
  role: planner | worker | reviewer | merge_reviewer | researcher | closure_auditor
  target:
  worktree:
  writable_files:
  forbidden_files:
  expected_output:
  verification:
```

规则：

- 先查 repo 指令、git 状态、dirty files、open issue/PR、CI 和相关代码。
- planner、reviewer、merge reviewer、closure auditor 默认只读。
- worker 必须有互不重叠的 `writable_files`；两个 worker 不能同时拥有同一文件。
- `AGENTS.md`、`CLAUDE.md`、settings、hooks、setup 脚本默认放进 `forbidden_files`，除非用户明确要求改。
- 优先使用已绑定目标分支的 worktree；否则从请求的 base 或 `origin/main` 创建干净 worktree。
- worker 不 merge；merge 必须经过独立 `merge_gate_reviewer`。
- 如果当前环境没有 native thread/subagent 工具，输出 lane map 和 handoff prompts，让用户手动开 thread，不要假装已并行执行。

### Thread 内部 Subagent 选择

- 规划 lane：`thread_planner`，按需补 `code_explorer`、`docs_checker`。
- 实现 lane：`feature_coder`，复杂链路先用 `code_explorer`。
- 审查 lane：`feature_reviewer` 或 `risk_reviewer`。
- UI lane：先 `ui_reproducer` 复现取证，再决定是否修改。
- 日志/payload/fallback lane：`log_investigator`。
- 第三方 API/SDK lane：`docs_checker` 查官方来源。
- 合并门禁：`merge_gate_reviewer`。
- 合并或关闭后：`closure_auditor`。

## Merge Gate

不要只凭 worker 输出 merge。合并前必须满足：

- 至少一个独立 review lane 已审查当前 diff/head。
- blocker 已修复，或用证据明确判定不是问题。
- 必要 checks 是 fresh 的，且绑定当前 head。
- GitHub review threads 已检查；不能只看普通 PR comments。
- 已修复的 review feedback 有回复或 thread 已 resolve，除非用户禁止写 GitHub。
- 最终答复能说清 PR、commit、变更文件和验证命令。

## AGENTS.md 推荐规则

更新项目 `AGENTS.md` 时，如果项目还没有同等规则，加入或替换安装脚本里的 `## Subagents 使用规则`。

## 典型调用

```text
这是小 Feature。请按 small_feature_duel 执行：feature_coder 实现，feature_reviewer 对抗审查，最多 3 轮，最后给我 human review 摘要。
```

```text
这是大 Feature。先按 large_feature_squad 的阶段 1 做方案确认，不要改代码。输出需求边界、方案、验收标准、测试计划和风险清单。
```

```text
这是多 issue/PR 队列。请按 thread_lanes 执行：先用 thread_planner 输出 lane map，能并行的分独立 worktree；每个实现 lane 必须有独立 reviewer，merge 前用 merge_gate_reviewer。
```

```text
只做 review_only。请开独立 review lane 审查 PR #123，输出 findings first；不要修改、提交或 merge。
```

更多 handoff 模板见 `references/thread-prompt-patterns.md`。

最终汇总和决策始终由主 Agent 负责。
