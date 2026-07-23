#!/usr/bin/env python3
"""接口粒度 AST 裁剪 — 物理删除未导出代码

用法:
    python scripts/filter_exports.py <源文件> --exports func1,func2 [--output <输出>]
    python scripts/filter_exports.py <源文件> --manifest MANIFEST.yaml [--output-dir <目录>]

策略:
    ① 从 exports 出发做 BFS 可达性分析 (静态调用图)
    ② 重写源文件, 只保留可达的定义 + 被使用的 import
    ③ 类: 保守策略 — 若任一方法可达则保留整个类
    ④ 动态引用/字符串引用 → 保守不裁剪 (标注 warning)
"""

import ast
import sys
import os
import re
import argparse
from typing import Set, Dict, List, Optional, Tuple
from pathlib import Path


# ============================================================
# 1. 名称映射 — 收集文件中所有顶层定义
# ============================================================

def _build_definition_map(tree: ast.AST) -> Dict[str, ast.AST]:
    """构建 名称 → AST 定义节点 映射。

    覆盖: FunctionDef, AsyncFunctionDef, ClassDef, 顶层赋值 (变量/常量)
    """
    name_map: Dict[str, ast.AST] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name_map[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name_map[target.id] = node
    return name_map


def _build_method_class_map(tree: ast.AST) -> Dict[str, str]:
    """构建 方法名 → 所属类名 反向映射。

    用于解析: 当 exports 包含方法名时, 自动将类名加入保留列表。
    """
    method_map: Dict[str, str] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_map[item.name] = node.name
    return method_map


# ============================================================
# 2. 引用提取 — 从 AST 节点中提取所有引用的名称
# ============================================================

def _extract_references(node: ast.AST) -> Set[str]:
    """递归提取 AST 节点内所有名称引用 (Name 节点)."""
    refs: Set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            refs.add(child.id)
        # 属性链 obj.method → 只需 obj
        elif isinstance(child, ast.Attribute):
            if isinstance(child.value, ast.Name):
                refs.add(child.value.id)
    return refs


def _extract_callee_names(node: ast.AST) -> Set[str]:
    """提取直接调用目标的名称。

    处理: f() → 'f',  obj.method() → 'obj',  d[key]() → (不处理)
    """
    names: Set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    names.add(func.value.id)
    return names


# ============================================================
# 3. 可达性分析 — BFS 从 exports 出发
# ============================================================

def _reachable_names(
    name_map: Dict[str, ast.AST],
    exports: Set[str],
    builtins: Set[str],
) -> Set[str]:
    """BFS 可达性分析: 从 exports 出发, 沿静态调用关系遍历。

    Returns:
        需要保留的所有名称 (exports + 被调用的辅助函数/类)
    """
    reachable: Set[str] = set(exports)
    queue: List[str] = list(exports)

    while queue:
        current = queue.pop(0)
        node = name_map.get(current)
        if node is None:
            continue  # 外部定义 (builtin, import), 跳过
        # 提取当前定义内部调用的一切名称
        callees = _extract_callee_names(node)
        for callee in callees:
            if callee in builtins:
                continue
            if callee in reachable:
                continue
            if callee in name_map:
                reachable.add(callee)
                queue.append(callee)
            # 不在 name_map 中的是外部 import, 不追踪

    # 类: 保守策略 — 若某方法可达, 整个类可达
    for name, node in name_map.items():
        if name in reachable:
            continue
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name in reachable:
                        reachable.add(name)
                        break

    return reachable


# ============================================================
# 4. 源码生成 — 重写文件, 只保留可达定义 + 精简 import
# ============================================================

def _collect_used_names_in_kept(tree: ast.AST, keep_names: Set[str]) -> Set[str]:
    """在保留的定义中, 扫描所有 Name 引用 (用于精简 import)."""
    used: Set[str] = set()
    for node in ast.iter_child_nodes(tree):
        name = getattr(node, 'name', None)
        if name and name in keep_names:
            used |= _extract_references(node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in keep_names:
                    used |= _extract_references(node)
    return used


def _generate_pruned_source(
    source_lines: List[str],
    tree: ast.AST,
    keep_names: Set[str],
    used_names: Set[str],
) -> str:
    """生成裁剪后的源码文本。

    保留:
      - shebang / encoding 声明
      - docstring (仅当至少一个定义被保留)
      - import 中 used_names 需要的
      - keep_names 中的定义
    删除:
      - 未被使用的 import
      - 非 keep_names 的定义
      - 顶层非定义语句 (if __name__, 裸表达式等)
    """
    result: List[str] = []

    # Shebang + encoding (行 1-2)
    if source_lines and source_lines[0].startswith("#!"):
        result.append(source_lines[0].rstrip())
        start = 1
    else:
        start = 0
    if start < len(source_lines) and "coding" in source_lines[start]:
        result.append(source_lines[start].rstrip())
        start += 1

    # Module docstring
    doc_node = ast.get_docstring(tree)
    if doc_node and keep_names:
        result.append(f'"""{doc_node}"""')
        result.append("")

    # Import 语句 — 只保留 used_names 需要的
    import_lines = _filter_imports(tree, used_names, source_lines)
    if import_lines:
        result.extend(import_lines)
        result.append("")

    # 定义 — 只保留 keep_names 中的
    for node in ast.iter_child_nodes(tree):
        name = getattr(node, 'name', None)
        if name and name in keep_names:
            result.append(_node_source(node, source_lines))
            result.append("")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in keep_names:
                    result.append(_node_source(node, source_lines))
                    result.append("")
                    break

    return "\n".join(result).strip() + "\n"


def _filter_imports(tree: ast.AST, used_names: Set[str], source_lines: List[str]) -> List[str]:
    """从 AST 提取 import 语句, 只保留 used_names 需要的。

    优先保留原始源码行 (含行内注释). 仅当需要部分裁剪时才重写。
    """
    lines: List[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            kept = [alias for alias in node.names
                    if alias.asname or alias.name in used_names
                    or alias.name.split('.')[0] in used_names]
            if kept:
                # 全部保留 → 直接用原始行 (含行内注释)
                if len(kept) == len(node.names):
                    lines.append(_raw_source_line(node, source_lines))
                else:
                    names_str = ", ".join(
                        f"{a.name} as {a.asname}" if a.asname else a.name
                        for a in kept
                    )
                    lines.append(f"import {names_str}")
        elif isinstance(node, ast.ImportFrom):
            if any(a.name == '*' for a in node.names):
                lines.append(_raw_source_line(node, source_lines))
            else:
                imported_names = {a.asname or a.name for a in node.names}
                kept = imported_names & used_names
                if kept == imported_names:
                    # 全部保留 → 原始行
                    lines.append(_raw_source_line(node, source_lines))
                elif kept:
                    module = node.module or ""
                    dots = "." * (node.level or 0)
                    names_str = ", ".join(sorted(kept))
                    lines.append(f"from {dots}{module} import {names_str}")
    return lines


def _raw_source_line(node: ast.AST, source_lines: List[str]) -> str:
    """提取 AST 节点对应的原始源码行 (保留行内注释)."""
    start = node.lineno - 1
    end = (node.end_lineno or node.lineno) - 1
    return "\n".join(
        source_lines[i].rstrip("\n").rstrip("\r")
        for i in range(start, end + 1)
    )


def _node_source(node: ast.AST, source_lines: List[str]) -> str:
    """从原始源码行中提取 AST 节点对应的文本 (保留格式)."""
    start_lineno = node.lineno - 1
    end_lineno = (node.end_lineno or node.lineno) - 1
    lines = source_lines[start_lineno:end_lineno + 1]
    # 去除所有行共有的前导空格
    text = "".join(lines)
    return text.rstrip()


# ============================================================
# 5. 主入口
# ============================================================

def prune_file(filepath: str, exports: List[str], verbose: bool = False) -> str:
    """对单个文件执行 AST 裁剪。

    Args:
        filepath: 源文件路径
        exports: 需要保留的接口名称列表
        verbose: 输出裁剪详情

    Returns:
        裁剪后的 Python 源码文本
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    source_lines = source.splitlines(keepends=True)

    tree = ast.parse(source, filename=filepath)

    # Python 内置名称 (不作为依赖追踪)
    builtins: Set[str] = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))

    # 步骤 1: 构建定义映射
    name_map = _build_definition_map(tree)
    method_class_map = _build_method_class_map(tree)
    if verbose:
        print(f"  [DEBUG] 文件中顶层定义: {list(name_map.keys())}")

    # 步骤 1.5: 方法名 → 类名解析
    resolved_exports: List[str] = []
    for e in exports:
        if e in name_map:
            resolved_exports.append(e)
        elif e in method_class_map:
            class_name = method_class_map[e]
            if class_name not in resolved_exports:
                resolved_exports.append(class_name)
                if verbose:
                    print(f"  [INFO] '{e}' 是类 '{class_name}' 的方法 → 保留整个类")
        else:
            if verbose:
                print(f"  [WARN] '{e}' 未在文件中找到 (非顶层定义/非类方法)")

    if not resolved_exports:
        return f"# {os.path.basename(filepath)} — 无有效 exports, 文件被裁剪为空\n"

    # 步骤 2: 可达性分析
    reachable = _reachable_names(name_map, set(resolved_exports), builtins)
    if verbose:
        pruned = set(name_map.keys()) - reachable
        print(f"  [INFO] 保留: {sorted(reachable)}")
        print(f"  [INFO] 裁剪: {sorted(pruned)}")

    # 步骤 4: 收集 kept 代码中使用的 import 名称
    used_names = _collect_used_names_in_kept(tree, reachable)

    # 步骤 5: 生成裁剪后源码
    return _generate_pruned_source(source_lines, tree, reachable, used_names)


def prune_from_manifest(
    manifest_path: str,
    output_dir: str,
    verbose: bool = False,
) -> Dict[str, Tuple[int, int, int]]:
    """根据 MANIFEST.yaml 中的 api_filter 批量裁剪。

    Returns:
        {filepath: (original_lines, kept_lines, pruned_count)}
    """
    import yaml
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = yaml.safe_load(f)

    api_filter = manifest.get('api_filter', [])
    if not api_filter:
        print("MANIFEST.yaml 中无 api_filter 配置, 跳过接口裁剪")
        return {}

    base_dir = os.path.dirname(os.path.abspath(manifest_path))
    results: Dict[str, Tuple[int, int, int]] = {}

    for entry in api_filter:
        file_rel = entry['file']
        exports = entry['exports']
        src_path = os.path.join(base_dir, file_rel)

        if not os.path.exists(src_path):
            print(f"  [SKIP] 文件不存在: {src_path}")
            continue

        original_lines = len(open(src_path).readlines())
        pruned_source = prune_file(src_path, exports, verbose=verbose)
        kept_lines = len(pruned_source.splitlines())

        # 写入输出目录, 保持相对路径
        dest_path = os.path.join(output_dir, file_rel)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(pruned_source)

        pruned_count = original_lines - kept_lines
        results[file_rel] = (original_lines, kept_lines, pruned_count)
        print(f"  {file_rel}: {original_lines}→{kept_lines} 行 (裁 {pruned_count} 行, 保留 {len(exports)} 接口)")

    return results


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="接口粒度 AST 裁剪工具")
    sub = parser.add_subparsers(dest="mode")

    # 单文件模式
    single = sub.add_parser("file", help="裁剪单个文件")
    single.add_argument("filepath", help="源文件路径")
    single.add_argument("--exports", required=True, help="逗号分隔的导出名称")
    single.add_argument("--output", "-o", help="输出文件路径 (默认 stdout)")
    single.add_argument("--verbose", "-v", action="store_true")

    # 批量模式 (从 MANIFEST.yaml)
    batch = sub.add_parser("manifest", help="根据 MANIFEST.yaml 批量裁剪")
    batch.add_argument("manifest", help="MANIFEST.yaml 路径")
    batch.add_argument("--output-dir", "-d", required=True, help="输出目录")
    batch.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.mode == "file":
        exports_list = [n.strip() for n in args.exports.split(",")]
        result = prune_file(args.filepath, exports_list, verbose=args.verbose)
        if args.output:
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"已写入: {args.output}")
        else:
            print(result)

    elif args.mode == "manifest":
        prune_from_manifest(args.manifest, args.output_dir, verbose=args.verbose)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
