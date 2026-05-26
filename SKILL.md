---
name: codex-subagents-optimizer
description: 用于优化 Codex 配置，安装可复用的自定义 subagents、全局 agents 配置和 AGENTS.md 协作规则；适合给自己或他人配置代码链路梳理、风险审查、日志排查、官方文档核对、UI 复现取证等工作流。
metadata:
  short-description: 配置可复用 Codex subagents
---

# Codex Subagents 优化器

使用这个 skill 安装或调整一套务实的 Codex subagents 配置。

## 安装内容

默认会创建 5 个全局自定义 agents：

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

## 使用流程

1. 如果用户没说清楚，先确认要配置全局、项目级，还是两者都要。
2. 全局配置：运行 `scripts/install_subagents.py`。
3. 项目规则：加 `--project /path/to/repo`，用于新增或更新 `AGENTS.md` 协作规则。
4. 如果项目内 `.codex/agents` 和全局 agents 重复，只有在用户同意或明确要求清理时，才使用 `--remove-project-codex`。
5. 用下面命令校验：

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

## AGENTS.md 推荐规则

更新项目 `AGENTS.md` 时，如果项目还没有同等规则，加入下面这段：

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

## 什么时候用哪个 Agent

- 风险较高的实现前：先启动 `code_explorer`，再决定最小改动。
- 合并或上线前：启动 `risk_reviewer`，由主 Agent 汇总后给 Go/No-Go。
- 线上异常：启动 `log_investigator`，要求给出 request、response、日志证据。
- API、SDK、版本行为不确定：启动 `docs_checker`，要求给官方来源链接。
- UI bug：启动 `ui_reproducer`，要求给复现步骤、console/network 证据，必要时附截图。

最终汇总和决策始终由主 Agent 负责。
