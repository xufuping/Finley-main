#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Finley 记忆层 —— 在一段工作收尾时把「本次会话做了什么」写进 journal。

用法：
    python .finley/scripts/add_session.py --title "标题" --summary "一句话总结"
    python .finley/scripts/add_session.py --title "标题" --commit "abc123,def456" --summary "..."
    python .finley/scripts/add_session.py --title "标题" --developer alice   # 指定开发者
    cat detail.md | python .finley/scripts/add_session.py --title "标题" --stdin

journal 写到 .finley/workspace/<开发者>/journal-N.md：
    - 开发者标识解析顺序：--developer > 环境变量 FINLEY_DEVELOPER
      > config.yaml 的 developer > git config user.name > 系统用户名。
    - 单个 journal 超过 config.yaml 的 journal.max_lines（默认 2000）行后，
      自动轮转到下一个 journal-(N+1).md。
    - 同时维护该开发者目录下的 index.md（会话总数 / 活跃文件 / 历史表）。

纯标准库实现（os / re / subprocess / argparse），不依赖任何第三方包。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

JOURNAL_PREFIX = "journal-"
DEFAULT_MAX_LINES = 2000


# =============================================================================
# 配置读取（复用极简 YAML 思路，仅取需要的两个字段）
# =============================================================================

def _read_config(repo_root: Path) -> dict:
    path = repo_root / ".finley" / "config.yaml"
    result = {"developer": "", "max_lines": DEFAULT_MAX_LINES}
    if not path.exists():
        return result

    in_journal = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            in_journal = stripped.startswith("journal:")
            if stripped.startswith("developer:"):
                val = stripped.split(":", 1)[1].strip().strip("'\"")
                if val:
                    result["developer"] = val
        elif in_journal and "max_lines" in stripped:
            m = re.search(r"(\d+)", stripped)
            if m:
                result["max_lines"] = int(m.group(1))
    return result


# =============================================================================
# 开发者与仓库定位
# =============================================================================

def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent  # .finley/scripts/ -> root


def _git(args: list[str], cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def resolve_developer(repo_root: Path, cli_value: str | None, config: dict) -> str:
    for candidate in (
        cli_value,
        os.environ.get("FINLEY_DEVELOPER"),
        config.get("developer"),
        _git(["config", "user.name"], repo_root),
        os.environ.get("USER") or os.environ.get("USERNAME"),
    ):
        if candidate and str(candidate).strip():
            # 规范化成适合作目录名的标识
            return re.sub(r"[^\w.\-]+", "-", str(candidate).strip())
    return "unknown"


def resolve_branch(repo_root: Path, cli_value: str | None) -> str | None:
    if cli_value:
        return cli_value
    branch = _git(["branch", "--show-current"], repo_root)
    return branch or None


# =============================================================================
# journal 文件管理
# =============================================================================

def get_latest_journal(dev_dir: Path) -> tuple[Path | None, int, int]:
    """返回 (最新 journal 路径, 编号, 行数)。目录为空时返回 (None, 0, 0)。"""
    latest_file: Path | None = None
    latest_num = -1
    for f in dev_dir.glob(f"{JOURNAL_PREFIX}*.md"):
        if not f.is_file():
            continue
        m = re.search(r"(\d+)$", f.stem)
        if m and int(m.group(1)) > latest_num:
            latest_num = int(m.group(1))
            latest_file = f
    if latest_file:
        lines = len(latest_file.read_text(encoding="utf-8").splitlines())
        return latest_file, latest_num, lines
    return None, 0, 0


def create_journal_file(dev_dir: Path, num: int, developer: str, today: str, max_lines: int) -> Path:
    new_file = dev_dir / f"{JOURNAL_PREFIX}{num}.md"
    if num <= 1:
        cont_line = f"> 单文件约 {max_lines} 行后自动轮转到下一个 journal\n"
    else:
        cont_line = f"> 续自 `{JOURNAL_PREFIX}{num - 1}.md`（约 {max_lines} 行后轮转）\n"
    header = (
        f"# Journal - {developer} (Part {num})\n\n"
        f"{cont_line}"
        f"> 起始：{today}\n\n---\n"
    )
    new_file.write_text(header, encoding="utf-8")
    return new_file


def get_session_count(index_file: Path) -> int:
    if not index_file.is_file():
        return 0
    for line in index_file.read_text(encoding="utf-8").splitlines():
        if "会话总数" in line or "Total Sessions" in line:
            m = re.search(r"[:：]\s*(\d+)", line)
            if m:
                return int(m.group(1))
    return 0


def build_session_block(
    session_num: int, title: str, today: str, task: str, summary: str,
    detail: str, commit: str, branch: str | None,
) -> str:
    if commit and commit != "-":
        rows = "\n".join(
            f"| `{c.strip()}` | (见 git log) |" for c in commit.split(",") if c.strip()
        )
        commit_table = "| Hash | 说明 |\n|------|------|\n" + rows
    else:
        commit_table = "（无提交 / 规划性会话）"

    branch_line = f"\n**Branch**: `{branch}`" if branch else ""

    return (
        f"\n\n## Session {session_num}: {title}\n\n"
        f"**日期**: {today}\n"
        f"**Task**: {task}{branch_line}\n\n"
        f"### Summary\n\n{summary}\n\n"
        f"### 主要改动\n\n{detail}\n\n"
        f"### Git Commits\n\n{commit_table}\n\n"
        f"### 状态\n\n✅ 已完成\n"
    )


def write_index(index_file: Path, active_file: str, session_num: int, today: str,
                title: str, commit: str, branch: str | None, developer: str) -> None:
    commit_disp = "-"
    if commit and commit != "-":
        commit_disp = re.sub(r"([0-9a-f]{7,})", r"`\1`", commit.replace(",", ", "))
    branch_disp = f"`{branch}`" if branch else "-"

    header = (
        f"# Journal 索引 - {developer}\n\n"
        f"## 当前状态\n\n"
        f"- **活跃文件**: `{active_file}`\n"
        f"- **会话总数**: {session_num}\n"
        f"- **最近活跃**: {today}\n\n"
        f"## 会话历史\n\n"
        f"| # | 日期 | 标题 | Commits | Branch |\n"
        f"|---|------|------|---------|--------|\n"
    )

    existing_rows: list[str] = []
    if index_file.is_file():
        capture = False
        for line in index_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("|---") or re.match(r"^\|\s*#\s*\|", line):
                capture = True
                continue
            if capture and line.startswith("|"):
                existing_rows.append(line)

    new_row = f"| {session_num} | {today} | {title} | {commit_disp} | {branch_disp} |"
    body = "\n".join([new_row, *existing_rows])
    index_file.write_text(header + body + "\n", encoding="utf-8")


# =============================================================================
# 主流程
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Finley：把本次会话写进 journal")
    parser.add_argument("--title", required=True, help="会话标题")
    parser.add_argument("--task", help="任务名（默认取 --title）")
    parser.add_argument("--summary", default="（补充总结）", help="一句话总结")
    parser.add_argument("--commit", default="-", help="逗号分隔的 commit 哈希")
    parser.add_argument("--content-file", help="从文件读取详细内容")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取详细内容")
    parser.add_argument("--developer", help="开发者标识（默认自动探测）")
    parser.add_argument("--branch", help="分支名（默认自动探测）")
    args = parser.parse_args()

    repo_root = get_repo_root()
    config = _read_config(repo_root)
    max_lines = int(config.get("max_lines", DEFAULT_MAX_LINES))

    developer = resolve_developer(repo_root, args.developer, config)
    branch = resolve_branch(repo_root, args.branch)

    workspace = repo_root / ".finley" / "workspace"
    dev_dir = workspace / developer
    dev_dir.mkdir(parents=True, exist_ok=True)

    detail = "（补充细节）"
    if args.content_file and Path(args.content_file).is_file():
        detail = Path(args.content_file).read_text(encoding="utf-8")
    elif args.stdin:
        detail = sys.stdin.read()

    today = datetime.now().strftime("%Y-%m-%d")
    index_file = dev_dir / "index.md"
    session_num = get_session_count(index_file) + 1

    block = build_session_block(
        session_num, args.title, today, args.task or args.title,
        args.summary, detail, args.commit, branch,
    )

    journal_file, current_num, current_lines = get_latest_journal(dev_dir)
    block_lines = len(block.splitlines())

    if journal_file is None:
        current_num = 1
        journal_file = create_journal_file(dev_dir, 1, developer, today, max_lines)
    elif current_lines + block_lines > max_lines:
        current_num += 1
        print(
            f"[Finley] 当前 journal 超过 {max_lines} 行，轮转到 "
            f"{JOURNAL_PREFIX}{current_num}.md",
            file=sys.stderr,
        )
        journal_file = create_journal_file(dev_dir, current_num, developer, today, max_lines)

    with journal_file.open("a", encoding="utf-8") as f:
        f.write(block)

    active_file = f"{JOURNAL_PREFIX}{current_num}.md"
    write_index(index_file, active_file, session_num, today, args.title,
                args.commit, branch, developer)

    print(f"[Finley] ✅ 已记录 Session {session_num} 到 {dev_dir}/{active_file}")
    print(f"         开发者：{developer}  分支：{branch or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
