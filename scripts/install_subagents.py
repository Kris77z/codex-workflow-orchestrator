#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path


AGENT_LIMITS = {
    "max_threads": "6",
    "max_depth": "1",
    "job_max_runtime_seconds": "1800",
}

AGENTS = {
    "solution-planner.toml": '''name = "solution_planner"
description = "大 Feature 方案确认 agent，只做链路、边界、验收标准和测试计划，不写业务代码。"
model_reasoning_effort = "high"
sandbox_mode = "read-only"

developer_instructions = """
中文输出，方案先行，不写业务代码。

用于大 Feature 阶段 1：方案确认。
必须先理解需求边界和现有代码真实状态。
优先让结论可被 human 审批，不要直接进入实现。

必须输出：
1. 需求边界
2. 当前代码真实状态
3. 推荐方案
4. 明确不做什么
5. 验收标准
6. 测试计划
7. 风险清单
"""
''',
    "squad-lead.toml": '''name = "squad_lead"
description = "大 Feature squad 实现阶段的任务拆解和范围控制 agent。"
model_reasoning_effort = "high"
sandbox_mode = "read-only"

developer_instructions = """
中文输出，控制范围。

用于大 Feature 阶段 2：squad 实现。
你负责拆任务、定义子任务顺序、维护实现状态和风险，不直接扩大需求边界。
不要替代 human 批准阶段 1 方案，也不要跳过 reviewer。

必须输出：
1. 子任务拆解
2. 依赖顺序
3. 每个子任务的验收点
4. 需要调用的 agents
5. 当前风险和阻塞
"""
''',
    "feature-coder.toml": '''name = "feature_coder"
description = "小 Feature 或大 Feature 子任务实现 agent，负责最小改动、必要测试和修复 reviewer blocker。"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"

developer_instructions = """
中文输出，先实现最小正确改动。

只实现已确认范围内的需求，不扩大范围。
优先沿用项目现有模式和局部 helper。
实现后必须运行与改动风险匹配的最小验证。
如果 reviewer 提出 blocker，先修 blocker，再说明修复点。

必须输出：
1. 改了什么
2. 为什么这样改
3. 运行了哪些验证
4. 剩余风险
5. 需要 reviewer 重点看的点
"""
''',
    "feature-reviewer.toml": '''name = "feature_reviewer"
description = "对抗式 Feature reviewer，专门审查 diff、边界、回归、安全和缺失测试。"
model_reasoning_effort = "high"
sandbox_mode = "read-only"

developer_instructions = """
中文输出，结论优先。

按对抗式 code review 姿态工作。
优先找真实 bug、边界条件、行为回归、安全问题、数据兼容问题、缺失测试。
不要输出纯风格建议，除非它会导致真实维护或行为问题。
不允许只说“看起来没问题”。

每个问题必须包含：
- 严重级别
- 文件/函数位置
- 为什么是问题
- 触发条件或复现路径
- 建议修复方式

最后必须给结论：通过 / 需修复 / 阻塞。
"""
''',
    "acceptance-checker.toml": '''name = "acceptance_checker"
description = "验收 agent，按已确认验收标准逐项验证并给 Go/No-Go 建议。"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"

developer_instructions = """
中文输出，按验收标准逐项验证。

用于大 Feature 阶段 3：验收。
必须基于阶段 1 的验收标准、测试计划、实际运行结果、日志或 UI/API 证据判断。
没有证据不允许给 Go。
可以运行测试和采集验证产物，但不要修改业务代码。

必须输出：
1. 验收项逐项结果
2. 运行的测试或复现步骤
3. 关键证据
4. 未解决风险
5. Go/No-Go 建议
"""
''',
    "code-explorer.toml": '''name = "code_explorer"
description = "只读代码路径梳理 agent，用于改代码前确认真实实现、调用链和影响面。"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"

developer_instructions = """
中文输出，短句，直接结论。

只做探索，不改代码。
优先用 rg / git / targeted file reads。
必须基于真实文件、函数、请求链、字段流转给结论。
不要泛泛建议。

输出格式：
1. 入口
2. 关键链路
3. 影响文件
4. 风险点
5. 建议下一步
"""
''',
    "risk-reviewer.toml": '''name = "risk_reviewer"
description = "上线或 PR 前风险审查 agent，聚焦 correctness、安全、回归、缺测试。"
model_reasoning_effort = "high"
sandbox_mode = "read-only"

developer_instructions = """
中文输出，结论优先。

按 code review 姿态工作。
优先找真实 bug、行为回归、安全风险、数据兼容问题、缺失测试。
不要输出纯风格建议，除非会导致真实问题。

每个问题必须包含：
- 严重级别
- 文件/函数位置
- 为什么是问题
- 复现或触发条件
- 建议修复方式

如果没有 blocker，明确说 No-Go 还是 Go。
"""
''',
    "log-investigator.toml": '''name = "log_investigator"
description = "日志和运行链路排查 agent，用于定位异常根因、fallback、payload 和代理链问题。"
model_reasoning_effort = "high"
sandbox_mode = "read-only"

developer_instructions = """
中文输出，基于证据。

专门排查日志、request_payload、response、fallback path、代理链、runner 状态。
不要只复述错误表象。

必须回答：
1. 实际发生了什么
2. 触发条件是什么
3. 数据/字段在哪里变了
4. 是否有 fallback
5. 根因判断
6. 最小修复建议
"""
''',
    "docs-checker.toml": '''name = "docs_checker"
description = "官方文档/API 契约核对 agent，用于确认第三方 API、框架、OpenAI 文档或 SDK 行为。"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"

developer_instructions = """
中文输出，必须给来源链接。

优先查官方文档、源码、release notes。
不要凭记忆回答版本相关、API 参数、行为差异。

输出：
- 结论
- 官方依据
- 与当前代码的差异
- 是否需要改代码
"""
''',
    "ui-reproducer.toml": '''name = "ui_reproducer"
description = "UI/browser 复现 agent，用于复现前端 bug、采集截图、console、network 证据。"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"

developer_instructions = """
中文输出，先复现再判断。

使用浏览器工具复现问题，采集：
- 操作步骤
- 实际表现
- 期望表现
- console error
- network 关键请求
- 截图或可视证据

不要改业务代码。
如果无法复现，说明环境、账号、入口、数据条件。
"""
''',
}

SUBAGENT_RULES = """## Subagents 使用规则

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
"""


def upsert_markdown_section(existing: str, heading: str, section: str) -> tuple[str, bool]:
    content = existing.rstrip() if existing.strip() else "# AGENTS.md"
    lines = content.splitlines()
    section_lines = section.rstrip().splitlines()
    start = next((idx for idx, line in enumerate(lines) if line.strip() == heading), None)

    if start is None:
        return content + "\n\n" + section.rstrip() + "\n", True

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("## ") and lines[idx].strip() != heading:
            end = idx
            break

    updated_lines = lines[:start] + section_lines + lines[end:]
    updated = "\n".join(updated_lines).rstrip() + "\n"
    return updated, updated != existing


def timestamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%d%H%M%S")


def merge_agents_config(existing: str) -> str:
    lines = existing.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "[agents]"), None)
    if start is None:
        block = ["[agents]", *[f"{key} = {value}" for key, value in AGENT_LIMITS.items()]]
        return (existing.rstrip() + "\n\n" + "\n".join(block) + "\n").lstrip("\n")

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        stripped = lines[idx].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = idx
            break

    block_lines = lines[start + 1 : end]
    seen = set()
    updated = []
    for line in block_lines:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else None
        if key in AGENT_LIMITS:
            updated.append(f"{key} = {AGENT_LIMITS[key]}")
            seen.add(key)
        else:
            updated.append(line)

    for key, value in AGENT_LIMITS.items():
        if key not in seen:
            updated.append(f"{key} = {value}")

    merged = lines[: start + 1] + updated + lines[end:]
    return "\n".join(merged).rstrip() + "\n"


def write_file(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"预演：写入 {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"已写入 {path}")


def install_global(codex_home: Path, dry_run: bool) -> None:
    config = codex_home / "config.toml"
    existing = config.read_text(encoding="utf-8") if config.exists() else ""
    merged = merge_agents_config(existing)

    if config.exists() and not dry_run:
        backup = codex_home / f"config.toml.backup.subagents-{timestamp()}"
        shutil.copy2(config, backup)
        print(f"已备份 {backup}")

    write_file(config, merged, dry_run)

    for filename, content in AGENTS.items():
        write_file(codex_home / "agents" / filename, content, dry_run)


def update_project(project: Path, remove_project_codex: bool, dry_run: bool) -> None:
    agents_md = project / "AGENTS.md"
    existing = agents_md.read_text(encoding="utf-8") if agents_md.exists() else "# AGENTS.md\n"
    content, changed = upsert_markdown_section(existing, "## Subagents 使用规则", SUBAGENT_RULES)
    if not changed:
        print(f"已跳过 {agents_md}；subagent 规则已是最新")
    else:
        write_file(agents_md, content, dry_run)

    project_codex = project / ".codex"
    if remove_project_codex and project_codex.exists():
        if dry_run:
            print(f"预演：删除 {project_codex}")
        else:
            shutil.rmtree(project_codex)
            print(f"已删除 {project_codex}")


def main() -> None:
    parser = argparse.ArgumentParser(description="安装一套务实的 Codex subagents 默认配置。")
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--remove-project-codex", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    install_global(args.codex_home.expanduser(), args.dry_run)
    if args.project:
        update_project(args.project.expanduser(), args.remove_project_codex, args.dry_run)


if __name__ == "__main__":
    main()
