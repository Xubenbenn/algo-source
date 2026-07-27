"""伪逆与正则化求解 — 基于 SVD"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import linalg


def pseudo_inverse(a: ArrayLike, rcond: float = 1e-15) -> NDArray:
    """Moore-Penrose 伪逆: A⁺ = V Σ⁺ U^T

    Args:
        a: 输入矩阵, shape (m, n)
        rcond: 奇异值截断阈值 (相对于最大奇异值)

    Returns:
        伪逆矩阵, shape (n, m)
    """
    a_arr = np.asarray(a, dtype=np.float64)
    # scipy ≥1.14 移除了 rcond 参数, 改用 rtol
    try:
        return linalg.pinv(a_arr, rcond=rcond)
    except TypeError:
        return linalg.pinv(a_arr, rtol=rcond)


def solve_via_svd(a: ArrayLike, b: ArrayLike, rcond: float = 1e-15) -> NDArray:
    """基于 SVD 的线性最小二乘求解: x = A⁺ b

    等价于 np.linalg.lstsq 但直接使用 SVD 路径，可控制截断阈值。

    Args:
        a: 系数矩阵, shape (m, n)
        b: 右端向量/矩阵, shape (m,) 或 (m, k)
        rcond: 奇异值截断阈值

    Returns:
        解 x, shape (n,) 或 (n, k)
    """
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    a_pinv = pseudo_inverse(a_arr, rcond=rcond)
    return np.dot(a_pinv, b_arr)


def tikhonov_regularized(
    a: ArrayLike, b: ArrayLike, alpha: float = 1.0
) -> NDArray:
    """Tikhonov 正则化 (岭回归): min ||Ax - b||²₂ + α²||x||²₂

    通过增广矩阵 SVD 求解:
      x = V (Σ² + α²I)^{-1} Σ U^T b

    Args:
        a: 系数矩阵
        b: 观测向量
        alpha: 正则化参数 (越大 → 解越平滑, 范数越小)

    Returns:
        正则化解 x
    """
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)

    u, s, vt = np.linalg.svd(a_arr, full_matrices=False)
    # 构造 Tikhonov 滤波器: s / (s² + α²)
    filt = s / (s**2 + alpha**2)
    # x = V · diag(filt) · U^T · b
    utb = np.dot(u.T, b_arr)
    filtered = filt * utb[: len(s)]
    return np.dot(vt.T, filtered)
