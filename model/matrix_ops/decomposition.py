"""矩阵分解 — LU / QR / Cholesky / 特征分解，基于 scipy 封装"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import linalg
from typing import Tuple


def lu_decompose(a: ArrayLike) -> Tuple[NDArray, NDArray, NDArray]:
    """LU 分解: A = PLU

    Args:
        a: 方阵, shape (n, n)

    Returns:
        (P, L, U) — 置换矩阵、下三角、上三角, 满足 A = P L U
    """
    a_arr = np.asarray(a, dtype=np.float64)
    p, l, u = linalg.lu(a_arr)
    return p, l, u


def qr_decompose(a: ArrayLike, mode: str = "full") -> Tuple[NDArray, NDArray]:
    """QR 分解: A = QR

    Args:
        a: 输入矩阵, shape (m, n)
        mode: 'full' (完整 Q) / 'economic' (经济型 Q)

    Returns:
        (Q, R) — 正交矩阵 Q、上三角矩阵 R
    """
    a_arr = np.asarray(a, dtype=np.float64)
    if mode == "economic":
        q, r = linalg.qr(a_arr, mode="economic")
    else:
        q, r = linalg.qr(a_arr, mode="full")
    return q, r


def cholesky_decompose(a: ArrayLike, lower: bool = True) -> NDArray:
    """Cholesky 分解: A = LL^T (A 必须对称正定)

    Args:
        a: 对称正定矩阵, shape (n, n)
        lower: True 返回下三角 L, False 返回上三角 U

    Returns:
        下三角矩阵 L 或上三角矩阵 U
    """
    a_arr = np.asarray(a, dtype=np.float64)
    factor = linalg.cholesky(a_arr, lower=lower)
    return factor


def eigen_decompose(a: ArrayLike) -> Tuple[NDArray, NDArray]:
    """特征分解: A = V Λ V^{-1} (仅对称/Hermitian 保证正交)

    Args:
        a: 方阵, shape (n, n)

    Returns:
        (eigenvalues, eigenvectors) — 特征值向量和特征向量矩阵
    """
    a_arr = np.asarray(a, dtype=np.float64)
    w, v = linalg.eig(a_arr)
    return w, v


def schur_decompose(a: ArrayLike) -> Tuple[NDArray, NDArray]:
    """Schur 分解: A = Z T Z^H

    Args:
        a: 方阵

    Returns:
        (T, Z) — Schur 型上三角矩阵 T 和酉矩阵 Z
    """
    a_arr = np.asarray(a, dtype=np.float64)
    t, z = linalg.schur(a_arr)
    return t, z
