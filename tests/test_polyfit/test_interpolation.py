"""插值测试"""

import numpy as np
import pytest
from model.polyfit.interpolation import (
    lagrange_interp,
    newton_interp,
    cubic_spline,
    linear_interp_grid,
)


class TestLagrangeInterp:
    """Lagrange 插值 — 生产验证"""

    @pytest.mark.prod
    def test_passes_through_nodes(self):
        """插值函数过所有节点"""
        x = np.array([0.0, 1.0, 2.0, 3.0])
        y = np.array([1.0, 2.0, 0.0, 3.0])
        f = lagrange_interp(x, y)
        y_interp = f(x)
        np.testing.assert_allclose(y_interp, y, rtol=1e-10)

    @pytest.mark.prod
    def test_midpoint_interpolation(self):
        """中间点插值"""
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 1.0, 4.0])  # y = x^2
        f = lagrange_interp(x, y)
        y_mid = f(np.array([0.5]))
        assert y_mid[0] == pytest.approx(0.25, rel=0.001)

    @pytest.mark.prod
    def test_single_point(self):
        """单节点退化"""
        f = lagrange_interp(np.array([5.0]), np.array([42.0]))
        assert f([5.0])[0] == pytest.approx(42.0)


class TestNewtonInterp:
    """Newton 插值 — 生产验证"""

    @pytest.mark.prod
    def test_passes_through_nodes(self):
        x = np.array([0.0, 1.0, 2.0, 3.0])
        y = np.array([1.0, 3.0, 2.0, 4.0])
        f = newton_interp(x, y)
        y_interp = f(x)
        np.testing.assert_allclose(y_interp, y, rtol=1e-10)

    @pytest.mark.prod
    def test_vs_lagrange(self):
        """与 Lagrange 插值一致"""
        x = np.array([0.0, 1.0, 3.0, 4.0])
        y = np.array([2.0, 1.0, 4.0, 3.0])
        f_newton = newton_interp(x, y)
        f_lagrange = lagrange_interp(x, y)
        xx = np.linspace(0, 4, 20)
        np.testing.assert_allclose(
            f_newton(xx), f_lagrange(xx), rtol=1e-10
        )


class TestCubicSpline:
    """三次样条 — 生产验证"""

    @pytest.mark.prod
    def test_passes_through_nodes(self):
        x = np.array([0.0, 1.0, 2.0, 3.0])
        y = np.array([0.0, 2.0, 1.0, 3.0])
        f = cubic_spline(x, y, kind="cubic")
        y_interp = f(x)
        np.testing.assert_allclose(y_interp, y, rtol=1e-10)

    @pytest.mark.prod
    def test_linear_spline(self):
        """线性样条"""
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 2.0, 0.0])
        f = cubic_spline(x, y, kind="linear")
        result = f(np.array([0.5, 1.5]))
        expected = np.array([1.0, 1.0])
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    @pytest.mark.prod
    def test_monotonic_increasing(self):
        """单调数据样条插值"""
        x = np.linspace(0, 5, 10)
        y = x**2
        f = cubic_spline(x, y, kind="cubic")
        xx = np.linspace(0, 5, 50)
        yy = f(xx)
        np.testing.assert_allclose(yy, xx**2, rtol=0.05)


class TestLinearInterpGrid:
    """线性插值 — 生产验证"""

    @pytest.mark.prod
    def test_interpolation(self):
        x = np.array([0.0, 1.0, 2.0, 3.0])
        y = np.array([0.0, 2.0, 4.0, 6.0])  # y = 2x
        result = linear_interp_grid(x, y, np.array([0.5, 1.5, 2.5]))
        expected = np.array([1.0, 3.0, 5.0])
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    @pytest.mark.prod
    def test_out_of_bounds(self):
        """外推 — np.interp 默认裁剪到边界值"""
        x = np.array([0.0, 2.0])
        y = np.array([0.0, 4.0])
        result = linear_interp_grid(x, y, np.array([-1.0, 3.0]))
        # np.interp 不支持外推, 返回边界值
        expected = np.array([0.0, 4.0])
        np.testing.assert_allclose(result, expected)


# ============================================================
# 研发扩展用例
# ============================================================

class TestInterpolationDev:
    @pytest.mark.extended
    def test_lagrange_many_nodes(self):
        """大量节点 Lagrange — 不崩溃"""
        n = 20
        x = np.linspace(0, 10, n)
        y = np.cos(x)
        f = lagrange_interp(x, y)
        xx = np.linspace(0, 10, 100)
        yy = f(xx)
        assert not np.any(np.isnan(yy))

    @pytest.mark.extended
    def test_spline_vs_original(self):
        """样条逼近连续函数"""
        x_nodes = np.linspace(0, 2 * np.pi, 12)
        y_nodes = np.sin(x_nodes)
        f = cubic_spline(x_nodes, y_nodes, kind="cubic")
        xx = np.linspace(0, 2 * np.pi, 200)
        yy = f(xx)
        # 样条应较好逼近正弦
        max_err = np.max(np.abs(yy - np.sin(xx)))
        assert max_err < 0.05

    @pytest.mark.extended
    @pytest.mark.parametrize("kind", ["linear", "quadratic", "cubic"])
    def test_spline_kinds(self, kind):
        """各种样条类型"""
        x = np.linspace(0, 5, 10)
        y = np.sqrt(x + 0.1)
        f = cubic_spline(x, y, kind=kind)
        xx = np.array([0.5, 2.5, 4.5])
        yy = f(xx)
        assert not np.any(np.isnan(yy))

    @pytest.mark.extended
    def test_runge_phenomenon(self):
        """Runge 现象 — 高阶多项式边界振荡"""
        # 等距节点插值 Runge 函数
        def runge(x):
            return 1.0 / (1.0 + 25.0 * x**2)

        n = 15
        x_nodes = np.linspace(-1, 1, n)
        y_nodes = runge(x_nodes)
        f = lagrange_interp(x_nodes, y_nodes)
        xx = np.linspace(-1, 1, 200)
        yy = f(xx)
        # 端点附近应有较大误差 (Runge 现象)
        errors = np.abs(yy - runge(xx))
        # 检查靠近边界的误差 (>0.5 处), 至少有一处 >0.1
        near_boundary = np.where(np.abs(xx) > 0.9)[0]
        assert np.max(errors[near_boundary]) > 0.1
