"""伪逆与正则化测试"""

import numpy as np
import pytest
from model.svd.pseudo_inverse import (
    pseudo_inverse,
    solve_via_svd,
    tikhonov_regularized,
)


class TestPseudoInverse:
    """Moore-Penrose 伪逆 — 生产验证"""

    @pytest.mark.prod
    def test_invertible(self, random_matrix):
        """可逆方阵: A⁺ = A⁻¹"""
        a = random_matrix(4, 4)
        a_pinv = pseudo_inverse(a)
        a_inv = np.linalg.inv(a)
        np.testing.assert_allclose(a_pinv, a_inv, rtol=1e-10)

    @pytest.mark.prod
    def test_penrose_condition_1(self, random_matrix):
        """A A⁺ A = A"""
        a = random_matrix(4, 3)
        a_pinv = pseudo_inverse(a)
        np.testing.assert_allclose(a @ a_pinv @ a, a, rtol=1e-10)

    @pytest.mark.prod
    def test_penrose_condition_2(self, random_matrix):
        """A⁺ A A⁺ = A⁺"""
        a = random_matrix(3, 4)
        a_pinv = pseudo_inverse(a)
        np.testing.assert_allclose(a_pinv @ a @ a_pinv, a_pinv, rtol=1e-10)

    @pytest.mark.prod
    def test_rank_deficient(self):
        """秩亏矩阵伪逆"""
        a = np.array([[1.0, 2.0], [2.0, 4.0]])
        a_pinv = pseudo_inverse(a)
        # 验证 Penrose 条件
        np.testing.assert_allclose(a @ a_pinv @ a, a, rtol=1e-8)


class TestSolveViaSVD:
    """SVD 最小二乘 — 生产验证"""

    @pytest.mark.prod
    def test_vs_numpy_lstsq(self, random_matrix, random_vector):
        """与 numpy.linalg.lstsq 结果一致"""
        a = random_matrix(6, 4)
        b = random_vector(6)
        x_svd = solve_via_svd(a, b)
        x_lstsq, _, _, _ = np.linalg.lstsq(a, b, rcond=None)
        np.testing.assert_allclose(x_svd, x_lstsq, rtol=1e-10)

    @pytest.mark.prod
    def test_exact_solution(self, random_matrix, random_vector):
        """适定方程组: 精确解"""
        n = 4
        a = random_matrix(n, n)
        x_true = random_vector(n)
        b = a @ x_true
        x = solve_via_svd(a, b)
        np.testing.assert_allclose(x, x_true, rtol=1e-10)


class TestTikhonovRegularized:
    """Tikhonov 正则化 — 生产验证"""

    @pytest.mark.prod
    def test_small_alpha_like_unregularized(self, random_matrix, random_vector):
        """α → 0 时趋近普通最小二乘"""
        a = random_matrix(5, 3)
        b = random_vector(5)
        x_tiny = tikhonov_regularized(a, b, alpha=1e-8)
        x_ls = solve_via_svd(a, b)
        np.testing.assert_allclose(x_tiny, x_ls, rtol=1e-5)

    @pytest.mark.prod
    def test_large_alpha_suppresses(self):
        """α → ∞ 时解趋近 0"""
        a = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        b = np.array([1.0, 2.0, 3.0])
        x = tikhonov_regularized(a, b, alpha=1e6)
        # 大正则化解应接近 0
        assert np.linalg.norm(x) < 1e-5

    @pytest.mark.prod
    def test_regularized_norm_smaller(self, random_matrix, random_vector):
        """正则化解范数 ≤ 未正则化解范数"""
        a = random_matrix(8, 5)
        b = random_vector(8)
        x_unreg = solve_via_svd(a, b)
        x_reg = tikhonov_regularized(a, b, alpha=1.0)
        assert np.linalg.norm(x_reg) <= np.linalg.norm(x_unreg) * 1.01


# ============================================================
# 研发扩展用例
# ============================================================

class TestPseudoInverseDev:
    @pytest.mark.extended
    def test_rectangular_tall(self, random_matrix):
        """瘦高矩阵伪逆"""
        a = random_matrix(20, 5)
        a_pinv = pseudo_inverse(a)
        assert a_pinv.shape == (5, 20)
        np.testing.assert_allclose(a @ a_pinv @ a, a, rtol=1e-8)

    @pytest.mark.extended
    def test_rectangular_wide(self, random_matrix):
        """矮宽矩阵伪逆"""
        a = random_matrix(5, 20)
        a_pinv = pseudo_inverse(a)
        assert a_pinv.shape == (20, 5)
        np.testing.assert_allclose(a @ a_pinv @ a, a, rtol=1e-8)


class TestTikhonovDev:
    @pytest.mark.extended
    @pytest.mark.parametrize("alpha", [0.01, 0.1, 1.0, 10.0, 100.0])
    def test_alpha_sweep(self, random_matrix, random_vector, alpha):
        """正则化参数扫描 — 解始终有限"""
        a = random_matrix(10, 6)
        b = random_vector(10)
        x = tikhonov_regularized(a, b, alpha=alpha)
        assert not np.any(np.isnan(x))
        assert not np.any(np.isinf(x))

    @pytest.mark.extended
    def test_monotonic_norm(self, random_matrix, random_vector):
        """α 增大 → 解范数单调递减"""
        a = random_matrix(10, 5)
        b = random_vector(10)
        norms = []
        for alpha in [0.1, 1.0, 10.0]:
            x = tikhonov_regularized(a, b, alpha=alpha)
            norms.append(np.linalg.norm(x))
        for i in range(len(norms) - 1):
            assert norms[i] >= norms[i + 1] * 0.99  # 近似单调
