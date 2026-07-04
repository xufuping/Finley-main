#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Finley 质量门禁 —— 在提交前统一跑 lint / typecheck / test。

用法：
    python .finley/scripts/gate.py                 # 前端 + 后端全部门禁
    python .finley/scripts/gate.py --only frontend # 只跑前端
    python .finley/scripts/gate.py --only backend  # 只跑后端
    python .finley/scripts/gate.py --dry-run       # 只打印将要执行的命令，不真正运行

命令来源：
    1. 读取 .finley/config.yaml 的 quality.frontend / quality.backend；
    2. 若某条命令是占位（形如 "<占位: ...>"），则自动探测：
       - 前端：读 package.json 的 scripts（lint / typecheck|type-check / test）；
       - 后端：读 pyproject.toml，检测 ruff / mypy / pytest。

任一命令失败 -> 整体门禁失败（进程非零退出）并清晰列出失败项。
纯标准库实现（json / tomllib / subprocess / argparse），不依赖任何第三方包。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - 仅在 <3.11 触发
    print("[Finley] 需要 Python 3.11+（缺少标准库 tomllib）。", file=sys.stderr)
    sys.exit(1)


PLACEHOLDER_PREFIX = "<占位"


# =============================================================================
# 极简 YAML 读取（仅支持 Finley config.yaml 的已知结构：两级嵌套 + 标量字符串）
# =============================================================================

def _strip_inline_comment(value: str) -> str:
    """去掉未被引号包裹的行内注释。"""
    in_single = in_double = False
    for i, ch in enumerate(value):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return value[:i]
    return value


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def load_simple_yaml(path: Path) -> dict:
    """解析 Finley 自有的简单 YAML（缩进两空格、key: value、字符串/整数标量）。

    这是一个针对已知 schema 的最小实现，不追求覆盖完整 YAML 规范。
    """
    root: dict = {}
    # 缩进栈：[(indent, container_dict), ...]
    stack: list[tuple[int, dict]] = [(-1, root)]

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = _strip_inline_comment(raw).rstrip()
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            continue

        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()

        # 回退到正确的父容器
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            stack = [(-1, root)]
        parent = stack[-1][1]

        if rest == "":
            # 新的嵌套映射
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            value = _unquote(_strip_inline_comment(rest))
            if value.isdigit():
                parent[key] = int(value)
            else:
                parent[key] = value

    return root


# =============================================================================
# 前端 / 后端命令探测
# =============================================================================

def is_placeholder(cmd: Optional[str]) -> bool:
    return not cmd or cmd.strip() == "" or cmd.strip().startswith(PLACEHOLDER_PREFIX)


def detect_pkg_runner(repo_root: Path) -> str:
    """根据锁文件推断包管理器命令前缀。"""
    if (repo_root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo_root / "yarn.lock").exists():
        return "yarn"
    if (repo_root / "bun.lockb").exists():
        return "bun"
    return "npm"


def detect_frontend(repo_root: Path, kind: str) -> Optional[str]:
    """从 package.json 的 scripts 探测前端命令。kind ∈ {lint, typecheck, test}。"""
    pkg_path = repo_root / "package.json"
    if not pkg_path.exists():
        return None
    try:
        scripts = json.loads(pkg_path.read_text(encoding="utf-8")).get("scripts", {})
    except (json.JSONDecodeError, OSError):
        return None

    runner = detect_pkg_runner(repo_root)

    if kind == "lint":
        candidates = ["lint"]
    elif kind == "typecheck":
        candidates = ["typecheck", "type-check", "tsc"]
    elif kind == "test":
        candidates = ["test"]
    else:
        candidates = []

    for name in candidates:
        if name in scripts:
            if name == "test":
                # npm/yarn/pnpm/bun 都支持简写
                return f"{runner} test"
            return f"{runner} run {name}"
    return None


def detect_backend(repo_root: Path, kind: str) -> Optional[str]:
    """从 pyproject.toml 探测后端命令。kind ∈ {lint, typecheck, test}。"""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError):
        return None

    tool = data.get("tool", {}) if isinstance(data.get("tool"), dict) else {}

    # 收集所有依赖声明字符串，便于关键字探测
    deps_blob = json.dumps(data.get("project", {}).get("dependencies", []))
    optional = data.get("project", {}).get("optional-dependencies", {})
    if isinstance(optional, dict):
        for group in optional.values():
            deps_blob += json.dumps(group)
    # PDM/Poetry 等的依赖组
    deps_blob += json.dumps(tool.get("poetry", {}).get("dependencies", {}))
    deps_blob = deps_blob.lower()

    def has(name: str) -> bool:
        return name in tool or name in deps_blob

    if kind == "lint" and has("ruff"):
        return "ruff check ."
    if kind == "typecheck" and has("mypy"):
        return "mypy ."
    if kind == "test" and ("pytest" in tool or "pytest" in deps_blob):
        return "pytest"
    return None


# =============================================================================
# 门禁执行
# =============================================================================

def resolve_commands(repo_root: Path, config: dict, side: str) -> list[tuple[str, str]]:
    """解析出某一侧（frontend/backend）要跑的 (标签, 命令) 列表。"""
    quality = config.get("quality", {}) if isinstance(config.get("quality"), dict) else {}
    section = quality.get(side, {}) if isinstance(quality.get(side), dict) else {}

    resolved: list[tuple[str, str]] = []
    for kind in ("lint", "typecheck", "test"):
        cmd = section.get(kind)
        if is_placeholder(cmd):
            detector = detect_frontend if side == "frontend" else detect_backend
            cmd = detector(repo_root, kind)
        if cmd and not is_placeholder(cmd):
            resolved.append((f"{side}:{kind}", cmd))
    return resolved


def run_command(label: str, cmd: str, repo_root: Path, dry_run: bool) -> bool:
    print(f"\n\033[1m▶ [{label}]\033[0m {cmd}")
    if dry_run:
        print("   (dry-run 跳过执行)")
        return True
    result = subprocess.run(cmd, shell=True, cwd=str(repo_root))
    ok = result.returncode == 0
    if ok:
        print(f"   \033[32m✔ 通过\033[0m [{label}]")
    else:
        print(f"   \033[31m✗ 失败\033[0m [{label}]（退出码 {result.returncode}）")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Finley 质量门禁：统一跑 lint / typecheck / test")
    parser.add_argument("--only", choices=["frontend", "backend"], help="只运行某一侧")
    parser.add_argument("--dry-run", action="store_true", help="只打印命令，不真正执行")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent  # .finley/scripts/gate.py -> repo root
    config_path = repo_root / ".finley" / "config.yaml"

    if not config_path.exists():
        print(f"[Finley] 未找到配置文件：{config_path}", file=sys.stderr)
        return 1

    config = load_simple_yaml(config_path)

    sides = [args.only] if args.only else ["frontend", "backend"]
    all_commands: list[tuple[str, str]] = []
    for side in sides:
        all_commands.extend(resolve_commands(repo_root, config, side))

    print("=" * 60)
    print("Finley 质量门禁")
    print("=" * 60)

    if not all_commands:
        print(
            "\n[Finley] 未解析到任何可执行的门禁命令。\n"
            "  → 请在 .finley/config.yaml 的 quality.frontend / quality.backend 里\n"
            "    填入真实命令，或确保 package.json / pyproject.toml 里存在可被探测的脚本。",
            file=sys.stderr,
        )
        # 没有命令视为门禁未配置：非零退出，避免「假绿」。
        return 2

    failures: list[str] = []
    for label, cmd in all_commands:
        if not run_command(label, cmd, repo_root, args.dry_run):
            failures.append(label)

    print("\n" + "=" * 60)
    if failures:
        print(f"\033[31m门禁失败\033[0m：{len(failures)}/{len(all_commands)} 项未通过")
        for label in failures:
            print(f"  ✗ {label}")
        print("=" * 60)
        return 1

    print(f"\033[32m门禁全部通过\033[0m：{len(all_commands)}/{len(all_commands)} 项")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
