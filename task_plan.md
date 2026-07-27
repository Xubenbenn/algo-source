# Task Plan: 特性迭代 + 两仓同步验证

> created: 2026-07-27
> goal: 新增算法特性 → 迭代推送 → 验证两仓同步和 production 线性追加

## 起始状态

| 仓库 | 最新 commit | 状态 |
|------|-----------|------|
| algo-source main | `655bdd1` docs v2.0 | 文档基线完成 |
| algo-deploy production | `584727c` | 一次推送 (source=846638a) |

## Phase 1: 新增算法特性 (V1.1)

Status: in_progress

- [ ] 1.1 在 `model/matrix_ops/basic.py` 新增 `matrix_power` 函数
- [ ] 1.2 在 `model/polyfit/fitting.py` 新增 `polyfit_ridge` 岭回归拟合
- [ ] 1.3 补充对应的 prod 测试用例
- [ ] 1.4 本地 pytest 验证 (全部 12+ 新测试通过)
- [ ] 1.5 提交 + PR 合入 main

## Phase 2: 第一次推送 (V1.1)

Status: pending

- [ ] 2.1 执行 `ci_push_production.sh --commit <sha> --tag "V1.1: 新增 matrix_power + polyfit_ridge"`
- [ ] 2.2 验证 L1/L2/L3 全部通过
- [ ] 2.3 验证 production 分支新增一个 commit（线性追加，非 root-commit）
- [ ] 2.4 验证 tag 已创建
- [ ] 2.5 验证 `release-*` 归档分支已创建

## Phase 3: 第二次推送 (V1.2 — 验证线性追加)

Status: pending

- [ ] 3.1 新增 `model/svd/decompose.py` 中 `svd_reconstruct` 函数
- [ ] 3.2 补充 prod 测试 + 合入 main
- [ ] 3.3 执行推送
- [ ] 3.4 验证 production 分支现有 3 个线性 commit
- [ ] 3.5 验证 `git log origin/production --oneline` 展示完整历史

## Phase 4: 字符串黑名单验证

Status: pending

- [ ] 4.1 在 `model/` 中临时添加含黑名单字符串（如 "GPL-3.0"）的注释
- [ ] 4.2 MANIFEST.yaml 启用 `string_blacklist: ["GPL-3.0"]`
- [ ] 4.3 执行推送 → 验证 L2 字符串扫描中止构建
- [ ] 4.4 清理测试代码 + 关闭黑名单规则

## Phase 5: 两仓同步端到端验证

Status: pending

- [ ] 5.1 克隆产品仓 production 分支 → 验证 model/ 完整性
- [ ] 5.2 验证 production tag → 开发仓 commit 的反向追踪
- [ ] 5.3 验证机台部署模拟（checkout tag → import model → 冒烟测试）
- [ ] 5.4 验证 `release-*` 分支 checkout 可复现源码

## Errors Encountered

| Error | Phase | Resolution |
|-------|-------|------------|
| — | — | — |
