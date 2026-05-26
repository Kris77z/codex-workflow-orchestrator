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

- 默认单 Agent 执行；只有任务可并行、需要独立审查、需要复现取证时才启用 subagents。
- 改代码前，复杂任务优先让 `code_explorer` 只读梳理真实链路。
- 上线、PR、跨模块改动，使用 `risk_reviewer` 做独立审查。
- 日志、payload、fallback、代理链问题，使用 `log_investigator`。
- 涉及第三方 API、SDK、OpenAI、框架版本行为，使用 `docs_checker` 查官方来源。
- UI 问题先用 `ui_reproducer` 复现并采集证据，再决定是否修改。
- Subagent 默认不提交、不推送、不做破坏性操作。
- 主 Agent 必须汇总证据后再给最终结论。
"""


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
    if "## Subagents 使用规则" in existing:
        print(f"已跳过 {agents_md}；subagent 规则已存在")
    else:
        content = existing.rstrip() + "\n\n" + SUBAGENT_RULES
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
