"""低秩逼近与矩阵分析测试"""

import numpy as np
import pytest
from model.svd.approximation import (
    low_rank_approx,
    reconstruction_error,
    condition_number,
    effective_rank,
)


class TestLowRankApprox:
    """低秩逼近 — 生产验证"""

    @pytest.mark.prod
    def test_rank_1_matrix_exact(self):
        """秩-1 矩阵可精确逼近"""
        u = np.array([1.0, 2.0, 3.0]).reshape(3, 1)
        v = np.array([4.0, 5.0]).reshape(1, 2)
        a = u @ v  # 秩1
        approx = low_rank_approx(a, 1)
        np.testing.assert_allclose(approx, a, rtol=1e-10)

    @pytest.mark.prod
    def test_approximation_shape(self, random_matrix):
        """低秩逼近保持形状"""
        a = random_matrix(5, 4)
        approx = low_rank_approx(a, 2)
        assert approx.shape == (5, 4)

    @pytest.mark.prod
    def test_full_rank_approx_equals_original(self, random_matrix):
        """秩-k = min(m,n) 时完全还原"""
        a = random_matrix(3, 4)
        k = min(3, 4)
        approx = low_rank_approx(a, k)
        np.testing.assert_allclose(approx, a, rtol=1e-10)

    @pytest.mark.prod
    def test_k_exceeds_min_dimension(self, random_matrix):
        """k 超过 min(m,n) 时自动截断"""
        a = random_matrix(3, 5)
        approx = low_rank_approx(a, 10)  # k > 3
        np.testing.assert_allclose(approx, a, rtol=1e-10)


class TestReconstructionError:
    """重构误差 — 生产验证"""

    @pytest.mark.prod
    def test_exact_reconstruction_zero_error(self, random_matrix):
        """完全重构误差为 0"""
        a = random_matrix(3, 3)
        err = reconstruction_error(a, 3)
        assert err < 1e-12

    @pytest.mark.prod
    def test_error_between_0_and_1(self, random_matrix):
        """误差 ∈ [0, 1]"""
        a = random_matrix(5, 4)
        for k in [1, 2, 3]:
            err = reconstruction_error(a, k)
            assert 0.0 <= err <= 1.0 + 1e-10

    @pytest.mark.prod
    def test_zero_matrix(self):
        err = reconstruction_error(np.zeros((4, 4)), 2)
        assert err == 0.0


class TestConditionNumber:
    """条件数 — 生产验证"""

    @pytest.mark.prod
    def test_identity(self):
        assert condition_number(np.eye(5)) == pytest.approx(1.0)

    @pytest.mark.prod
    def test_singular(self):
        a = np.array([[1.0, 2.0], [2.0, 4.0]])
        assert condition_number(a) > 1e6  # 近似无穷

    @pytest.mark.prod
    def test_well_conditioned(self, random_matrix):
        """良态矩阵条件数较小"""
        a = random_matrix(4, 4, method="spd")
        cond = condition_number(a)
        assert cond >= 1.0


class TestEffectiveRank:
    """有效秩 — 生产验证"""

    @pytest.mark.prod
    def test_identity(self):
        assert effective_rank(np.eye(5)) == 5

    @pytest.mark.prod
    def test_rank_deficient(self):
        a = np.array([[1.0, 2.0], [2.0, 4.0]])
        assert effective_rank(a) == 1


# ============================================================
# 研发扩展用例
# ============================================================

class TestLowRankApproxDev:
    @pytest.mark.extended
    def test_approximation_improves(self, random_matrix):
        """k 增大时逼近误差递减"""
        a = random_matrix(10, 10)
        errors = [reconstruction_error(a, k) for k in range(1, 11)]
        for i in range(len(errors) - 1):
            assert errors[i] >= errors[i + 1] * 0.99  # 近似单调

    @pytest.mark.extended
    def test_large_matrix(self, random_matrix):
        """大矩阵低秩逼近"""
        a = random_matrix(100, 100)
        approx = low_rank_approx(a, 10)
        assert approx.shape == (100, 100)
        assert not np.any(np.isnan(approx))


class TestConditionNumberDev:
    @pytest.mark.extended
    def test_scale_invariance(self, random_matrix):
        """κ(cA) = κ(A)"""
        a = random_matrix(4, 4)
        cond1 = condition_number(a)
        cond2 = condition_number(a * 2.5)
        np.testing.assert_allclose(cond1, cond2, rtol=1e-10)
