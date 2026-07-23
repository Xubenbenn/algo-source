"""SVD 分解 — 基于 numpy/scipy 封装"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import linalg
from typing import Tuple


def svd_full(a: ArrayLike) -> Tuple[NDArray, NDArray, NDArray]:
    """完整 SVD 分解: A = U Σ V^T

    Args:
        a: 输入矩阵, shape (m, n)

    Returns:
        (U, S, Vt) — 左奇异向量(m×m)、奇异值向量(k,)、右奇异向量转置(n×n)
    """
    a_arr = np.asarray(a, dtype=np.float64)
    u, s, vt = linalg.svd(a_arr, full_matrices=True)
    return u, s, vt


def svd_economy(a: ArrayLike) -> Tuple[NDArray, NDArray, NDArray]:
    """经济型 SVD 分解: A = U Σ V^T (U 为 m×k, k = min(m,n))

    Args:
        a: 输入矩阵

    Returns:
        (U, S, Vt) — 经济尺寸的奇异向量和奇异值
    """
    a_arr = np.asarray(a, dtype=np.float64)
    u, s, vt = linalg.svd(a_arr, full_matrices=False)
    return u, s, vt


def singular_values(a: ArrayLike) -> NDArray:
    """仅计算奇异值（不计算奇异向量），性能更高

    Args:
        a: 输入矩阵

    Returns:
        奇异值向量, 降序排列
    """
    a_arr = np.asarray(a, dtype=np.float64)
    return linalg.svdvals(a_arr)


def svd_rank(a: ArrayLike, tol: float = 1e-10) -> int:
    """通过 SVD 计算矩阵的数值秩

    Args:
        a: 输入矩阵
        tol: 奇异值阈值, 低于此值的视为零

    Returns:
        数值秩 (大于 tol 的奇异值个数)
    """
    s = singular_values(a)
    max_s = s[0] if len(s) > 0 else 0.0
    if max_s == 0:
        return 0
    return int(np.sum(s / max_s > tol))
