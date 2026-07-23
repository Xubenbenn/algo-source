"""多项式求根与微积分测试"""

import numpy as np
import pytest
from model.polyfit.roots import (
    poly_roots,
    poly_derivative,
    poly_integral,
    find_extrema,
)


class TestPolyRoots:
    """求根 — 生产验证"""

    @pytest.mark.prod
    def test_quadratic_roots(self):
        """二次方程: x² - 5x + 6 = 0 → x = 2, 3"""
        p = [1.0, -5.0, 6.0]
        roots = poly_roots(p)
        roots_sorted = np.sort(roots)
        np.testing.assert_allclose(roots_sorted, [2.0, 3.0], rtol=1e-10)

    @pytest.mark.prod
    def test_linear_root(self):
        """一次方程: 2x + 4 = 0 → x = -2"""
        roots = poly_roots([2.0, 4.0])
        np.testing.assert_allclose(roots, [-2.0], rtol=1e-10)

    @pytest.mark.prod
    def test_cubic_has_three_roots(self):
        """三次方程有 3 个根"""
        # x³ - 6x² + 11x - 6 = (x-1)(x-2)(x-3)
        p = [1.0, -6.0, 11.0, -6.0]
        roots = poly_roots(p)
        assert len(roots) == 3
        np.testing.assert_allclose(
            np.sort(roots), [1.0, 2.0, 3.0], rtol=1e-10
        )

    @pytest.mark.prod
    def test_complex_roots(self):
        """复根: x² + 1 = 0 → x = ±i"""
        roots = poly_roots([1.0, 0.0, 1.0])
        assert len(roots) == 2
        np.testing.assert_allclose(
            np.sort(np.abs(roots)), [1.0, 1.0], rtol=1e-10
        )


class TestPolyDerivative:
    """多项式求导 — 生产验证"""

    @pytest.mark.prod
    def test_first_derivative(self):
        """(x³)' = 3x²"""
        p = [1.0, 0.0, 0.0, 0.0]  # x^3
        dp = poly_derivative(p, m=1)
        np.testing.assert_allclose(dp, [3.0, 0.0, 0.0], rtol=1e-10)

    @pytest.mark.prod
    def test_second_derivative(self):
        """(x³)'' = 6x"""
        p = [1.0, 0.0, 0.0, 0.0]
        d2p = poly_derivative(p, m=2)
        np.testing.assert_allclose(d2p, [6.0, 0.0], rtol=1e-10)

    @pytest.mark.prod
    def test_constant_derivative(self):
        """常数导数为空 (0 多项式)"""
        dp = poly_derivative([5.0], m=1)
        assert len(dp) == 0 or np.all(dp == 0)


class TestPolyIntegral:
    """多项式积分 — 生产验证"""

    @pytest.mark.prod
    def test_monomial_integral(self):
        """∫ x dx = x²/2"""
        p = [1.0, 0.0]  # x
        integral = poly_integral(p, m=1, k=[0.0])
        np.testing.assert_allclose(integral, [0.5, 0.0, 0.0], rtol=1e-10)

    @pytest.mark.prod
    def test_with_constant(self):
        """∫ 2x dx = x² + C (C=3)"""
        p = [2.0, 0.0]
        integral = poly_integral(p, m=1, k=[3.0])
        np.testing.assert_allclose(integral, [1.0, 0.0, 3.0], rtol=1e-10)

    @pytest.mark.prod
    def test_double_integral(self):
        """∬ 1 dx = x²/2 + C₁x + C₂"""
        p = [1.0]
        integral = poly_integral(p, m=2, k=[0.0, 0.0])
        np.testing.assert_allclose(integral, [0.5, 0.0, 0.0], rtol=1e-10)


class TestFindExtrema:
    """极值点 — 生产验证"""

    @pytest.mark.prod
    def test_quadratic_extrema(self):
        """x² 的极值点在 x=0"""
        p = [1.0, 0.0, 0.0]  # x²
        ext = find_extrema(p, x_range=(-2.0, 2.0))
        np.testing.assert_allclose(ext, [0.0], rtol=1e-10)

    @pytest.mark.prod
    def test_cubic_extrema(self):
        """x³ - 3x 极值点在 x=±1"""
        p = [1.0, 0.0, -3.0, 0.0]  # x³ - 3x
        ext = find_extrema(p, x_range=(-3.0, 3.0))
        np.testing.assert_allclose(np.sort(ext), [-1.0, 1.0], rtol=1e-10)

    @pytest.mark.prod
    def test_no_extrema_outside_range(self):
        """区间外无极值点"""
        p = [1.0, 0.0, 0.0]  # x², 极值在 0
        ext = find_extrema(p, x_range=(1.0, 5.0))
        assert len(ext) == 0


# ============================================================
# 研发扩展用例
# ============================================================

class TestRootsDev:
    @pytest.mark.extended
    def test_high_degree_polynomial(self):
        """高次多项式 — 不崩溃"""
        # (x-1)(x-2)(x-3)(x-4)(x-5)(x-6)(x-7) 展开后为 7 次多项式
        roots_true = np.arange(1, 8, dtype=float)
        p = np.poly(roots_true)
        roots_found = poly_roots(p)
        np.testing.assert_allclose(
            np.sort(roots_found.real), roots_true, rtol=1e-8
        )

    @pytest.mark.extended
    def test_wilkinson_polynomial(self):
        """Wilkinson 多项式 — 数值稳定性测试"""
        # ∏(x - k), k=1..15 展开
        roots_true = np.arange(1, 16, dtype=float)
        p = np.poly(roots_true)
        roots_found = poly_roots(p)
        # 高阶 Wilkinson 多项式求根不稳定, 只检查不崩溃
        assert len(roots_found) == 15
        assert not np.any(np.isnan(roots_found))


class TestFindExtremaDev:
    @pytest.mark.extended
    def test_no_range_filter(self):
        """不给定范围时返回所有实极值点"""
        p = [1.0, 0.0, -3.0, 0.0]  # x³ - 3x
        ext = find_extrema(p)
        np.testing.assert_allclose(np.sort(ext), [-1.0, 1.0], rtol=1e-10)

    @pytest.mark.extended
    @pytest.mark.parametrize("degree", [3, 5, 7, 9])
    def test_derivative_order(self, degree):
        """高阶导数 → 降低次数"""
        p = np.ones(degree + 1)  # 全 1 系数
        for m in range(1, min(degree, 4)):
            dp = poly_derivative(p, m=m)
            assert len(dp) == degree + 1 - m
