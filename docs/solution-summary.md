# Python 算法分仓管理 — 方案总结

## 一、背景

### 1.1 需求

一个开发仓，不断演进，包含所有算法、实验代码、测试；机台环境只需要核心代码子集，运行环境极简。

### 1.2 目标

- **源码唯一性**：算法只在开发仓存在一份
- **物理隔离**：未选中的代码不在产品仓制品中出现
- **合规切断**：GPL/AGPL 依赖无法进入机台
- **构建→部署自动化**：开发仓合入 → CI 构建裁剪产物 → 推送产品仓
- **分支隔离**：产品仓 `main` 分支人工合入，CI 只推 `production` 分支

---

## 二、怎么做

### 2.1 仓库与分支

实际两个 Git 仓库：

| 仓库 | 分支 | 内容 | 维护方式 |
|------|------|------|---------|
| **开发仓** `algo-source` | `main` | 全量算法、测试、构建脚本、MANIFEST | 人工 PR |
| **产品仓** `algo-deploy` | `main` | 适配器、集成测试、部署脚本、依赖锁 | 人工 PR |
| | `production` | 裁剪后算法源码（`model/`）+ 版本标记 `VERSION` | CI force push（孤儿分支） |

### 2.2 筛选规则

`MANIFEST.yaml` 使用 `build.exclude_patterns` 声明排除通配符列表，支持 `**`（任意层级）、`*`、`?`。命中任一规则的文件不进入制品，其余全量保留。

示例：

```yaml
build:
  exclude_patterns:
    - "**/test_*.py"
    - "**/conftest.py"
    - "scripts/**"
    - "**/__pycache__/**"
```

筛选规则随代码版本在开发仓中，纳入 Code Review。

### 2.3 裁剪引擎

`file_filter.py`，仅使用 Python 标准库（`pathlib`, `shutil`, `fnmatch`）：

- `apply_exclude_filter(src, dst, patterns)`：扫描源目录下 `.py/.yaml/.json`，黑名单匹配 → 跳过；否则复制到目标目录。复制后递归清理空目录。
- `print_tree(file_list, root_label, title)`：ASCII 树状图渲染，按字母序排序保证输出一致。

`build_machine.py` 作为构建入口：解析 MANIFEST → 调用 `apply_exclude_filter` → 打印 `[KEPT]` + `[EXCLUDED]` 两份树状图。

### 2.4 CI 流水线（沙箱闭环）

`ci_push_production.sh` 全部操作在 `/tmp/ci_sandbox_XXXXX/` 内：

| 阶段 | 操作 | 产物 |
|:---:|------|------|
| 1 | `git clone --depth 1` 两仓 | 独立副本 |
| 2 | `venv` + `pip install pyyaml` | 隔离环境 |
| 3 | `build_machine.py` 裁剪 + 树状图 | 裁剪源码 |
| 4 | 三级校验 | 全通过 → 继续 / 任一失败 → 中止 |
| 5 | 产品仓 `production` 分支 force push + tag | 远程更新 |

### 2.5 三级校验

校验对象是裁剪产物（`output/` 目录），全部在沙箱内执行：

| 层级 | 操作 | 检测 | 耗时 |
|:---:|------|------|:---:|
| **L1** | `import model` → 整个包是否可导入 | `__init__.py` 导入链断裂 | <1s |
| **L2** | `importlib.import_module` 逐 `.py` | 每模块独立导入（不互相掩盖） | 1-2s |
| **L3** | `pytest -m prod` | 核心计算路径正确性 | ~30s |

L1 在 pip install 之前执行（零额外依赖），失败可省去后续依赖安装时间。L2 需 numpy/scipy（算法运行时依赖）。L3 需 pytest（测试依赖）。

### 2.6 机台部署

`deploy.sh`：`git fetch origin production` → `git checkout origin/production -- model/` → `pip install -r requirements.lock` → 冒烟测试。

---

## 三、为什么

### 3.1 为什么用文件级黑名单而不是 AST 接口裁剪？

- **规则可审计**：`exclude_patterns` 是一份可读的文本列表，Code Review 时一眼能看出哪些被排除。AST 裁剪需要理解调用图才能判断最终保留了什么。
- **CI 日志可审计**：两份 ASCII 树状图（`[KEPT]` / `[EXCLUDED]`）在每次构建日志中输出，可直接 `diff` 对比两次构建的文件变更，肉眼确认。
- **零维护成本**：不需要追踪调用图、不需要处理类方法解析、不需要同步 `__init__.py`。新增算法 = 文件放入 `model/`，无需任何额外标记。
- **约束明确**：文件排除前，L1/L2 校验会自动检测 ImportError。若排除规则破坏了依赖链，CI 立即中止并给出精确的断裂点。不需要开发者手动 `grep` 检查。

### 3.2 为什么用三级校验而不是单层 grep？

- **L1（快闸）**：秒级，零额外依赖。`import model` 触发整个导入链。失败时能省去后续 pip install 的时间。
- **L2（精确定位）**：逐模块独立导入，不互相掩盖错误。一个模块的 ImportError 不影响其他模块的检测，给出完整故障清单。
- **L3（语义验证）**：真实执行计算路径，暴露 L1/L2 检测不到的运行时错误。
- **自动化**：不需要开发者手动 `grep -r "from.*xxx" model/` 检查依赖关系。CI 直接给出"哪个模块因为缺哪个文件而失败"的精确报告。

### 3.3 为什么用 Git 分支做制品而不是 .tar.gz？

- **版本追踪**：Git commit SHA 天然链接到开发仓精确版本
- **回滚**：`git checkout v1.0.0 -- model/` 一步完成
- **diff 可见**：`git diff production` 展示两次构建的文件级变更
- **基础设施最简**：不需要 PyPI 私有源或对象存储

### 3.4 为什么 production 用孤儿分支 + force push？

- **永不冲突**：无共同祖先，force push 是完整替换
- **无人为介入**：不接受人工提交
- **与 main 隔离**：不影响产品仓 `main` 分支

### 3.5 为什么沙箱闭环（clone 到 /tmp）？

- **分支安全**：显式 `git clone --branch main`，不误用 feature 分支
- **清洁度保证**：`git status --porcelain` 检查
- **零污染**：`__pycache__`、临时文件在 `/tmp` 内，`trap EXIT` 清空
- **可复现**：任意机器执行脚本即可
