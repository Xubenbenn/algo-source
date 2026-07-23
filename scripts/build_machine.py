#!/usr/bin/env python3
"""机台源码构建编排 — 两层筛选, 输出纯源码 (无 .pyc / 无 .tar.gz)

流程:
  ① 解析 MANIFEST.yaml → 获取 include/exclude 规则
  ② 文件粒度筛选: 拷贝 include 文件到构建目录
  ③ 接口粒度筛选: 对 api_filter 文件执行 AST 裁剪 (物理删除)
  ④ 输出纯源码到指定目录 (准备推送到部署仓 production 分支)

用法:
  python scripts/build_machine.py [--output ../deployment-repo/model/] [--dry-run]
"""

import ast
import os
import sys
import shutil
import argparse
import tempfile
import fnmatch
from typing import List, Set


# ============================================================
# 步骤 1: 解析 MANIFEST → 文件列表
# ============================================================

def resolve_module_paths(base_dir: str, manifest: dict) -> List[str]:
    """解析 modules.include/exclude → 精确文件路径列表。"""
    include = manifest.get("modules", {}).get("include", [])
    exclude = manifest.get("modules", {}).get("exclude", [])

    files: Set[str] = set()
    for pattern in include:
        full = os.path.join(base_dir, pattern)
        if os.path.isfile(full):
            files.add(pattern)
        elif os.path.isdir(full):
            for root, _, filenames in os.walk(full):
                for fname in filenames:
                    if fname.endswith(".py"):
                        abs_path = os.path.join(root, fname)
                        rel = os.path.relpath(abs_path, base_dir)
                        files.add(rel)
        else:
            import glob as gmod
            for matched in gmod.glob(full, recursive=True):
                if os.path.isfile(matched):
                    rel = os.path.relpath(matched, base_dir)
                    files.add(rel)

    result: List[str] = []
    for f in sorted(files):
        excluded = False
        for pat in exclude:
            if fnmatch.fnmatch(f, pat):
                excluded = True
                break
            if pat.rstrip("/") and f.startswith(pat.rstrip("/") + "/"):
                excluded = True
                break
        if not excluded:
            result.append(f)
    return result


# ============================================================
# 步骤 2 + 3: 文件拷贝 + AST 裁剪
# ============================================================

def copy_files(file_list: List[str], src_dir: str, dst_dir: str, dry_run: bool = False) -> int:
    """拷贝文件, 保持相对路径."""
    count = 0
    for rel in file_list:
        src = os.path.join(src_dir, rel)
        dst = os.path.join(dst_dir, rel)
        if not os.path.exists(src):
            print(f"  [WARN] 源文件不存在: {src}")
            continue
        if dry_run:
            print(f"  [DRY] COPY {rel}")
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        count += 1
    return count


def apply_api_filter(build_dir: str, manifest_path: str, verbose: bool = False):
    """原地对构建目录中的文件执行 AST 裁剪."""
    from filter_exports import prune_from_manifest
    results = prune_from_manifest(manifest_path, build_dir, verbose=verbose)
    if not results:
        print("  (无需接口裁剪)")
    return results


# ============================================================
# 步骤 3.5: 重建 __init__.py — 裁剪后同步导入列表
# ============================================================

def regenerate_init_files(build_dir: str):
    """扫描每个包目录, 重建 __init__.py 只导入实际存在的符号。

    AST 裁剪后, 部分模块的函数被物理删除, 但 __init__.py 的 import
    列表未更新, 导致 import 时 NameError。此函数扫描裁剪后的模块,
    仅保留实际存在的符号导入。
    """
    import re

    fixed_count = 0
    for root, dirs, files in os.walk(build_dir):
        init_path = os.path.join(root, "__init__.py")
        if not os.path.exists(init_path):
            continue

        # 扫描同目录下所有 .py 模块的实际顶层符号
        available: Set[str] = set()
        for fname in files:
            if fname == "__init__.py" or not fname.endswith(".py"):
                continue
            module_path = os.path.join(root, fname)
            try:
                with open(module_path) as f:
                    tree = ast.parse(f.read(), filename=fname)
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        available.add(node.name)
            except SyntaxError:
                continue

        # 解析 __init__.py 的导入
        with open(init_path) as f:
            init_source = f.read()
        init_tree = ast.parse(init_source, filename="__init__.py")

        new_lines = []
        has_changes = False
        for node in ast.iter_child_nodes(init_tree):
            if isinstance(node, ast.ImportFrom):
                kept = [alias for alias in node.names
                        if alias.name in available or alias.name == '*']
                if not kept:
                    has_changes = True
                    continue  # 整行删除
                if len(kept) != len(node.names):
                    has_changes = True
                    # 部分裁剪 — 重写 import 行
                    module = node.module or ""
                    dots = "." * (node.level or 0)
                    names_str = ",\n    ".join(
                        a.asname if a.asname else a.name for a in kept
                    )
                    if len(kept) == 1:
                        new_lines.append(
                            f"from {dots}{module} import {names_str}"
                        )
                    else:
                        new_lines.append(
                            f"from {dots}{module} import (\n"
                            f"    {names_str},\n"
                            f")"
                        )
                    continue
                # 全部保留 → 原始行 (含注释)
            elif isinstance(node, ast.Expr):
                continue  # docstring — 单独处理
            new_lines.append(_raw_node_source(node, init_source))

        if has_changes and new_lines:
            # 如果有 module docstring, 保留它
            doc = ast.get_docstring(init_tree)
            with open(init_path, 'w') as f:
                if doc:
                    f.write(f'"""{doc}"""\n\n')
                f.write("\n".join(new_lines).rstrip() + "\n")
            fixed_count += 1

    if fixed_count:
        print(f"  🔧 重建 {fixed_count} 个 __init__.py (移除已裁剪符号的导入)")


def _raw_node_source(node: ast.AST, source: str) -> str:
    """从源码中提取 AST 节点的原始文本. 使用 lineno 定位."""
    lines = source.splitlines()
    start = node.lineno - 1
    end = (node.end_lineno or node.lineno) - 1
    return "\n".join(lines[start:end + 1])


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="机台源码构建 (纯源码输出)")
    parser.add_argument("--manifest", default="MANIFEST.yaml", help="MANIFEST.yaml 路径")
    parser.add_argument("--output-dir", "-d", required=True, help="输出目录 (裁剪后源码)")
    parser.add_argument("--dry-run", action="store_true", help="仅打印, 不执行")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    import yaml

    base_dir = os.path.dirname(os.path.abspath(args.manifest))
    with open(args.manifest, 'r', encoding='utf-8') as f:
        manifest = yaml.safe_load(f)

    version = manifest.get("version", "unknown")
    print(f"=== 机台源码构建 (MANIFEST v{version}) ===")

    # ── 第一层: 文件粒度 ──
    print("\n📁 第一层: 文件粒度筛选")
    file_list = resolve_module_paths(base_dir, manifest)
    print(f"  解析到 {len(file_list)} 个文件")

    output_dir = os.path.abspath(args.output_dir)

    if args.dry_run:
        for f in file_list:
            print(f"  [DRY] {f}")
        api_filter = manifest.get("api_filter", [])
        if api_filter:
            print(f"\n  [DRY] 第二层将裁剪 {len(api_filter)} 个文件")
        print(f"\n  [DRY] 将输出到 {output_dir}")
        return

    # 先输出到临时目录, 裁剪后移到最终目录
    tmp_dir = tempfile.mkdtemp(prefix="machine_src_")
    try:
        copied = copy_files(file_list, base_dir, tmp_dir)
        print(f"  已拷贝 {copied} 个文件")

        # ── 第二层: 接口粒度 ──
        print("\n✂️  第二层: 接口粒度 AST 裁剪")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, script_dir)
        apply_api_filter(tmp_dir, args.manifest, verbose=args.verbose)

        # ── 同步 __init__.py ──
        print("\n🔧 同步 __init__.py 导入列表")
        regenerate_init_files(tmp_dir)

        # ── 输出: 安全替换 model/ 子目录 (不删除部署仓其他文件) ──
        model_output = os.path.join(output_dir, "model")
        print(f"\n📤 输出到: {model_output}")
        if os.path.exists(model_output):
            shutil.rmtree(model_output)
        # tmp_dir 中文件路径含 model/ 前缀, 直接移动
        shutil.move(os.path.join(tmp_dir, "model"), model_output)

        # 统计 (仅 model/, 不包含部署仓自身的 adapters/tests)
        py_count = 0
        total_lines = 0
        stat_dir = os.path.join(output_dir, "model")
        if os.path.isdir(stat_dir):
            for root, _, files in os.walk(stat_dir):
                for f in files:
                    if f.endswith(".py"):
                        py_count += 1
                        with open(os.path.join(root, f)) as fp:
                            total_lines += len(fp.readlines())
        print(f"\n✅ 构建完成: {py_count} 个 .py 文件, {total_lines} 行源码")
        print(f"   输出目录: {output_dir}")
        print(f"   下一步: bash scripts/ci_push_production.sh")

    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    main()
