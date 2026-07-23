"""低秩逼近与矩阵分析 — 基于 SVD"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import linalg


def low_rank_approx(a: ArrayLike, k: int) -> NDArray:
    """低秩逼近: A ≈ U_k Σ_k V_k^T (Eckart-Young 最优逼近)

    Args:
        a: 输入矩阵, shape (m, n)
        k: 目标秩 (k ≤ min(m, n))

    Returns:
        秩-k 逼近矩阵, shape (m, n)
    """
    a_arr = np.asarray(a, dtype=np.float64)
    u, s, vt = linalg.svd(a_arr, full_matrices=False)
    k = min(k, len(s))
    return np.dot(u[:, :k] * s[:k], vt[:k, :])


def reconstruction_error(a: ArrayLike, k: int) -> float:
    """低秩逼近的 Frobenius 范数相对重构误差

    err = ||A - A_k||_F / ||A||_F

    Args:
        a: 输入矩阵
        k: 逼近秩

    Returns:
        相对误差 ∈ [0, 1]
    """
    a_arr = np.asarray(a, dtype=np.float64)
    approx = low_rank_approx(a_arr, k)
    err = np.linalg.norm(a_arr - approx, ord="fro")
    norm_a = np.linalg.norm(a_arr, ord="fro")
    return float(err / norm_a) if norm_a > 0 else 0.0


def condition_number(a: ArrayLike) -> float:
    """矩阵条件数 (2-范数): κ₂(A) = σ_max / σ_min

    Args:
        a: 输入矩阵

    Returns:
        条件数, ∞ 表示奇异 (不可逆)
    """
    s = linalg.svdvals(np.asarray(a, dtype=np.float64))
    if len(s) == 0 or s[-1] == 0:
        return float("inf")
    return float(s[0] / s[-1])


def effective_rank(a: ArrayLike, tol: float = 0.01) -> int:
    """有效秩 — 奇异值占比超过 tol 的分量个数

    rank_eff = argmin_k { Σ_{i=1}^k σ_i² / Σ σ² ≥ 1 - tol }

    Args:
        a: 输入矩阵
        tol: 能量损失容忍度

    Returns:
        有效秩
    """
    s = linalg.svdvals(np.asarray(a, dtype=np.float64))
    total_energy = np.sum(s**2)
    if total_energy == 0:
        return 0
    cumulative = np.cumsum(s**2) / total_energy
    return int(np.searchsorted(cumulative, 1.0 - tol) + 1)
