#!/bin/bash
# ============================================================
# ci_push_production.sh — 手动触发, 沙箱闭环, 线性追加推送到产品仓 production 分支
#
# 沙箱模型:
#   /tmp/ci_XXXXX/
#   ├── source/     ← git clone 开发仓
#   ├── deploy/     ← git clone 产品仓
#   ├── output/     ← build_machine.py 产出
#   └── venv/       ← Python 虚拟环境
#
# 外部影响: 零。所有操作在 /tmp 内。trap EXIT 清理。
#
# 流水线阶段:
#   ① clone source-repo → checkout --commit SHA → 校验 SHA 在 origin/main 上
#   ② venv + pyyaml
#   ③ build_machine.py 文件级黑名单 + 字符串扫描 + 树状图
#   ④ L1(包导入)→L2(逐模块)→L3(pytest prod) 三级校验
#   ⑤ 线性追加推送到 deployment-repo production (非 force push)
#   ⑥ source-repo 创建 release-* 归档分支
#
# 用法:
#   bash ci_push_production.sh --commit <sha> --tag <message>
#
# 示例:
#   bash ci_push_production.sh \
#       --commit abc1234 \
#       --tag "修复 SVD 边界条件 + 更新依赖"
# ============================================================
set -euo pipefail

# ── 默认配置 ──
SOURCE_REPO="${SOURCE_REPO:-git@github.com:Xubenbenn/algo-source.git}"
DEPLOY_REPO="${DEPLOY_REPO:-git@github.com:Xubenbenn/algo-deploy.git}"
COMMIT=""
TAG=""
SANDBOX=""
LOCAL_SOURCE=""
DEPLOY_TOKEN=""  # GitHub Actions: PAT for cross-repo push

# ── 参数 ──
usage() {
    echo "用法: $0 --commit <sha> --tag <message> [--local-source <path>] [--deploy-token <token>]"
    echo ""
    echo "  --commit SHA     开发仓 main 分支上的 commit (必须已合入 main)"
    echo "  --tag   MSG      本次发布的描述, 写入 production 的 commit message"
    echo "  --local-source   使用本地路径作为开发仓源码 (跳过 git clone, GA 模式)"
    echo "  --deploy-token   产品仓推送 Token (GA 模式, 用于 HTTPS push)"
    echo ""
    echo "  环境变量:"
    echo "    SOURCE_REPO    开发仓地址"
    echo "    DEPLOY_REPO    产品仓地址"
    exit 1
}
while [[ $# -gt 0 ]]; do
    case "$1" in
        --commit)       COMMIT="$2"; shift ;;
        --tag)          TAG="$2"; shift ;;
        --local-source) LOCAL_SOURCE="$2"; shift ;;
        --deploy-token) DEPLOY_TOKEN="$2"; shift ;;
        --help|-h)      usage ;;
        *) echo "未知参数: $1"; usage ;;
    esac
    shift
done

if [ -z "$COMMIT" ] || [ -z "$TAG" ]; then
    echo "❌ --commit 和 --tag 为必填参数"
    usage
fi

# ── 前置检查 ──
command -v git    >/dev/null 2>&1 || { echo "❌ 需要 git";   exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ 需要 python3"; exit 1; }

COMMIT_SHORT=$(echo "${COMMIT}" | cut -c1-7)
RELEASE_DATE=$(date +%Y%m%d%H%M)
RELEASE_BRANCH="release-${COMMIT_SHORT}_${RELEASE_DATE}"

echo "=== 手动生产推送 ==="
echo "  开发仓: ${SOURCE_REPO}"
echo "  Commit: ${COMMIT}"
echo "  Tag:    ${TAG}"
echo "  归档:   ${RELEASE_BRANCH}"

# ── 阶段 0: 沙箱 ──
SANDBOX=$(mktemp -d /tmp/ci_sandbox_XXXXXX)
cleanup() {
    if [ -n "${SANDBOX}" ] && [ -d "${SANDBOX}" ]; then
        rm -rf "${SANDBOX}"
        echo "🧹 沙箱已清理"
    fi
}
trap cleanup EXIT
echo ""
echo "📦 沙箱: ${SANDBOX}"

# ════════════════════════════════════════════════════════════
# 阶段 1: 准备开发仓源码
# ════════════════════════════════════════════════════════════
echo ""
echo "━━━ 阶段 1: 准备源码 ━━━"

if [ -n "$LOCAL_SOURCE" ]; then
    # GitHub Actions 模式: 使用已 checkout 的本地代码
    cp -r "$LOCAL_SOURCE" "${SANDBOX}/source"
    cd "${SANDBOX}/source"
    echo "  ✅ 本地源码 → source/ (GA 模式)"
else
    # 本地模式: 从远程 clone
    git clone --branch main \
        "${SOURCE_REPO}" "${SANDBOX}/source" 2>&1 | tail -1
    cd "${SANDBOX}/source"
    echo "  ✅ 开发仓 → source/"
fi

# fetch 确保 commit 存在 (本地模式可能没有)
git fetch origin "${COMMIT}" 2>/dev/null || true

# checkout 到指定 commit
git checkout "${COMMIT}" 2>/dev/null || {
    echo "❌ commit ${COMMIT} 不存在于远程"
    exit 1
}

# 校验: commit 必须在 origin/main 上（祖先关系）
if ! git merge-base --is-ancestor "${COMMIT}" origin/main 2>/dev/null; then
    echo "❌ ${COMMIT_SHORT} 不在 origin/main 上 (未合入 main 的 commit 禁止推送)"
    echo "   提示: 请先将该 commit 通过 PR 合入 main"
    exit 1
fi
echo "  ✅ ${COMMIT_SHORT} 已合入 origin/main"

# clone 产品仓（完整历史, 需要 production 分支历史做线性追加）
if [ -n "$DEPLOY_TOKEN" ]; then
    # GitHub Actions: 使用 token 认证的 HTTPS URL
    DEPLOY_REPO_HTTPS=$(echo "$DEPLOY_REPO" | sed 's|git@github.com:|https://github.com/|')
    DEPLOY_AUTH_URL=$(echo "$DEPLOY_REPO_HTTPS" | sed "s|https://|https://${DEPLOY_TOKEN}@|")
    git clone --branch main "$DEPLOY_AUTH_URL" "${SANDBOX}/deploy" 2>&1
else
    git clone --branch main \
        "${DEPLOY_REPO}" "${SANDBOX}/deploy" 2>&1
fi
# 验证 clone 成功 (之前 2>&1|tail 会吞掉错误)
if [ ! -d "${SANDBOX}/deploy/.git" ]; then
    echo "❌ 产品仓 clone 失败"
    exit 1
fi
echo "  ✅ 产品仓 → deploy/"

# ════════════════════════════════════════════════════════════
# 阶段 2: venv + pyyaml
# ════════════════════════════════════════════════════════════
echo ""
echo "━━━ 阶段 2: Python 环境 ━━━"

python3 -m venv "${SANDBOX}/venv"
source "${SANDBOX}/venv/bin/activate"
pip install --quiet pyyaml 2>&1 | tail -1
echo "  ✅ venv + pyyaml"

# ════════════════════════════════════════════════════════════
# 阶段 3: 构建（含字符串黑名单扫描 + 树状图）
# ════════════════════════════════════════════════════════════
echo ""
echo "━━━ 阶段 3: 文件级裁剪 + 字符串扫描 ━━━"

python "${SANDBOX}/source/scripts/build_machine.py" \
    --manifest "${SANDBOX}/source/MANIFEST.yaml" \
    --dst "${SANDBOX}/output"

MODEL_DIR="${SANDBOX}/output/model"
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ 构建失败: model/ 目录未生成"
    exit 1
fi
PY_COUNT=$(find "$MODEL_DIR" -name "*.py" -type f | wc -l | tr -d ' ')
echo "  产出: ${PY_COUNT} 个 .py 文件"

# ════════════════════════════════════════════════════════════
# 阶段 4: L1 → L2 → L3 三级校验
# ════════════════════════════════════════════════════════════

# ── L1: 包级导入 (秒级, 零依赖) ──
echo ""
echo "━━━ L1: 包级导入 ━━━"
cd "${SANDBOX}/output"
python3 -B -c "
import sys; sys.path.insert(0, '.')
try:
    import model
    print('   ✅ L1 通过')
except Exception as e:
    print(f'   ❌ L1 失败: {type(e).__name__}: {e}')
    sys.exit(1)
" || { echo "❌ L1 未通过, 推送中止"; exit 1; }

# ── L2: 逐模块导入 (秒级, 精确定位) ──
echo ""
echo "━━━ L2: 逐模块导入 ━━━"
pip install --quiet pytest numpy scipy 2>&1 | tail -1

python3 -B -c "
import sys, importlib, pathlib
sys.path.insert(0, '.')
errors = []
files = sorted(pathlib.Path('model').rglob('*.py'))
total = len(files)
for f in files:
    if f.name == '__init__.py':
        continue
    mod = str(f.with_suffix('')).replace('/', '.')
    try:
        importlib.import_module(mod)
    except Exception as e:
        errors.append((mod, type(e).__name__))
if errors:
    print(f'   ❌ L2 失败: {len(errors)}/{total} 个模块导入异常')
    for mod, err in errors:
        print(f'      {mod} → {err}')
    sys.exit(1)
print(f'   ✅ L2 通过: 全部 {total} 个模块导入正常')
" || { echo "❌ L2 未通过, 推送中止"; exit 1; }

# ── L3: 生产测试 ──
echo ""
echo "━━━ L3: 生产测试 (pytest -m prod) ━━━"
cd "${SANDBOX}/source"
set +e
python -m pytest tests/ -m "prod" -q --tb=short 2>&1
PYTEST_EXIT=$?
set -e
if [ $PYTEST_EXIT -ne 0 ]; then
    echo "❌ L3 未通过 (exit=${PYTEST_EXIT}), 推送中止"
    exit 1
fi
echo "  ✅ L3 通过"

# ════════════════════════════════════════════════════════════
# 阶段 5: 线性追加推送到产品仓 production
# ════════════════════════════════════════════════════════════
echo ""
echo "━━━ 阶段 5: 线性追加推送 production ━━━"

cd "${SANDBOX}/deploy"
# 设置 remote (GA 模式使用 token URL)
if [ -n "$DEPLOY_TOKEN" ]; then
    DEPLOY_REPO_HTTPS=$(echo "$DEPLOY_REPO" | sed 's|git@github.com:|https://github.com/|')
    DEPLOY_AUTH_URL=$(echo "$DEPLOY_REPO_HTTPS" | sed "s|https://|https://${DEPLOY_TOKEN}@|")
    git remote set-url origin "$DEPLOY_AUTH_URL" 2>/dev/null || git remote add origin "$DEPLOY_AUTH_URL"
else
    git remote set-url origin "${DEPLOY_REPO}" 2>/dev/null || git remote add origin "${DEPLOY_REPO}"
fi

# 拉取远程 production 状态
git fetch origin production 2>/dev/null || true

if git rev-parse origin/production >/dev/null 2>&1; then
    # production 已存在 → 线性追加
    echo "  production 分支已存在, 准备线性追加..."
    git checkout production 2>/dev/null || git checkout -b production origin/production
    git reset --hard origin/production
else
    # 首次推送 → 创建孤儿分支
    echo "  首次推送, 创建 production 孤儿分支..."
    git checkout --orphan production
fi

# 清空工作树, 拷贝新 model/
git rm -rf --cached . 2>/dev/null || true
find . -mindepth 1 -not -path './.git' -not -path './.git/*' -delete 2>/dev/null || true
cp -r "${SANDBOX}/output/model" .
find model/ -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
echo "${COMMIT_SHORT}" > VERSION

git add model/ VERSION
git commit -m "production: ${TAG} (source=${COMMIT_SHORT})"

# 安全推送: rebase + force-with-lease
git pull --rebase origin production 2>/dev/null || {
    echo "  ⚠️  rebase 冲突，尝试合并..."
    git rebase --abort 2>/dev/null || true
}
git push --force-with-lease origin production
echo "  ✅ production 分支已推送 (线性追加)"

# tag (每次唯一, 不覆盖)
git tag "v${COMMIT_SHORT}_${RELEASE_DATE}" 2>/dev/null || \
    git tag "v${COMMIT_SHORT}_${RELEASE_DATE}-$(date +%s)"
git push origin "v${COMMIT_SHORT}_${RELEASE_DATE}" 2>/dev/null || true
echo "  ✅ tag: v${COMMIT_SHORT}_${RELEASE_DATE}"

# ════════════════════════════════════════════════════════════
# 阶段 6: 开发仓发布归档
# ════════════════════════════════════════════════════════════
echo ""
echo "━━━ 阶段 6: 发布归档 ━━━"

cd "${SANDBOX}/source"
# 检查归档分支是否已存在
if git rev-parse "origin/${RELEASE_BRANCH}" >/dev/null 2>&1; then
    echo "  ⚠️  ${RELEASE_BRANCH} 已存在, 跳过归档"
else
    git branch "${RELEASE_BRANCH}" "${COMMIT}"
    git push origin "${RELEASE_BRANCH}"
    echo "  ✅ 归档分支: ${RELEASE_BRANCH}"
fi

# ── 完成 ──
deactivate 2>/dev/null || true

echo ""
echo "============================================"
echo "✅ 推送完成"
echo "   source commit: ${COMMIT_SHORT}"
echo "   tag message:   ${TAG}"
echo "   归档分支:      ${RELEASE_BRANCH}"
echo "   production:    model/ (${PY_COUNT} 个文件)"
echo "============================================"
