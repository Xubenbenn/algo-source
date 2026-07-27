"""基础矩阵运算 — 基于 numpy 封装"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from typing import Union


def matrix_multiply(a: ArrayLike, b: ArrayLike) -> NDArray:
    """矩阵乘法: C = A × B

    Args:
        a: 左矩阵, shape (m, k) 或 (k,)
        b: 右矩阵, shape (k, n) 或 (k,)

    Returns:
        乘积矩阵, shape (m, n) 或标量
    """
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    return np.dot(a_arr, b_arr)


def matrix_add(a: ArrayLike, b: ArrayLike) -> NDArray:
    """矩阵加法: C = A + B

    Args:
        a, b: 同型矩阵

    Returns:
        和矩阵
    """
    return np.add(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64))


def matrix_transpose(a: ArrayLike) -> NDArray:
    """矩阵转置: A^T

    Args:
        a: 输入矩阵

    Returns:
        转置矩阵
    """
    return np.asarray(a, dtype=np.float64).T


def matrix_trace(a: ArrayLike) -> float:
    """矩阵迹: Tr(A)

    Args:
        a: 方阵

    Returns:
        迹值（对角线元素之和）
    """
    return float(np.trace(np.asarray(a, dtype=np.float64)))


def matrix_norm(a: ArrayLike, ord: Union[str, int] = "fro") -> float:
    """矩阵范数

    Args:
        a: 输入矩阵
        ord: 范数类型, 'fro' (Frobenius) / 1 / 2 / np.inf

    Returns:
        范数值
    """
    return float(np.linalg.norm(np.asarray(a, dtype=np.float64), ord=ord))


def matrix_power(a: ArrayLike, n: int) -> NDArray:
    """矩阵幂: A^n (方阵, n ≥ 0)

    Args:
        a: 方阵, shape (m, m)
        n: 幂次, n=0 返回单位矩阵

    Returns:
        A^n
    """
    return np.linalg.matrix_power(np.asarray(a, dtype=np.float64), n)


def elementwise_multiply(a: ArrayLike, b: ArrayLike) -> NDArray:
    """逐元素乘法 (Hadamard 积): C[i,j] = A[i,j] × B[i,j]

    Args:
        a, b: 同型矩阵

    Returns:
        逐元素乘积
    """
    return np.multiply(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64))


def matrix_column_norm(a: ArrayLike, ord: Union[int, str] = 2) -> NDArray:
    """逐列范数: 返回每列的范数值向量

    Args:
        a: 输入矩阵, shape (m, n)
        ord: 范数类型 (2, 1, np.inf 等)

    Returns:
        每列范数值, shape (n,)
    """
    a_arr = np.asarray(a, dtype=np.float64)
    return np.array([np.linalg.norm(a_arr[:, j], ord=ord)
                     for j in range(a_arr.shape[1])])
