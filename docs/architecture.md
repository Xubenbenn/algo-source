# 仓库架构与同步流程

## 一、仓库全景

```mermaid
graph TB
    subgraph 开发仓["开发仓 (algo-source)"]
        S_main["main<br/>全量算法 + 测试 + 构建脚本 + MANIFEST"]
        S_release["release-xxx_yyyymmdd<br/>发布归档分支 (只读)"]
    end

    subgraph 产品仓["产品仓 (algo-deploy)"]
        D_main["main<br/>适配器 + 集成测试 + 部署脚本"]
        D_prod["production<br/>裁剪后算法源码 (CI 线性追加)"]
    end

    subgraph 机台["机台环境"]
        M["/opt/algo/app/<br/>checkout tag 获取 model/"]
    end

    S_main -->|"手动触发 ci_push_production.sh<br/>--commit sha --tag msg"| D_prod
    S_main -.->|"推送成功后自动创建"| S_release
    D_prod -->|"git checkout vXXX -- model/"| M
    D_main -->|"人工 PR 合入"| D_main
```

## 二、分支关系

```mermaid
gitGraph
    commit id: "init"
    commit id: "feat_algo"
    commit id: "feat_test"
    commit id: "fix_bug" tag: "v1.0.0"
    branch release_abc1234_20260724
    checkout main
    commit id: "feat_v2"
```

```mermaid
gitGraph
    commit id: "prod_v1" tag: "v1.0.0"
    commit id: "prod_v2" tag: "v1.0.1"
    commit id: "prod_v3" tag: "v1.0.2"
```

| 仓库 | 分支 | 写权限 | 说明 |
|------|------|:---:|------|
| **algo-source** | `main` | 人工 PR | 唯一源码事实，所有算法、测试、构建脚本在此演进 |
| | `release-{sha}_{ts}` | CI 自动 | 每次生产推送后创建，指向推送时的源码 commit，只读归档 |
| **algo-deploy** | `main` | 人工 PR | 胶水适配器、集成测试、部署脚本，不含算法源码 |
| | `production` | CI 线性追加 | 孤儿分支，仅含裁剪后 `model/` + `VERSION`，每次推送新增一个 commit |

## 三、同步推送流程

```mermaid
sequenceDiagram
    participant Dev as 开发者
    participant Src as 开发仓 main
    participant CI as ci_push_production.sh (沙箱 /tmp/ci_XXXXX)
    participant Dep as 产品仓 production
    participant Arc as 开发仓 release-*
    participant Mac as 机台

    Dev->>Src: PR 合入 main
    Note over Dev: 需要生产推送时

    Dev->>CI: bash ci_push_production.sh<br/>--commit abc1234 --tag "修复 SVD"
    CI->>Src: git clone + checkout abc1234
    CI->>CI: 校验 abc1234 在 origin/main 上
    CI-->>Dev: ❌ 未合入 main → 拒绝

    CI->>CI: build_machine.py 裁剪
    CI->>CI: 字符串黑名单扫描
    CI->>CI: L1 包导入 → L2 逐模块 → L3 生产测试
    CI-->>Dev: ❌ 失败 → 推送中止

    CI->>Dep: git pull --rebase origin production
    CI->>Dep: git push --force-with-lease origin production
    CI->>Dep: git tag vabc1234_20260724
    CI->>Src: git push origin release-abc1234_20260724

    Note over Arc: 归档分支已创建

    Mac->>Dep: git fetch origin production
    Mac->>Dep: git checkout vabc1234_20260724 -- model/
    Note over Mac: 部署完成
```

## 四、校验闸门

```mermaid
flowchart TD
    A["开发者执行 ci_push_production.sh"] --> B{"commit 在 origin/main 上?"}
    B -->|否| X1["❌ 拒绝"]
    B -->|是| C["build_machine.py<br/>文件级黑名单 + 字符串扫描"]
    C --> D{"字符串黑名单命中?"}
    D -->|是| X2["❌ 构建中止"]
    D -->|否| E["L1: import model"]
    E --> F{"通过?"}
    F -->|否| X3["❌ 推送中止<br/>(无需安装依赖)"]
    F -->|是| G["L2: 逐模块 importlib"]
    G --> H{"通过?"}
    H -->|否| X4["❌ 推送中止"]
    H -->|是| I["L3: pytest -m prod"]
    I --> J{"通过?"}
    J -->|否| X5["❌ 推送中止"]
    J -->|是| K["线性追加推送 production"]
    K --> L["创建 release-* 归档分支"]
    L --> M["✅ 完成"]
```

## 五、数据流向

```mermaid
flowchart LR
    subgraph 开发仓
        A1["model/ 全量源码"]
        A2["MANIFEST.yaml"]
        A3["scripts/"]
        A4["tests/"]
    end

    subgraph 沙箱构建
        B1["file_filter.py<br/>exclude_patterns 匹配"]
        B2["scan_strings<br/>字符串黑名单"]
        B3["L1+L2+L3<br/>三级校验"]
    end

    subgraph 产品仓
        C1["production 分支<br/>model/ 裁剪源码"]
        C2["main 分支<br/>adapters/ 部署脚本"]
    end

    A1 --> B1
    A2 --> B1
    A2 --> B2
    B1 --> B2
    B2 --> B3
    B3 --> C1
    C1 -.->|"机台: checkout tag"| C2
```

## 六、版本追踪链

```
机台运行的 model/
  → 产品仓 production tag: v846638a_202607241450
    → production commit: 584727c
      → "source=846638a"
        → 开发仓 commit: 846638a
          → 归档分支: release-846638a_202607241450
```
