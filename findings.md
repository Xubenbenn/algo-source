# Findings

> Research notes for task plan phases

## 当前架构基线 (2026-07-27)

- **开发仓 algo-source**: `docs/` 有三份文档 (design-doc, solution-summary, architecture)
- **产品仓 algo-deploy**: production 分支有 1 次线性追加推送 (2 个 commit)
- **推送脚本** `ci_push_production.sh`: 手动触发, 沙箱闭环, 6 阶段流水线
- **校验**: L1(包导入) → L2(逐模块) → L3(pytest prod)
- **筛选**: MANIFEST.yaml exclude_patterns + string_blacklist

## Phase 1 依赖

- `model/matrix_ops/basic.py` 目前已实现: multiply, add, transpose, trace, norm, elementwise_multiply
- `model/polyfit/fitting.py` 目前已实现: polyfit_ls, polyval, poly_residual, r2_score, weighted_polyfit
- 新增函数需添加 prod 标记的测试
