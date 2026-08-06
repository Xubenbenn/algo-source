# MANIFEST 版本独立承载 — 设计文档

> **状态**: 待审查 | **日期**: 2026-08-06
> **前置**: [release 分支方案 v3.0](../release-branch-design.md)

---

## 一、背景与诉求

### 1.1 问题

当前 MANIFEST.yaml 位于开发仓 master 根目录，构建时从指定 commit 的树中读取——**代码版本与代码范围（裁剪规则）强耦合**。

### 1.2 诉求（已确认）

- 场景 1: 代码版本 = 某个历史 commit_id，但需要使用一个新提交的 MANIFEST.yaml
- 场景 2: 反向组合——新代码 + 老规则
- **规则变更不要求与代码同 PR**（独立演进）

### 1.3 决策过程

| 环节 | 结论 |
|------|------|
| council 第一轮（分支 vs SHA 组合） | 反对常设分支——"master 也存 MANIFEST"时双真相无解 |
| 场景确认（规则独立于代码 PR） | master 必须移除 MANIFEST，独立承载 → 双真相消失，分支方案回归 |
| 用户约束 | 两个 commit_id 均必填；各自必须来源于对应分支；版本信息必须打印 |

---

## 二、设计

### 2.1 分支模型

```
开发仓 algo-source:
  master        ← 代码 (移除 MANIFEST.yaml)
  manifest      ← 仅 MANIFEST.yaml (受保护分支, 唯一权威)
                  git 历史 + tag (manifest/v{N}) 即规则版本库
  release       ← 裁剪产物 (线性演进, 保持 v3.0 方案不变)
```

### 2.2 workflow 输入（两个 commit_id，均必填，不允许缺省）

```
Actions → 生产推送:
  commit        (必填) 代码版本 — 必须 ∈ master 分支
  manifest_ref  (必填) 规则版本 — 必须 ∈ manifest 分支
  semver        (必填) 对外版本号
  tag           (必填) 发布描述
```

### 2.3 流水线第 0 步：合法性校验 + 信息打印

```
① git merge-base --is-ancestor <commit> origin/master
   → 失败: "❌ commit 不在 master 分支上" → 终止
② git merge-base --is-ancestor <manifest_ref> origin/manifest
   → 失败: "❌ manifest_ref 不在 manifest 分支上" → 终止
③ 打印 (强制, 供审计):
   ========================================
   代码版本:     commit=<full sha>  (branch: master)
   MANIFEST 版本: manifest_ref=<full sha>  (branch: manifest)
   ========================================
```

### 2.4 构建（解耦点）

```
src      ← git checkout <commit>                    (代码树)
MANIFEST ← git show <manifest_ref>:MANIFEST.yaml > /tmp/manifest.yaml   (规则树)

build_machine.py --manifest /tmp/manifest.yaml --src <checkout目录>
```

`build_machine.py` 变更：`--src` 显式参数（去掉当前 `base_dir = manifest_path.parent` 的隐式耦合）。

### 2.5 产物记录（审计闭环）

```
VERSION (随 release 分支 + production 透传):
  source_commit: <代码 full sha>
  manifest_sha:  <规则 commit full sha>    ← 导航: 定位规则版本
  manifest_hash: <MANIFEST.yaml 文件 SHA-256>  ← 验真: 校验规则内容
  semver:        v1.2.0
  release_tag:   release/v3
  content_hash:  <model/ 树哈希>
  ...

打印 + VERSION 双记录 → 产物可反查"用的哪个代码 + 哪个规则"
```

**双字段说明**: `manifest_sha` 回答"用的哪个规则版本"（可 checkout 复现），`manifest_hash` 回答"规则内容是什么"（防 sha 指向的内容被篡改）。两者缺一不可——v3.0 已有 manifest_hash，本设计新增 manifest_sha。

### 2.6 校验机制（保持 v3.0 不变）

- pattern 空匹配校验: 任一 exclude_patterns 匹配 0 个文件 → 构建失败
- L1 包导入 → L2 逐模块 → L3 pytest prod

### 2.7 分支保护

```
manifest 分支 (与 release 同构):
  - 仅 CI Bot (PAT) 推送
  - 禁止人工 push
  - 禁止 force push
```

---

## 三、变更清单

| 文件 | 变更 |
|------|------|
| `master/MANIFEST.yaml` | 删除 |
| `manifest` 分支 | 新建，承载 MANIFEST.yaml（初始 = 当前 master 版本） |
| `scripts/build_machine.py` | `--src` 显式参数；`--manifest` 任意路径 |
| `.github/workflows/production-push.yml` | `manifest_ref` 必填输入；第 0 步双校验 + 打印；构建取 MANIFEST 改为 `git show` |
| release 分支生成逻辑 | VERSION 记录 `manifest_sha` |
| 文档 | release-branch-design.md 同步 |

---

## 四、边界情况

| 场景 | 处理 |
|------|------|
| 老代码 + 新规则 | commit=历史SHA + manifest_ref=manifest@HEAD ✅ |
| 新代码 + 老规则 | commit=master@HEAD + manifest_ref=manifest/v2 ✅ |
| commit 不在 master | 第 0 步校验拒绝 |
| manifest_ref 不在 manifest | 第 0 步校验拒绝 |
| 老规则对新代码 pattern 空匹配 | pattern 空匹配校验拒绝 |
| 本地开发跑 build_machine | 手动 `git show manifest:MANIFEST.yaml` 到临时路径 |

---

## 五、验证

```bash
# 端到端 (GA):
# 触发 workflow, 输入:
#   commit=<master 上某 SHA>  manifest_ref=<manifest 分支某 SHA>
# 预期:
#   ① 第 0 步打印两版本信息
#   ② 构建成功 (pattern 空匹配 + L1/L2/L3 通过)
#   ③ release 分支线性追加, VERSION 含 manifest_sha
#   ④ production 同步 + sync PR

# 负向验证:
#   manifest_ref 传 master 上的 SHA → 应被拒绝
#   commit 传 manifest 分支的 SHA → 应被拒绝
```
