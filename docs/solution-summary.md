# Python 算法分仓管理 — 方案总结

## 一、背景

### 1.1 需求

一个开发仓，不断演进，包含所有算法、实验代码、测试中间流程；一个产品仓，只保留机台需要的核心代码，运行环境极简。

### 1.2 目标效果

- **源码唯一性**：算法只在开发仓存在一份，产品仓不存源码副本
- **物理隔离**：未选中的代码不在产品仓磁盘上出现（不是注释、不是条件跳过）
- **合规切断**：GPL/AGPL 类依赖的代码无法进入机台
- **构建→部署自动化**：开发仓合入 → CI 构建裁剪产物 → 推送到产品仓 → 机台拉取部署
- **分支隔离**：产品仓主分支由人工 PR 合入，CI 只推独立分支，永不冲突

---

## 二、方案

### 2.1 仓库三角色

| 仓库 | 分支 | 内容 | 维护方式 |
|------|------|------|---------|
| **开发仓** `algo-source` | `main` | 全量算法、测试、构建脚本、MANIFEST 筛选规则 | 人工 PR |
| **产品仓** `algo-deploy` | `main` | 适配器、集成测试、部署脚本、依赖锁 | 人工 PR |
| | `production` | 裁剪后的算法源码（`model/`）+ 版本标记 `VERSION` | CI 强制推送 |

### 2.2 两层筛选

**第一层：文件粒度。** `MANIFEST.yaml:modules.include/exclude` 声明哪些文件进入制品。include 为目录时递归展开 `.py`。exclude 从结果中排除。

**第二层：接口粒度。** `MANIFEST.yaml:api_filter` 按文件声明保留的函数/类。CI 通过 AST 可达性分析，从保留接口出发沿静态调用图 BFS，保留所有可达定义，物理删除不可达代码。同步更新 `__init__.py`，移除已裁剪符号的 import。

**筛选规则** 随代码版本走，在开发仓中纳入 Code Review。

### 2.3 构建流水线（沙箱闭环）

`ci_push_production.sh` 全部操作在 `/tmp/ci_sandbox_XXXXX/` 内完成，`trap EXIT` 清理：

| 阶段 | 操作 | 产物 |
|:---:|------|------|
| 1 | `git clone --depth 1` 开发仓 + 产品仓到沙箱 | 独立副本 |
| 2 | `python3 -m venv` + `pip install pyyaml` | 隔离 Python 环境 |
| 3 | `build_machine.py` 两层筛选 | 裁剪源码 (`output/model/`) |
| 3.5a | `python3 -B -c "importlib.import_module"` 逐模块检查 | 导入完整性报告 |
| 3.5b | `pytest -m prod` 生产测试 | 通过/失败（失败则推送中止） |
| 4 | 产品仓 `production` 孤儿分支 force push + 打 tag | 远程 production 更新 |

**依赖清单**：bash, git, python3.9+, find, mktemp（系统）；pyyaml（构建，纯 Python 零传递依赖）；pytest, numpy, scipy（测试，沙箱 venv 内安装）。

### 2.4 机台部署

机台端执行 `deploy.sh`：`git fetch origin production` → `git checkout origin/production -- model/` → `pip install -r requirements.lock` → 冒烟测试。

### 2.5 分支 push 规则

```
开发仓 main        ← 人工 PR
产品仓 main        ← 人工 PR（禁止 CI 推送）
产品仓 production  ← CI force push（孤儿分支，永不冲突）
```

---

## 三、选型原因

### 3.1 为什么三仓（开发仓 + 制品定义 + 产品仓）而不是两仓？

两仓模型（开发仓 + 产品仓，CI 从开发仓 `git clone` 后筛选再拷入产品仓）在合规上有致命缺陷：`git clone` 拉取全量代码的瞬间，GPL 文件已在机台磁盘上存在过，构成分发行为。三仓将筛选提前到 CI 构建机，产品仓的 `production` 分支从诞生起就只含裁剪后代码，物理层面从未存在过被排除的文件。

### 3.2 为什么用 Git 分支做制品而不是 .tar.gz / .whl？

- **版本追踪**：Git commit SHA 天然链接到开发仓的精确源码版本，不需要额外的元数据服务
- **回滚**：机台 `git checkout v1.0.0 -- model/` 即完成回滚，不依赖制品库可用性
- **diff 可见**：`git diff production` 直接展示两次构建间哪些接口发生了变更
- **基础设施最简**：不需要 PyPI 私有源、Artifactory、S3

### 3.3 为什么 AST 裁剪而不是装饰器标记或文件拆分？

- **物理隔离**：装饰器标记是逻辑隔离——源码文件仍在，只是"不调用"。AST 裁剪后代码物理不存在。
- **无侵入**：不要求开发者在源码中添加 `@production` 等标记，筛选规则集中在 MANIFEST.yaml 中管理
- **自动追踪依赖**：被保留接口调用的辅助函数自动纳入保留集，不需要开发者手动梳理依赖链
- **类方法解析**：`api_filter` 可以直接写方法名，工具自动定位到包含类并保留整个类

### 3.4 为什么 production 用孤儿分支 + force push？

- **永不冲突**：孤儿分支无共同祖先，force push 是完整替换，不会有 merge conflict
- **无人为介入**：该分支不接受人工提交，任何状态都可被下一次 CI 完整覆盖
- **与 main 完全隔离**：`git checkout main` 恢复工作树后，production 的变更对 main 零影响

### 3.5 为什么沙箱闭环（clone 到 /tmp）而不是就地构建？

- **分支安全**：显式 `git clone --branch main` 确保基于指定分支构建，不会误用开发者的 feature 分支
- **清洁度保证**：`git status --porcelain` 检查确保无未提交代码混入
- **零污染**：`__pycache__`、`.pyc`、临时文件全部在 `/tmp` 内，`trap EXIT` 清理
- **可复现**：任意机器 clone 脚本即可执行，不依赖本地工作树状态
