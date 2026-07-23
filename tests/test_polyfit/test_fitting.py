"""多项式拟合测试"""

import numpy as np
import pytest
from model.polyfit.fitting import (
    polyfit_ls,
    polyval,
    poly_residual,
    r2_score,
    weighted_polyfit,
)


class TestPolyfitLS:
    """多项式拟合 — 生产验证"""

    @pytest.mark.prod
    def test_exact_linear(self):
        """精确线性拟合"""
        x = np.array([0.0, 1.0, 2.0, 3.0])
        y = 2.0 * x + 1.0
        p = polyfit_ls(x, y, 1)
        np.testing.assert_allclose(p, [2.0, 1.0], rtol=1e-10)

    @pytest.mark.prod
    def test_exact_quadratic(self):
        """精确二次拟合"""
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        y = x**2 + 3.0 * x + 5.0
        p = polyfit_ls(x, y, 2)
        np.testing.assert_allclose(p, [1.0, 3.0, 5.0], rtol=1e-10)

    @pytest.mark.prod
    def test_noisy_fit(self):
        """含噪声拟合 — 系数接近真实值"""
        rng = np.random.default_rng(42)
        x = np.linspace(0, 10, 20)
        y_true = 1.5 * x + 2.0
        y = y_true + rng.normal(0, 0.5, 20)
        p = polyfit_ls(x, y, 1)
        # 噪声下系数近似
        np.testing.assert_allclose(p, [1.5, 2.0], rtol=0.3)

    @pytest.mark.prod
    def test_output_length(self):
        """输出系数个数 = deg + 1"""
        x = np.linspace(0, 1, 10)
        y = np.sin(x * np.pi)
        for deg in [1, 3, 5]:
            p = polyfit_ls(x, y, deg)
            assert len(p) == deg + 1


class TestPolyval:
    """多项式求值 — 生产验证"""

    @pytest.mark.prod
    def test_linear_eval(self):
        y = polyval([2.0, 1.0], np.array([0.0, 1.0, 2.0]))
        expected = np.array([1.0, 3.0, 5.0])
        np.testing.assert_allclose(y, expected)

    @pytest.mark.prod
    def test_scalar_input(self):
        y = polyval([1.0, 0.0, 0.0], 3.0)  # x^2 at x=3
        assert y == pytest.approx(9.0)


class TestPolyResidual:
    """残差 — 生产验证"""

    @pytest.mark.prod
    def test_exact_fit_zero_residual(self):
        x = np.array([0.0, 1.0, 2.0])
        y = 3.0 * x + 1.0
        p = polyfit_ls(x, y, 1)
        r = poly_residual(p, x, y)
        np.testing.assert_allclose(r, np.zeros(3), atol=1e-12)

    @pytest.mark.prod
    def test_residual_length(self):
        x = np.linspace(0, 1, 15)
        y = np.random.randn(15)
        p = polyfit_ls(x, y, 3)
        r = poly_residual(p, x, y)
        assert len(r) == 15


class TestR2Score:
    """R² — 生产验证"""

    @pytest.mark.prod
    def test_perfect_fit(self):
        x = np.linspace(0, 10, 20)
        y = 2.0 * x + 3.0
        p = [2.0, 3.0]
        assert r2_score(p, x, y) == pytest.approx(1.0)

    @pytest.mark.prod
    def test_poor_fit_low_r2(self):
        """差拟合 R² 较低"""
        x = np.linspace(0, 10, 30)
        y_true = x**2
        # 用常数拟合二次函数, R² 应很低
        p = [0.0, 0.0, np.mean(y_true)]  # y = mean(y)
        r2 = r2_score(p, x, y_true)
        assert r2 < 0.9


class TestWeightedPolyfit:
    """加权拟合 — 生产验证"""

    @pytest.mark.prod
    def test_uniform_weights(self):
        """均匀权重等价于最小二乘"""
        x = np.linspace(0, 5, 20)
        y = 2.0 * x**2 - x + 3.0 + np.random.randn(20) * 0.1
        w = np.ones(20)
        p_w = weighted_polyfit(x, y, 2, w)
        p = polyfit_ls(x, y, 2)
        np.testing.assert_allclose(p_w, p, rtol=1e-10)

    @pytest.mark.prod
    def test_zero_weight_exclusion(self):
        """零权重点不参与拟合"""
        x = np.array([0.0, 1.0, 2.0, 3.0])
        y = np.array([0.0, 2.0, 4.0, 100.0])  # 最后一个离群
        w = np.array([1.0, 1.0, 1.0, 0.0])  # 排除离群点
        p = weighted_polyfit(x, y, 1, w)
        np.testing.assert_allclose(p, [2.0, 0.0], rtol=1e-10, atol=1e-14)


# ============================================================
# 研发扩展用例
# ============================================================

class TestPolyfitDev:
    @pytest.mark.extended
    def test_high_degree_fit(self):
        """高次多项式 — 不过拟合崩溃"""
        x = np.linspace(0, 1, 30)
        y = np.sin(x * 2 * np.pi) + np.random.randn(30) * 0.05
        p = polyfit_ls(x, y, 10)
        assert len(p) == 11
        r2 = r2_score(p, x, y)
        assert r2 > 0.9  # 高次应对正弦有较好拟合

    @pytest.mark.extended
    def test_noise_robustness(self):
        """不同噪声水平验证"""
        rng = np.random.default_rng(42)
        x = np.linspace(0, 5, 40)
        for noise_level in [0.01, 0.1, 1.0]:
            y = 1.5 * x + 2.0 + rng.normal(0, noise_level, 40)
            p = polyfit_ls(x, y, 1)
            r2 = r2_score(p, x, y)
            # 低噪声应有高 R²
            if noise_level < 0.1:
                assert r2 > 0.9

    @pytest.mark.extended
    @pytest.mark.parametrize("deg", [1, 2, 3, 5, 8])
    def test_degree_sweep(self, deg):
        """多种次数 — 均不崩溃"""
        x = np.linspace(0, 10, 50)
        y = np.exp(-x / 5) * np.sin(x)
        p = polyfit_ls(x, y, deg)
        assert len(p) == deg + 1
        assert not np.any(np.isnan(p))


class TestWeightedPolyfitDev:
    @pytest.mark.extended
    def test_importance_weighting(self):
        """大权重区域拟合更精确"""
        x = np.linspace(0, 5, 50)
        y = 2.0 * x + 1.0 + np.random.randn(50) * 0.5
        # 前 10 个点给极高权重
        w = np.ones(50)
        w[:10] = 100.0
        p = weighted_polyfit(x, y, 1, w)
        # 前 10 个点残差应较小
        r = poly_residual(p, x[:10], y[:10])
        r_unweighted = poly_residual(
            polyfit_ls(x, y, 1), x[:10], y[:10]
        )
        assert np.mean(r**2) <= np.mean(r_unweighted**2) * 1.1
