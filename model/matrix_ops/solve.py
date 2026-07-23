"""线性方程组求解 — 基于 scipy 封装"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import linalg
from typing import Optional, Tuple


def linear_solve(a: ArrayLike, b: ArrayLike) -> NDArray:
    """求解线性方程组: Ax = b

    Args:
        a: 系数矩阵, shape (n, n)
        b: 右端向量/矩阵, shape (n,) 或 (n, k)

    Returns:
        解向量/矩阵 x
    """
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    return linalg.solve(a_arr, b_arr)


def matrix_inverse(a: ArrayLike) -> NDArray:
    """矩阵求逆: A^{-1}

    Args:
        a: 方阵

    Returns:
        逆矩阵
    """
    return linalg.inv(np.asarray(a, dtype=np.float64))


def matrix_det(a: ArrayLike) -> float:
    """矩阵行列式: det(A)

    Args:
        a: 方阵

    Returns:
        行列式值
    """
    return float(linalg.det(np.asarray(a, dtype=np.float64)))


def least_squares(a: ArrayLike, b: ArrayLike, method: str = "gelsd") -> Tuple[NDArray, NDArray, int, NDArray]:
    """最小二乘求解: min ||Ax - b||₂

    Args:
        a: 系数矩阵, shape (m, n)
        b: 观测向量/矩阵
        method: 求解方法 'gelsd' / 'gelss' / 'gelsy'

    Returns:
        (x, residuals, rank, s) — 解向量、残差、有效秩、奇异值
    """
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    result = linalg.lstsq(a_arr, b_arr, lapack_driver=method)
    return result[0], result[1], result[2], result[3]


def solve_triangular(
    a: ArrayLike, b: ArrayLike, lower: bool = False
) -> NDArray:
    """三角方程组求解: Tx = b (T 为上三角或下三角)

    Args:
        a: 三角矩阵, shape (n, n)
        b: 右端向量/矩阵
        lower: True 表示下三角, False 表示上三角

    Returns:
        解 x
    """
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    return linalg.solve_triangular(a_arr, b_arr, lower=lower)
