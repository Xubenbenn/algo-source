"""pytest 全局配置 — fixtures 与公共工具"""

import pytest
import numpy as np


# ============================================================
# 公共 fixtures
# ============================================================

@pytest.fixture(scope="session")
def rng():
    """可复现的随机数生成器 (固定种子)"""
    return np.random.default_rng(seed=42)


@pytest.fixture(scope="module")
def random_matrix(rng):
    """生成指定尺寸的随机矩阵"""

    def _make(m: int, n: int, method: str = "uniform") -> np.ndarray:
        if method == "uniform":
            return rng.uniform(-10, 10, size=(m, n))
        elif method == "normal":
            return rng.normal(0, 5, size=(m, n))
        elif method == "spd":
            # 对称正定矩阵: A = Q Λ Q^T, Λ > 0
            a = rng.uniform(-5, 5, size=(m, m))
            a = a @ a.T + np.eye(m) * m  # 保证正定
            return a
        raise ValueError(f"未知生成方法: {method}")

    return _make


@pytest.fixture(scope="module")
def random_vector(rng):
    """生成指定长度的随机向量"""

    def _make(n: int) -> np.ndarray:
        return rng.uniform(-10, 10, size=n)

    return _make


# ============================================================
# 标记说明:
#
#   @pytest.mark.prod  → 生产环境用例 (也是研发环境的子集)
#   @pytest.mark.extended   → 仅研发环境运行的扩展用例
#
# 运行方式:
#   研发环境: pytest                          (运行全部)
#   生产环境: pytest -m "prod"                (仅运行 prod 标记)
#   研发扩展: pytest -m "extended"            (仅运行 extended 标记)
# ============================================================
