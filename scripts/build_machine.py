#!/usr/bin/env python3
"""机台源码构建 — 文件级黑名单裁剪 + 树状图报告。

流程:
  ① 解析 MANIFEST.yaml → 获取 exclude_patterns
  ② file_filter.apply_exclude_filter 扫描 + 匹配 + 复制
  ③ 打印 [KEPT] + [EXCLUDED] ASCII 树状图

用法:
  python scripts/build_machine.py --manifest MANIFEST.yaml \\
      --src ./model --dst ../deployment-repo/model/
"""

from __future__ import annotations

import sys
import os
from pathlib import Path


def main() -> None:
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description="文件级黑名单裁剪构建")
    parser.add_argument("--manifest", default="MANIFEST.yaml", help="MANIFEST.yaml 路径")
    parser.add_argument("--src", help="源目录 (默认: MANIFEST 所在目录, 即仓库根)")
    parser.add_argument("--dst", required=True, help="目标输出目录 (制品放入 dst/model/)")
    parser.add_argument("--dry-run", action="store_true", help="仅打印, 不执行")
    args = parser.parse_args()

    # 脚本所在目录 → 添加 sys.path 以便导入 file_filter
    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))
    from file_filter import apply_exclude_filter, print_tree

    # 路径解析
    manifest_path = Path(args.manifest).resolve()
    base_dir = manifest_path.parent
    src_root = Path(args.src).resolve() if args.src else base_dir
    dst_root = Path(args.dst).resolve()

    # 读取配置
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    patterns = manifest.get("build", {}).get("exclude_patterns", [])

    print(f"=== 机台源码构建 ===")
    print(f"源目录:  {src_root}")
    print(f"目标:    {dst_root}")
    print(f"规则:    {len(patterns)} 条")
    for p in patterns:
        print(f"  - {p}")

    if args.dry_run:
        # dry-run: 只打印规则, 不执行
        from fnmatch import fnmatch
        kept, excluded = [], []
        for f in sorted(src_root.rglob("*")):
            if not f.is_file() or f.suffix not in {".py", ".yaml", ".json"}:
                continue
            rel = str(f.relative_to(src_root))
            if any(fnmatch(rel, pat) for pat in patterns):
                excluded.append(f.relative_to(src_root))
            else:
                kept.append(f.relative_to(src_root))

        print_tree(
            kept, "",
            f"\n=== [KEPT] 保留的源码树 (共 {len(kept)} 个文件) ===",
        )
        print_tree(
            excluded, "",
            f"=== [EXCLUDED] 排除的源码树 (共 {len(excluded)} 个文件) ===",
        )
        print(f"\n[DRY-RUN] 以上为预览, 未实际拷贝")
        return

    # 执行裁剪
    kept, excluded = apply_exclude_filter(src_root, dst_root, patterns)

    # 树状图报告
    print_tree(
        kept, "",
        f"=== [KEPT] 保留的源码树 (共 {len(kept)} 个文件) ===",
    )
    print_tree(
        excluded, "",
        f"=== [EXCLUDED] 排除的源码树 (共 {len(excluded)} 个文件) ===",
    )

    # 统计
    total_lines = 0
    for f_rel in kept:
        with open(dst_root / f_rel) as fp:
            total_lines += len(fp.readlines())

    print(f"\n✅ 构建完成: {len(kept)} 个文件, {total_lines} 行源码")
    print(f"   排除: {len(excluded)} 个文件")
    print(f"   输出: {dst_root}")
    print(f"   下一步: bash scripts/ci_push_production.sh")


if __name__ == "__main__":
    main()
