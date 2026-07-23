"""插值 — 基于 scipy 封装"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import interpolate
from typing import Callable


def lagrange_interp(x: ArrayLike, y: ArrayLike) -> Callable[[ArrayLike], NDArray]:
    """Lagrange 多项式插值 — 过所有数据点的唯一 ≤ n-1 次多项式

    Args:
        x: 插值节点, 必须互异
        y: 节点函数值

    Returns:
        插值函数 f(xx), 接受新的 x 坐标返回插值 y
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)

    # 构造 Lagrange 基函数的 barycentric 表示
    n = len(x_arr)
    w = np.ones(n)
    for j in range(n):
        w[j] = 1.0 / np.prod(x_arr[j] - np.delete(x_arr, j))
    # 避免符号反转
    w = w / np.max(np.abs(w))

    def interp_func(xx: ArrayLike) -> NDArray:
        xx_arr = np.asarray(xx, dtype=np.float64)
        # Barycentric 公式
        numer = np.zeros_like(xx_arr, dtype=np.float64)
        denom = np.zeros_like(xx_arr, dtype=np.float64)
        exact = np.zeros_like(xx_arr, dtype=bool)
        for j in range(n):
            diff = xx_arr - x_arr[j]
            mask = diff == 0
            exact = exact | mask
            term = w[j] / np.where(mask, 1.0, diff)
            numer = numer + term * y_arr[j]
            denom = denom + term
        result = numer / denom
        # 精确命中的点直接取 y 值
        for j in range(n):
            result[xx_arr == x_arr[j]] = y_arr[j]
        return result

    return interp_func


def newton_interp(x: ArrayLike, y: ArrayLike) -> Callable[[ArrayLike], NDArray]:
    """Newton 差商插值 — 便于增量添加节点

    Args:
        x: 插值节点
        y: 节点函数值

    Returns:
        插值函数 f(xx)
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    n = len(x_arr)

    # 计算差商表 (下三角)
    div_diff = np.zeros((n, n))
    div_diff[:, 0] = y_arr
    for j in range(1, n):
        for i in range(n - j):
            div_diff[i, j] = (div_diff[i + 1, j - 1] - div_diff[i, j - 1]) / (
                x_arr[i + j] - x_arr[i]
            )

    coeffs = div_diff[0, :]  # Newton 系数: f[x₀], f[x₀,x₁], ...

    def interp_func(xx: ArrayLike) -> NDArray:
        xx_arr = np.asarray(xx, dtype=np.float64).ravel()
        # Newton 形式: P(x) = c₀ + c₁(x-x₀) + c₂(x-x₀)(x-x₁) + ...
        result = np.full_like(xx_arr, coeffs[-1], dtype=np.float64)
        for k in range(n - 2, -1, -1):
            result = result * (xx_arr - x_arr[k]) + coeffs[k]
        return result

    return interp_func


def cubic_spline(
    x: ArrayLike, y: ArrayLike, kind: str = "cubic"
) -> Callable[[ArrayLike], NDArray]:
    """三次样条插值 (C² 连续)

    Args:
        x: 插值节点 (严格递增)
        y: 节点值
        kind: 'cubic' (三次) / 'linear' (线性) / 'quadratic' (二次)

    Returns:
        样条插值函数 f(xx)
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    spline = interpolate.interp1d(
        x_arr, y_arr, kind=kind, fill_value="extrapolate"
    )

    def interp_func(xx: ArrayLike) -> NDArray:
        return spline(np.asarray(xx))

    return interp_func


def linear_interp_grid(
    x: ArrayLike, y: ArrayLike, xx: ArrayLike
) -> NDArray:
    """线性插值 (便捷版本, 一次调用完成)

    Args:
        x: 已知节点
        y: 已知节点值
        xx: 待插值点

    Returns:
        插值结果
    """
    return np.interp(np.asarray(xx), np.asarray(x), np.asarray(y))
