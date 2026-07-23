#!/bin/bash
# ============================================================
# ci_push_production.sh — 沙箱闭环: 构建裁剪源码 → 推送到产品仓 production 分支
#
# 沙箱模型:
#   /tmp/ci_XXXXX/
#   ├── source/     ← git clone 开发仓
#   ├── deploy/     ← git clone 产品仓
#   ├── output/     ← build_machine.py 产出
#   └── venv/       ← Python 虚拟环境 (pyyaml)
#
# 外部影响: 零。所有操作在 /tmp 内完成，trap EXIT 清理。
#
# 依赖清单 (最小化):
#   系统:  bash, git, python3.9+, find, mktemp
#   Python: pyyaml (venv 内 pip install, 纯 Python, 无传递依赖)
#
# 用法:
#   bash ci_push_production.sh                          # 默认 main 分支
#   bash ci_push_production.sh --ref v1.2.3             # 指定 tag
#   bash ci_push_production.sh --ref feature/xxx        # 指定分支
#   bash ci_push_production.sh --dry-run                # 演练
# ============================================================
set -euo pipefail

# ── 默认配置 ──
SOURCE_REPO="${SOURCE_REPO:-git@github.com:Xubenbenn/algo-source.git}"
DEPLOY_REPO="${DEPLOY_REPO:-git@github.com:Xubenbenn/algo-deploy.git}"
SOURCE_REF="${SOURCE_REF:-main}"
VERSION=""
DRY_RUN=false
SANDBOX=""

# ── 参数 ──
usage() {
    echo "用法: $0 [--ref <branch|tag>] [--version <ver>] [--dry-run]"
    echo ""
    echo "  环境变量:"
    echo "    SOURCE_REPO  开发仓地址 (默认 github:Xubenbenn/algo-source)"
    echo "    DEPLOY_REPO  产品仓地址 (默认 github:Xubenbenn/algo-deploy)"
    echo "    SOURCE_REF   checkout 目标 (默认 main)"
    exit 1
}
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ref)     SOURCE_REF="$2"; shift ;;
        --version) VERSION="$2"; shift ;;
        --dry-run) DRY_RUN=true ;;
        --help|-h) usage ;;
        *) echo "未知参数: $1"; usage ;;
    esac
    shift
done

# ── 前置检查 ──
command -v git    >/dev/null 2>&1 || { echo "❌ 需要 git";   exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ 需要 python3"; exit 1; }

echo "=== CI 沙箱构建 ==="
echo "  开发仓: ${SOURCE_REPO}"
echo "  Checkout: ${SOURCE_REF}"
echo "  产品仓: ${DEPLOY_REPO}"

# ── 阶段 0: 创建沙箱 ──
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

# ── 阶段 1: clone 仓库到沙箱 ──
echo ""
echo "━━━ 阶段 1: 克隆仓库 ━━━"

git clone --depth 1 --branch "${SOURCE_REF}" \
    "${SOURCE_REPO}" "${SANDBOX}/source" 2>&1 | tail -1
echo "  ✅ 开发仓 → source/"

git clone --depth 1 --branch main \
    "${DEPLOY_REPO}" "${SANDBOX}/deploy" 2>&1 | tail -1
echo "  ✅ 产品仓 → deploy/"

# ── 阶段 1.5: 工作树清洁度检查 ──
cd "${SANDBOX}/source"
if [ -n "$(git status --porcelain 2>/dev/null || true)" ]; then
    echo "  ❌ 开发仓工作树不干净 (clone 后不应有变更)"
    exit 1
fi

# 版本号
if [ -z "$VERSION" ]; then
    VERSION=$(git describe --tags --always 2>/dev/null || echo "dev-$(date +%Y%m%d%H%M)")
fi
ACTUAL_REF=$(git rev-parse --short HEAD)
echo "  版本: ${VERSION} (ref=${SOURCE_REF}, commit=${ACTUAL_REF})"

# ── 阶段 2: venv + 最小依赖 ──
echo ""
echo "━━━ 阶段 2: Python 环境 ━━━"

python3 -m venv "${SANDBOX}/venv"
# shellcheck disable=SC1091
source "${SANDBOX}/venv/bin/activate"
pip install --quiet pyyaml 2>&1 | tail -1
echo "  ✅ venv + pyyaml (唯一外部依赖)"

# ── 阶段 3: 构建裁剪源码 ──
echo ""
echo "━━━ 阶段 3: 两层筛选构建 ━━━"

python "${SANDBOX}/source/scripts/build_machine.py" \
    --manifest "${SANDBOX}/source/MANIFEST.yaml" \
    -d "${SANDBOX}/output"

# 验证产出
MODEL_DIR="${SANDBOX}/output/model"
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ 构建失败: model/ 目录未生成"
    exit 1
fi
PY_COUNT=$(find "$MODEL_DIR" -name "*.py" -type f | wc -l | tr -d ' ')
echo "  产出: ${PY_COUNT} 个 .py 文件"

# ── 阶段 4: 推送到产品仓 production 分支 ──
echo ""
echo "━━━ 阶段 4: 更新 production 分支 ━━━"

cd "${SANDBOX}/deploy"

# 确保 remote 设置 (如果 clone 时未自动设置)
git remote set-url origin "${DEPLOY_REPO}" 2>/dev/null || git remote add origin "${DEPLOY_REPO}"

# 创建/切换到 production 孤儿分支
git checkout --orphan production 2>/dev/null || git checkout production 2>/dev/null || true

# 安全清空: git 索引 + 工作树 (保护 .git)
git rm -rf --cached . 2>/dev/null || true
find . -mindepth 1 -not -path './.git' -not -path './.git/*' -delete 2>/dev/null || true

# 复制裁剪源码 + 版本标记
cp -r "${SANDBOX}/output/model" .
cat > VERSION <<< "${VERSION}"

git add model/ VERSION

if [ "$DRY_RUN" = true ]; then
    echo "  [DRY-RUN] 将提交: production: ${VERSION}"
    echo "  [DRY-RUN] 产物预览:"
    find model/ -name "*.py" | sort | while read f; do
        echo "    ${f}"
    done
else
    if git diff --cached --quiet 2>/dev/null; then
        echo "  (无变更, 跳过推送)"
    else
        git commit -m "production: ${VERSION} (source=${ACTUAL_REF})"
        git push --force origin production
        echo "  ✅ production 分支已推送"
    fi

    # 打 tag
    git tag -f "v${VERSION}" 2>/dev/null || true
    git push --force origin "v${VERSION}" 2>/dev/null || true
    echo "  ✅ 标签: v${VERSION}"
fi

# ── 完成 ──
deactivate 2>/dev/null || true

echo ""
echo "============================================"
if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] 完成 — 无实际推送"
else
    echo "✅ 推送完成: ${VERSION} (source=${ACTUAL_REF})"
fi
echo "   沙箱: ${SANDBOX} (退出时自动清理)"
echo "   产品仓 production 分支: model/ (${PY_COUNT} 个文件)"
echo "============================================"
