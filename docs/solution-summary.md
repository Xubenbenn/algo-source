# Python 算法分仓管理 — 方案总结

## 一、背景

### 1.1 需求

一个开发仓，不断演进，包含所有算法、实验代码、测试中间流程；机台环境只需要核心代码子集，运行环境极简。

### 1.2 目标效果

- **源码唯一性**：算法只在开发仓存在一份，产品仓不存完整源码副本
- **物理隔离**：未选中的代码不在产品仓的制品中出现（不是注释、不是条件跳过）
- **合规切断**：GPL/AGPL 类依赖的代码无法进入机台
- **构建→部署自动化**：开发仓合入 → CI 沙箱构建裁剪产物 → 推送到产品仓独立分支 → 机台拉取部署
- **分支隔离**：产品仓主分支由人工 PR 合入，CI 只推 `production` 分支，永不冲突

---

## 二、方案

### 2.1 两仓库，三角色

实际只有**两个 Git 仓库**。制品不单独建仓，而是产品仓的一个独立分支：

| 仓库 | 分支 | 角色 | 内容 |
|------|------|------|------|
| **开发仓** `algo-source` | `main` | 唯一源码事实 | 全量算法、测试、构建脚本、MANIFEST 筛选规则 |
| **产品仓** `algo-deploy` | `main` | 部署编排 | 适配器、集成测试、部署脚本、依赖锁 |
| | `production` | 制品 | 裁剪后算法源码 (`model/`) + 版本标记 `VERSION` |

`production` 是孤儿分支，与 `main` 无共同祖先。每次 CI 构建 force push 完整替换。

### 2.2 两层筛选

**第一层：文件粒度。** `MANIFEST.yaml:modules.include/exclude` 声明哪些文件进入制品。include 为目录时递归展开 `.py`。exclude 从结果中排除。

**第二层：接口粒度。** `MANIFEST.yaml:api_filter` 按文件声明保留的函数/类。CI 通过 AST 解析，从保留接口出发沿静态调用图 BFS 做可达性分析，保留所有可达定义，物理删除不可达代码。同步更新 `__init__.py`，移除已裁剪符号的 import。

筛选规则随代码版本走在开发仓中，纳入 Code Review。

### 2.3 构建流水线（沙箱闭环）

`ci_push_production.sh` 全部在 `/tmp/ci_sandbox_XXXXX/` 内完成，`trap EXIT` 清理：

| 阶段 | 操作 | 产物 |
|:---:|------|------|
| 1 | `git clone --depth 1` 两仓到沙箱 | 独立副本 |
| 2 | `venv` + `pip install pyyaml` | 隔离 Python 环境 |
| 3 | `build_machine.py` 两层筛选 | 裁剪源码 |
| 3.5a | 逐模块 `importlib.import_module` | 导入完整性 |
| 3.5b | `pytest -m prod` | 通过/中止 |
| 4 | 产品仓 `production` 分支 force push + tag | 远程更新 |

依赖：bash, git, python3.9+, find, mktemp（系统）；pyyaml（构建）；pytest, numpy, scipy（测试，沙箱内安装）。

### 2.4 机台部署

`deploy.sh`：`git fetch origin production` → `git checkout origin/production -- model/` → `pip install -r requirements.lock` → 冒烟测试。

### 2.5 分支 Push 规则

```
开发仓 main        ← 人工 PR
产品仓 main        ← 人工 PR（CI 不推送）
产品仓 production  ← CI force push（孤儿分支，永不冲突）
```

---

## 三、选型原因

### 3.1 为什么制品不单独建仓？

制品 = `production` 分支的 `model/` 目录，挂在产品仓内。单独建制品仓会多一个仓库的 clone/权限/同步开销，而 Git 分支本身提供版本历史、diff、tag，完全满足制品管理需求。本质上是把"制品库"降级为一个 Git 分支，零额外基础设施。

### 3.2 为什么不用 .tar.gz / .whl 做制品？

- **版本追踪**：Git commit SHA 天然链接到开发仓精确版本，不需要额外元数据服务
- **回滚**：`git checkout v1.0.0 -- model/` 即完成，不依赖制品库可用性
- **diff 可见**：`git diff production` 展示两次构建间的接口变更
- **基础设施最简**：不需要 PyPI 私有源、Artifactory、S3

### 3.3 为什么 AST 裁剪而不是装饰器标记或文件拆分？

- **物理隔离**：装饰器标记是逻辑隔离——源码仍在，只是不调用。AST 裁剪后代码物理不存在
- **无侵入**：不要求开发者在源码中添加标记，筛选规则集中在 MANIFEST.yaml
- **自动追踪依赖**：被保留接口调用的辅助函数自动纳入，无需手动梳理
- **类方法解析**：可直接写方法名，工具自动定位到包含类并保留整个类

### 3.4 为什么 production 用孤儿分支 + force push？

- **永不冲突**：孤儿分支无共同祖先，force push 是完整替换
- **无人为介入**：该分支不接受人工提交，任何状态可被下次 CI 完整覆盖
- **与 main 隔离**：`git checkout main` 恢复工作树后，不影响 main

### 3.5 为什么沙箱闭环（clone 到 /tmp）？

- **分支安全**：显式 `git clone --branch main`，不会误用 feature 分支
- **清洁度保证**：`git status --porcelain` 检查无未提交代码混入
- **零污染**：`__pycache__`、临时文件在 `/tmp`，`trap EXIT` 清空
- **可复现**：任意机器 clone 脚本即可执行，不依赖本地状态
