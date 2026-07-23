#!/bin/bash
# ============================================================
# ci_push_production.sh — 构建裁剪源码 → 强制推送到部署仓 production 分支
#
# 流程:
#   ① build_machine.py → 裁剪后纯源码
#   ② 推送到部署仓 production 分支 (强制推送, 避免冲突)
#   ③ 打 tag 记录版本
#
# 冲突规避: production 分支完全由 CI 管理, force push 无冲突
#
# 用法:
#   bash ci_push_production.sh [--version 1.0.0] [--dry-run]
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_REPO="${SOURCE_ROOT}/../deployment-repo"
TMP_OUTPUT=$(mktemp -d /tmp/production_src_XXXXXX)
DRY_RUN=false
VERSION=""

trap "rm -rf ${TMP_OUTPUT}" EXIT

# ── 参数 ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --version) VERSION="$2"; shift ;;
        *) echo "未知: $1"; exit 1 ;;
    esac
    shift
done

# ── 版本号 ──
if [ -z "$VERSION" ]; then
    # 从 MANIFEST 或 git 获取
    cd "$SOURCE_ROOT"
    VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo "dev-$(date +%Y%m%d%H%M)")
fi

echo "=== CI 推送 production 分支: ${VERSION} ==="

# ── 步骤 1: 构建裁剪源码 ──
echo ""
echo "📁 构建裁剪源码..."
python3 "${SCRIPT_DIR}/build_machine.py" \
    --manifest "${SOURCE_ROOT}/MANIFEST.yaml" \
    -d "${TMP_OUTPUT}"

# ── 步骤 2: 强制推送到部署仓 production 分支 ──
echo ""
echo "📤 推送到部署仓 production 分支..."

DEPLOY_REPO_ABS=$(cd "$DEPLOY_REPO" 2>/dev/null && pwd || echo "")

if [ -z "$DEPLOY_REPO_ABS" ]; then
    echo "❌ 部署仓不存在: ${DEPLOY_REPO}"
    exit 1
fi

cd "$DEPLOY_REPO_ABS"

# 检查是否已初始化为 git 仓库
if [ ! -d ".git" ]; then
    echo "  初始化部署仓 git..."
    git init
    git checkout -b main 2>/dev/null || true
fi

# 切换到 production 分支 (孤儿分支, 与 main 完全独立)
git checkout --orphan production 2>/dev/null || git checkout production 2>/dev/null || true

# 清空 production 分支内容 — 安全方式, 保护 .git 目录
# ① 清除 git 索引
git rm -rf --cached . 2>/dev/null || true
# ② 清除工作树中所有文件和目录, 但排除 .git/
find . -mindepth 1 -not -path './.git' -not -path './.git/*' -delete 2>/dev/null || true

# 拷贝裁剪源码
cp -r "${TMP_OUTPUT}/model" .
# 添加版本标记文件
cat > VERSION <<< "${VERSION}"

git add model/ VERSION

if [ "$DRY_RUN" = true ]; then
    echo "  [DRY-RUN] git commit -m 'production: ${VERSION}'"
    echo "  [DRY-RUN] git push --force origin production"
else
    if git diff --cached --quiet 2>/dev/null; then
        echo "  (无变更, 跳过)"
    else
        git commit -m "production: ${VERSION}"
        # 强制推送 — 这是关键: production 分支无冲突
        git push --force origin production 2>/dev/null || {
            echo "  ⚠️  git push 失败 (可能无 remote), 本地 production 分支已就绪"
            echo "  请手动设置 remote 后执行: git push --force origin production"
        }
    fi
fi

# 打 tag
if [ "$DRY_RUN" = false ]; then
    git tag -f "v${VERSION}" 2>/dev/null || true
    git push --force origin "v${VERSION}" 2>/dev/null || true
fi

# 切回 main
git checkout main 2>/dev/null || true

echo ""
echo "============================================"
echo "✅ production 分支已更新: ${VERSION}"
echo "   分支:  deployment-repo/production  (仅含裁剪后 model/)"
echo "   标签:  v${VERSION}"
echo "   下一步: cd deployment-repo && bash deploy.sh"
echo "============================================"
