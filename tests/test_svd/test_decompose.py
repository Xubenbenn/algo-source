"""SVD 分解测试"""

import numpy as np
import pytest
from model.svd.decompose import (
    svd_full,
    svd_economy,
    singular_values,
    svd_rank,
    svd_reconstruct,
)


class TestSVDFull:
    """完整 SVD — 生产验证"""

    @pytest.mark.prod
    def test_decomposition(self, random_matrix):
        """A = U Σ V^T"""
        a = random_matrix(4, 3)
        u, s, vt = svd_full(a)
        sigma = np.zeros((4, 3))
        np.fill_diagonal(sigma, s)
        np.testing.assert_allclose(a, u @ sigma @ vt, rtol=1e-10)

    @pytest.mark.prod
    def test_u_orthogonal(self, random_matrix):
        """U^T U = I"""
        a = random_matrix(4, 4)
        u, _, _ = svd_full(a)
        np.testing.assert_allclose(u.T @ u, np.eye(4), rtol=1e-10, atol=1e-14)

    @pytest.mark.prod
    def test_vt_orthogonal(self, random_matrix):
        """V V^T = I"""
        a = random_matrix(4, 4)
        _, _, vt = svd_full(a)
        np.testing.assert_allclose(vt @ vt.T, np.eye(4), rtol=1e-10, atol=1e-14)

    @pytest.mark.prod
    def test_singular_values_non_negative(self, random_matrix):
        """奇异值非负"""
        a = random_matrix(5, 5)
        _, s, _ = svd_full(a)
        assert np.all(s >= -1e-12)

    @pytest.mark.prod
    def test_singular_values_descending(self, random_matrix):
        """奇异值降序排列"""
        a = random_matrix(5, 3)
        _, s, _ = svd_full(a)
        for i in range(len(s) - 1):
            assert s[i] >= s[i + 1] - 1e-12


class TestSVDEconomy:
    """经济型 SVD — 生产验证"""

    @pytest.mark.prod
    def test_tall_economy(self, random_matrix):
        """m > n 时, U shape (m, n)"""
        a = random_matrix(6, 3)
        u, s, vt = svd_economy(a)
        assert u.shape == (6, 3)
        sigma = np.diag(s)
        np.testing.assert_allclose(a, u @ sigma @ vt, rtol=1e-10)

    @pytest.mark.prod
    def test_wide_economy(self, random_matrix):
        """m < n 时, U shape (m, m)"""
        a = random_matrix(3, 6)
        u, s, vt = svd_economy(a)
        assert u.shape == (3, 3)
        # 经济型: U(m×k) · diag(s)(k×k) · Vt(k×n), k = min(m,n)
        np.testing.assert_allclose(a, u @ np.diag(s) @ vt, rtol=1e-10)


class TestSingularValues:
    """仅计算奇异值 — 生产验证"""

    @pytest.mark.prod
    def test_vs_full_svd(self, random_matrix):
        """与完整 SVD 的奇异值一致"""
        a = random_matrix(5, 4)
        s_only = singular_values(a)
        _, s_full, _ = svd_full(a)
        np.testing.assert_allclose(s_only, s_full, rtol=1e-12)

    @pytest.mark.prod
    def test_zero_matrix(self):
        """零矩阵奇异值全为零"""
        s = singular_values(np.zeros((3, 3)))
        assert np.all(s < 1e-12)


class TestSVDReconstruct:
    """SVD 重构 — 生产验证"""

    @pytest.mark.prod
    def test_reconstruct_square(self, random_matrix):
        """A = U Σ V^T"""
        a = random_matrix(4, 4)
        u, s, vt = svd_full(a)
        result = svd_reconstruct(u, s, vt)
        np.testing.assert_allclose(result, a, rtol=1e-10)

    @pytest.mark.prod
    def test_reconstruct_economy(self, random_matrix):
        """经济型重构"""
        a = random_matrix(5, 3)
        u, s, vt = svd_economy(a)
        result = svd_reconstruct(u, s, vt)
        np.testing.assert_allclose(result, a, rtol=1e-10)


class TestSVDRank:
    """数值秩 — 生产验证"""

    @pytest.mark.prod
    def test_full_rank(self):
        """满秩矩阵"""
        a = np.eye(5)
        assert svd_rank(a) == 5

    @pytest.mark.prod
    def test_rank_deficient(self):
        """秩亏矩阵"""
        a = np.array([[1.0, 2.0], [2.0, 4.0]])
        assert svd_rank(a) == 1

    @pytest.mark.prod
    def test_zero_matrix_rank(self):
        assert svd_rank(np.zeros((4, 4))) == 0


# ============================================================
# 研发扩展用例
# ============================================================

class TestSVDSpecialCases:
    @pytest.mark.extended
    def test_vector_svd(self):
        """列向量 SVD"""
        a = np.array([[3.0], [4.0]])
        u, s, vt = svd_full(a)
        assert len(s) == 1
        assert s[0] == pytest.approx(5.0)  # ||[3,4]|| = 5
        np.testing.assert_allclose(a, u[:, :1] * s[0] @ vt, rtol=1e-10)

    @pytest.mark.extended
    @pytest.mark.parametrize("shape", [(10, 10), (20, 5), (5, 20), (1, 1)])
    def test_various_shapes(self, random_matrix, shape):
        a = random_matrix(*shape)
        u, s, vt = svd_full(a)
        k = min(shape)
        sigma = np.zeros(shape)
        np.fill_diagonal(sigma, s)
        np.testing.assert_allclose(a, u @ sigma @ vt, rtol=1e-10)

    @pytest.mark.extended
    def test_near_rank_deficient(self, random_matrix):
        """近秩亏矩阵"""
        n = 10
        a = random_matrix(n, n)
        s_full = singular_values(a)
        # 人工引入小奇异值
        a_mod = a.copy()
        a_mod[-1, :] = a_mod[0, :] * (1 + 1e-10)  # 近线性相关
        s_mod = singular_values(a_mod)
        # 最小奇异值应该变得很小
        assert s_mod[-1] < s_full[-1]

    @pytest.mark.extended
    def test_svd_energy_preservation(self, random_matrix):
        """||A||_F² = Σ σ_i²"""
        a = random_matrix(4, 4)
        _, s, _ = svd_full(a)
        energy_svd = np.sum(s**2)
        energy_direct = np.sum(a**2)
        np.testing.assert_allclose(energy_svd, energy_direct, rtol=1e-10)
