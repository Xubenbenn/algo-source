"""矩阵分解测试"""

import numpy as np
import pytest
from model.matrix_ops.decomposition import (
    lu_decompose,
    qr_decompose,
    cholesky_decompose,
    eigen_decompose,
    schur_decompose,
)


# ============================================================
# 生产环境用例 (prod)
# ============================================================

class TestLUDecompose:
    """LU 分解 — 生产验证"""

    @pytest.mark.prod
    def test_square_decompose(self, random_matrix):
        """PA = LU 恒等式验证"""
        a = random_matrix(4, 4)
        p, l, u = lu_decompose(a)
        # PA = LU
        np.testing.assert_allclose(a, p @ l @ u, rtol=1e-10)

    @pytest.mark.prod
    def test_l_is_lower_triangular(self, random_matrix):
        a = random_matrix(5, 5)
        _, l, _ = lu_decompose(a)
        # L 应为下三角 (含单位对角线)
        for i in range(l.shape[0]):
            for j in range(i + 1, l.shape[1]):
                assert abs(l[i, j]) < 1e-12, f"L[{i},{j}] 应≈0"

    @pytest.mark.prod
    def test_u_is_upper_triangular(self, random_matrix):
        a = random_matrix(5, 5)
        _, _, u = lu_decompose(a)
        for i in range(1, u.shape[0]):
            for j in range(i):
                assert abs(u[i, j]) < 1e-12, f"U[{i},{j}] 应≈0"


class TestQRDecompose:
    """QR 分解 — 生产验证"""

    @pytest.mark.prod
    def test_full_qr(self, random_matrix):
        """A = QR"""
        a = random_matrix(4, 3)
        q, r = qr_decompose(a, mode="full")
        np.testing.assert_allclose(a, q @ r, rtol=1e-10, atol=1e-14)

    @pytest.mark.prod
    def test_q_orthogonal(self, random_matrix):
        """Q^T Q = I"""
        a = random_matrix(4, 4)
        q, _ = qr_decompose(a)
        np.testing.assert_allclose(q.T @ q, np.eye(4), rtol=1e-10, atol=1e-14)

    @pytest.mark.prod
    def test_r_upper_triangular(self, random_matrix):
        a = random_matrix(4, 3)
        _, r = qr_decompose(a)
        for i in range(1, r.shape[0]):
            for j in range(min(i, r.shape[1])):
                assert abs(r[i, j]) < 1e-12

    @pytest.mark.prod
    def test_economic_qr(self, random_matrix):
        """经济型 QR — Q shape (m, k)"""
        a = random_matrix(5, 3)
        q, r = qr_decompose(a, mode="economic")
        assert q.shape == (5, 3)
        assert r.shape == (3, 3)
        np.testing.assert_allclose(a, q @ r, rtol=1e-10, atol=1e-14)


class TestCholeskyDecompose:
    """Cholesky — 生产验证"""

    @pytest.mark.prod
    def test_spd_decompose(self, random_matrix):
        """A = LL^T"""
        a = random_matrix(4, 4, method="spd")
        l = cholesky_decompose(a, lower=True)
        np.testing.assert_allclose(a, l @ l.T, rtol=1e-10)

    @pytest.mark.prod
    def test_upper_variant(self, random_matrix):
        """上三角变体 A = U^T U"""
        a = random_matrix(4, 4, method="spd")
        u = cholesky_decompose(a, lower=False)
        np.testing.assert_allclose(a, u.T @ u, rtol=1e-10)

    @pytest.mark.prod
    def test_non_spd_raises(self):
        """非正定矩阵应报错"""
        a = np.array([[1.0, 2.0], [2.0, 1.0]])  # 非正定
        with pytest.raises(np.linalg.LinAlgError):
            cholesky_decompose(a)


class TestEigenDecompose:
    """特征分解 — 生产验证"""

    @pytest.mark.prod
    def test_symmetric_eigen(self):
        """对称矩阵: A v = λ v"""
        a = np.array([[4.0, 1.0], [1.0, 3.0]])
        w, v = eigen_decompose(a)
        for i in range(len(w)):
            np.testing.assert_allclose(
                a @ v[:, i], w[i] * v[:, i], rtol=1e-10
            )

    @pytest.mark.prod
    def test_eigenvalues_real_symmetric(self):
        """对称矩阵特征值全为实数"""
        a = np.array([[2.0, 1.0, 0.0], [1.0, 2.0, 1.0], [0.0, 1.0, 2.0]])
        w, _ = eigen_decompose(a)
        assert np.all(np.isreal(w))


class TestSchurDecompose:
    """Schur 分解 — 生产验证"""

    @pytest.mark.prod
    def test_schur_form(self, random_matrix):
        """A = Z T Z^H"""
        a = random_matrix(4, 4)
        t, z = schur_decompose(a)
        np.testing.assert_allclose(a, z @ t @ z.T.conj(), rtol=1e-10)

    @pytest.mark.prod
    def test_z_unitary(self, random_matrix):
        """Z 为酉矩阵"""
        a = random_matrix(4, 4)
        _, z = schur_decompose(a)
        np.testing.assert_allclose(
            z @ z.T.conj(), np.eye(4), rtol=1e-10, atol=1e-14
        )


# ============================================================
# 研发环境扩展用例 (dev)
# ============================================================

class TestLUDecomposeDev:
    @pytest.mark.extended
    def test_large_matrix(self, random_matrix):
        """大矩阵 LU — 不应崩溃"""
        n = 100
        a = random_matrix(n, n)
        p, l, u = lu_decompose(a)
        np.testing.assert_allclose(a, p @ l @ u, rtol=1e-6, atol=1e-12)

    @pytest.mark.extended
    @pytest.mark.parametrize("n", [2, 3, 5, 10, 20])
    def test_various_sizes(self, random_matrix, n):
        """多种尺寸的 LU"""
        a = random_matrix(n, n)
        p, l, u = lu_decompose(a)
        np.testing.assert_allclose(a, p @ l @ u, rtol=1e-8, atol=1e-13)


class TestQRDecomposeDev:
    @pytest.mark.extended
    def test_tall_matrix(self, random_matrix):
        """瘦高矩阵 QR"""
        a = random_matrix(50, 5)
        q, r = qr_decompose(a, mode="economic")
        assert q.shape == (50, 5)
        assert r.shape == (5, 5)
        np.testing.assert_allclose(a, q @ r, rtol=1e-8)


class TestEigenDecomposeDev:
    @pytest.mark.extended
    def test_random_eigenvalues(self, random_matrix):
        """随机矩阵 — 特征值约束验证"""
        for n in [5, 10]:
            a = random_matrix(n, n, method="normal")
            w, v = eigen_decompose(a)
            # 所有特征值非 NaN
            assert not np.any(np.isnan(w))

    @pytest.mark.extended
    def test_trace_equals_sum_eigenvalues(self, random_matrix):
        """迹 = 特征值之和"""
        a = random_matrix(6, 6)
        w, _ = eigen_decompose(a)
        np.testing.assert_allclose(
            np.sum(w), np.trace(a), rtol=1e-10
        )
