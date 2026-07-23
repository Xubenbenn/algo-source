"""多项式求根、微积分 — 基于 numpy 封装"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from typing import List, Tuple


def poly_roots(p: ArrayLike) -> NDArray:
    """求多项式所有根 (包括复数): p[0]·x^n + ... + p[n] = 0

    Args:
        p: 多项式系数 (降幂排列)

    Returns:
        根数组 (可能含复数)
    """
    return np.roots(np.asarray(p, dtype=np.float64))


def poly_derivative(p: ArrayLike, m: int = 1) -> NDArray:
    """多项式 m 阶导数系数

    Args:
        p: 原多项式系数 (降幂)
        m: 求导阶数

    Returns:
        导数多项式系数 (降幂), 长度 = len(p) - m
    """
    result = np.asarray(p, dtype=np.float64)
    for _ in range(m):
        result = np.polyder(result)
    return result


def poly_integral(p: ArrayLike, m: int = 1, k: List[float] = None) -> NDArray:
    """多项式 m 次积分系数

    Args:
        p: 原多项式系数 (降幂)
        m: 积分次数
        k: 积分常数列表 (长度为 m), 默认全 0

    Returns:
        积分多项式系数 (降幂), 长度 = len(p) + m
    """
    result = np.asarray(p, dtype=np.float64)
    if k is None:
        k_list = [0.0] * m
    else:
        k_list = list(k)
    for i in range(m):
        result = np.polyint(result, k=k_list[i] if i < len(k_list) else 0)
    return result


def find_extrema(p: ArrayLike, x_range: Tuple[float, float] = None) -> NDArray:
    """求多项式在区间内的所有极值点 (导数为 0 的实根)

    Args:
        p: 多项式系数
        x_range: 可选, 筛选区间 (x_min, x_max)

    Returns:
        极值点 x 坐标数组 (升序)
    """
    deriv = poly_derivative(p, m=1)
    all_roots = poly_roots(deriv)
    # 保留实根
    real_roots = np.sort(all_roots[np.isreal(all_roots)].real)
    if x_range is not None:
        real_roots = real_roots[
            (real_roots >= x_range[0]) & (real_roots <= x_range[1])
        ]
    return real_roots
