"""线性方程组求解测试"""

import numpy as np
import pytest
from model.matrix_ops.solve import (
    linear_solve,
    matrix_inverse,
    matrix_det,
    least_squares,
    solve_triangular,
)


# ============================================================
# 生产环境用例 (prod)
# ============================================================

class TestLinearSolve:
    """线性方程组求解"""

    @pytest.mark.prod
    def test_solve_well_conditioned(self, random_matrix, random_vector):
        """良态方程组 Ax=b"""
        n = 4
        a = random_matrix(n, n)
        x_true = random_vector(n)
        b = a @ x_true
        x = linear_solve(a, b)
        np.testing.assert_allclose(x, x_true, rtol=1e-10)

    @pytest.mark.prod
    def test_solve_identity(self):
        """Ix = b → x = b"""
        b = np.array([1.0, 2.0, 3.0])
        x = linear_solve(np.eye(3), b)
        np.testing.assert_allclose(x, b)

    @pytest.mark.prod
    def test_solve_multiple_rhs(self, random_matrix):
        """多右端项"""
        a = random_matrix(3, 3)
        b = random_matrix(3, 2)
        x = linear_solve(a, b)
        np.testing.assert_allclose(a @ x, b, rtol=1e-10)


class TestMatrixInverse:
    """矩阵求逆"""

    @pytest.mark.prod
    def test_inverse(self, random_matrix):
        """A · A^{-1} = I"""
        a = random_matrix(4, 4)
        a_inv = matrix_inverse(a)
        np.testing.assert_allclose(a @ a_inv, np.eye(4), rtol=1e-10, atol=1e-14)

    @pytest.mark.prod
    def test_inverse_2x2(self):
        """2×2 已知逆矩阵"""
        a = np.array([[1.0, 2.0], [3.0, 4.0]])
        a_inv = matrix_inverse(a)
        expected = np.array([[-2.0, 1.0], [1.5, -0.5]])
        np.testing.assert_allclose(a_inv, expected, rtol=1e-10)


class TestMatrixDet:
    """行列式"""

    @pytest.mark.prod
    def test_det_identity(self):
        assert matrix_det(np.eye(5)) == pytest.approx(1.0)

    @pytest.mark.prod
    def test_det_zero(self):
        """奇异矩阵行列式为 0"""
        a = np.array([[1.0, 2.0], [2.0, 4.0]])
        assert abs(matrix_det(a)) < 1e-12

    @pytest.mark.prod
    def test_det_triangular(self):
        """三角矩阵 det = 对角线乘积"""
        a = np.array([[3.0, 1.0, 2.0], [0.0, 4.0, 5.0], [0.0, 0.0, 6.0]])
        result = matrix_det(a)
        assert result == pytest.approx(72.0)  # 3×4×6


class TestLeastSquares:
    """最小二乘"""

    @pytest.mark.prod
    def test_overdetermined(self, random_matrix, random_vector):
        """超定方程组"""
        a = random_matrix(6, 4)
        b = random_vector(6)
        x, residuals, rank, s = least_squares(a, b)
        assert x.shape == (4,)
        assert rank > 0
        assert len(s) == min(6, 4)

    @pytest.mark.prod
    def test_exact_fit(self):
        """精确拟合"""
        a = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        b = np.array([1.0, 2.0, 3.0])
        x, _, _, _ = least_squares(a, b)
        # 残差应为 0
        residual = np.linalg.norm(a @ x - b)
        assert residual < 1e-10


class TestSolveTriangular:
    """三角方程组"""

    @pytest.mark.prod
    def test_upper_triangular(self):
        a = np.array([[3.0, 1.0], [0.0, 2.0]])
        b = np.array([5.0, 4.0])
        x = solve_triangular(a, b, lower=False)
        np.testing.assert_allclose(a @ x, b, rtol=1e-10)

    @pytest.mark.prod
    def test_lower_triangular(self):
        a = np.array([[2.0, 0.0], [1.0, 3.0]])
        b = np.array([2.0, 7.0])
        x = solve_triangular(a, b, lower=True)
        np.testing.assert_allclose(a @ x, b, rtol=1e-10)


# ============================================================
# 研发环境扩展用例 (dev)
# ============================================================

class TestLinearSolveDev:
    @pytest.mark.extended
    def test_near_singular_warning(self, random_matrix):
        """近奇异矩阵 — 应完成计算"""
        n = 10
        a = random_matrix(n, n)
        # 人工降低条件: 缩小最后一行的值
        a[-1, :] *= 1e-8
        b = random_matrix(n, 1)[:, 0]
        try:
            x = linear_solve(a, b)
            assert not np.any(np.isnan(x))
        except np.linalg.LinAlgError:
            pass  # 奇异错误也是可接受的结果

    @pytest.mark.extended
    @pytest.mark.parametrize("n", [2, 5, 10, 20])
    def test_various_sizes(self, random_matrix, random_vector, n):
        a = random_matrix(n, n)
        x_true = random_vector(n)
        b = a @ x_true
        x = linear_solve(a, b)
        np.testing.assert_allclose(x, x_true, rtol=1e-10)


class TestLeastSquaresDev:
    @pytest.mark.extended
    def test_all_methods(self, random_matrix, random_vector):
        """三种 LAPACK 驱动方法均可用"""
        a = random_matrix(10, 4)
        b = random_vector(10)
        for method in ["gelsd", "gelss", "gelsy"]:
            x, _, rank, _ = least_squares(a, b, method=method)
            assert x.shape == (4,)
            assert rank > 0

    @pytest.mark.extended
    def test_rank_deficient(self):
        """秩亏矩阵"""
        a = np.array([[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0]])
        b = np.array([6.0, 12.0, 18.0])
        x, _, rank, s = least_squares(a, b)
        assert rank < 3  # 秩亏

    @pytest.mark.extended
    def test_large_overdetermined(self, random_matrix, random_vector):
        """大规模超定 — 不崩溃"""
        a = random_matrix(200, 10)
        b = random_vector(200)
        x, _, _, _ = least_squares(a, b)
        assert x.shape == (10,)
        assert not np.any(np.isnan(x))
