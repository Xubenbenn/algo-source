#!/usr/bin/env python3
"""文件级黑名单裁剪 — 基于通配符的显式排除 + ASCII 树状图。

核心逻辑:
  ① 扫描源目录下所有 .py / .yaml / .json
  ② 相对路径命中 exclude_patterns → 跳过, 否则保留
  ③ 清理输出目录中的空文件夹
  ④ 打印 [KEPT] + [EXCLUDED] 两份树状图

仅使用 Python 标准库 (pathlib, shutil, fnmatch), 零额外依赖。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Tuple


# ============================================================
# 1. 核心过滤逻辑
# ============================================================

# 始终扫描的文件类型
SCAN_SUFFIXES = {".py", ".yaml", ".json"}


def apply_exclude_filter(
    src_root: Path,
    dst_root: Path,
    patterns: List[str],
) -> Tuple[List[Path], List[Path]]:
    """扫描源目录, 按黑名单复制到目标目录。

    Args:
        src_root: 源目录根路径
        dst_root: 目标目录根路径
        patterns: 排除通配符列表 (fnmatch 语法, 支持 ** * ?)

    Returns:
        (kept, excluded) — 保留和排除的文件相对路径列表
    """
    from fnmatch import fnmatch

    kept: List[Path] = []
    excluded: List[Path] = []

    # 清空目标目录
    if dst_root.exists():
        shutil.rmtree(dst_root)

    # 扫描 + 匹配
    for src_file in sorted(src_root.rglob("*")):
        if not src_file.is_file():
            continue
        if src_file.suffix not in SCAN_SUFFIXES:
            continue

        rel = src_file.relative_to(src_root)
        rel_str = str(rel)

        # 黑名单匹配
        if any(fnmatch(rel_str, pat) for pat in patterns):
            excluded.append(rel)
        else:
            kept.append(rel)
            # 复制文件
            dst_file = dst_root / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    # 清理空目录
    _remove_empty_dirs(dst_root)

    return kept, excluded


def _remove_empty_dirs(root: Path) -> None:
    """递归删除 root 下的所有空目录 (自底向上)."""
    for d in sorted(root.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


# ============================================================
# 2. ASCII 树状图渲染
# ============================================================

def print_tree(
    file_list: List[Path],
    root_label: str,
    title: str,
) -> None:
    """打印 ASCII 目录树。

    Args:
        file_list: 文件相对路径列表
        root_label: 树根名称, 空字符串时不打印根节点
        title: 标题行
    """
    if not file_list:
        print(f"\n{title}")
        print("(empty)")
        return

    # 构建目录树
    tree: dict = {}
    for f in file_list:
        parts = f.parts
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = None

    print(f"\n{title}")
    if root_label:
        print(f"{root_label}/")
    _render_tree(tree, prefix="")


def _render_tree(node: dict, prefix: str) -> None:
    """递归渲染目录树. 按字母序排序保证每次输出一致."""
    items = sorted(node.items(), key=lambda x: (x[1] is not None, x[0]))
    for i, (name, subtree) in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        line = f"{prefix}{connector}{name}"
        if subtree is None:
            print(line)  # 文件
        else:
            print(f"{line}/")
            extension = "    " if is_last else "│   "
            _render_tree(subtree, prefix + extension)


# ============================================================
# 3. CLI 入口 (可独立调用)
# ============================================================

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="文件级黑名单裁剪 + 树状图")
    parser.add_argument("--src", required=True, help="源目录")
    parser.add_argument("--dst", required=True, help="目标目录")
    parser.add_argument("--patterns", nargs="*", default=[], help="排除通配符列表")
    parser.add_argument("--manifest", help="从 MANIFEST.yaml 读取 exclude_patterns")
    args = parser.parse_args()

    patterns = list(args.patterns)

    # 从 MANIFEST 读取
    if args.manifest:
        import yaml
        with open(args.manifest) as f:
            manifest = yaml.safe_load(f)
        patterns.extend(manifest.get("build", {}).get("exclude_patterns", []))

    if not patterns:
        print("⚠️  无排除规则, 将全量复制")
        patterns = []

    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()

    if not src.is_dir():
        print(f"❌ 源目录不存在: {src}")
        return

    print(f"源目录:  {src}")
    print(f"目标目录: {dst}")
    print(f"排除规则: {len(patterns)} 条")
    for p in patterns:
        print(f"  - {p}")

    kept, excluded = apply_exclude_filter(src, dst, patterns)

    # 树状图输出
    print_tree(
        [Path("model") / f for f in kept],
        "model",
        f"=== [KEPT] 保留的源码树 (共 {len(kept)} 个文件) ===",
    )
    print_tree(
        [Path("model") / f for f in excluded],
        "model",
        f"=== [EXCLUDED] 排除的源码树 (共 {len(excluded)} 个文件) ===",
    )


if __name__ == "__main__":
    main()
