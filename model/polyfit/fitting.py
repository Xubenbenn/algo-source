"""多项式拟合 — 基于 numpy 封装"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from typing import Tuple


def polyfit_ls(x: ArrayLike, y: ArrayLike, deg: int) -> NDArray:
    """最小二乘多项式拟合: y ≈ p[0]·x^deg + ... + p[deg]
    update 0727
    Args:
        x: 自变量观测点
        y: 因变量观测值
        deg: 多项式次数

    Returns:
        系数向量 [p₀, p₁, ..., p_{deg}], 降幂排列
    """
    return np.polyfit(np.asarray(x), np.asarray(y), deg)


def polyval(p: ArrayLike, x: ArrayLike) -> NDArray:
    """多项式求值: y = p[0]·x^n + p[1]·x^{n-1} + ... + p[n]

    Args:
        p: 多项式系数 (降幂排列)
        x: 求值点

    Returns:
        多项式值
    """
    return np.polyval(np.asarray(p), np.asarray(x))


def poly_residual(p: ArrayLike, x: ArrayLike, y: ArrayLike) -> NDArray:
    """多项式拟合残差向量: r_i = y_i - p(x_i)

    Args:
        p: 多项式系数
        x: 自变量观测点
        y: 因变量观测值

    Returns:
        残差向量
    """
    y_pred = polyval(p, x)
    return np.asarray(y, dtype=np.float64) - y_pred


def r2_score(p: ArrayLike, x: ArrayLike, y: ArrayLike) -> float:
    """决定系数 R² (拟合优度)

    R² = 1 - SS_res / SS_tot

    Args:
        p: 多项式系数
        x: 自变量
        y: 观测值

    Returns:
        R² ∈ (-∞, 1], 越接近 1 表示拟合越好
    """
    y_arr = np.asarray(y, dtype=np.float64)
    ss_res = np.sum(poly_residual(p, x, y_arr) ** 2)
    ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
    return float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0


def weighted_polyfit(
    x: ArrayLike, y: ArrayLike, deg: int, w: ArrayLike
) -> NDArray:
    """加权最小二乘多项式拟合: min Σ w_i (y_i - p(x_i))²

    Args:
        x: 自变量
        y: 观测值
        deg: 多项式次数
        w: 权重 (与 x, y 等长)

    Returns:
        多项式系数 (降幂)
    """
    return np.polyfit(
        np.asarray(x), np.asarray(y), deg, w=np.asarray(w)
    )


def polyfit_ridge(
    x: ArrayLike, y: ArrayLike, deg: int, alpha: float = 1.0
) -> NDArray:
    """岭回归多项式拟合: min ||Ax - y||²₂ + α||x||²₂

    通过增广矩阵求解, 等价于权重衰减正则化。

    Args:
        x: 自变量观测点
        y: 因变量观测值
        deg: 多项式次数
        alpha: 正则化系数 (越大 → 系数收缩越强)

    Returns:
        多项式系数 (降幂)
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    # 构造 Vandermonde 矩阵 (deg+1 列, 降幂)
    a = np.vander(x_arr, deg + 1)
    # 增广矩阵: [A; √α·I],  [y; 0]
    n_cols = a.shape[1]
    a_aug = np.vstack([a, np.sqrt(alpha) * np.eye(n_cols)])
    y_aug = np.concatenate([y_arr, np.zeros(n_cols)])
    coef, *_ = np.linalg.lstsq(a_aug, y_aug, rcond=None)
    return coef
