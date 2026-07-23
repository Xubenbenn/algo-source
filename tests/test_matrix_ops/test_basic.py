"""矩阵运算 — 基础操作测试"""

import numpy as np
import pytest
from model.matrix_ops.basic import (
    matrix_multiply,
    matrix_add,
    matrix_transpose,
    matrix_trace,
    matrix_norm,
    elementwise_multiply,
)


# ============================================================
# 生产环境用例 (prod) — 核心功能正确性
# ============================================================

class TestMatrixMultiply:
    """矩阵乘法 — 生产验证"""

    @pytest.mark.prod
    def test_square_multiply(self, random_matrix):
        """方阵乘法正确性"""
        a = random_matrix(3, 3)
        b = random_matrix(3, 3)
        result = matrix_multiply(a, b)
        expected = a @ b
        np.testing.assert_allclose(result, expected, rtol=1e-12)

    @pytest.mark.prod
    def test_vector_dot(self, random_vector):
        """向量内积"""
        a = random_vector(5)
        b = random_vector(5)
        result = matrix_multiply(a, b)
        expected = np.dot(a, b)
        assert isinstance(result, (float, np.floating))
        np.testing.assert_allclose(result, expected, rtol=1e-12)

    @pytest.mark.prod
    def test_identity(self):
        """乘以单位矩阵返回自身"""
        a = np.array([[2.0, 1.0], [3.0, 4.0]])
        eye = np.eye(2)
        result = matrix_multiply(a, eye)
        np.testing.assert_allclose(result, a, rtol=1e-12)

    @pytest.mark.prod
    def test_zero_matrix(self):
        """零矩阵乘积为零"""
        a = np.zeros((3, 3))
        b = np.ones((3, 3))
        result = matrix_multiply(a, b)
        np.testing.assert_allclose(result, np.zeros((3, 3)))

    @pytest.mark.prod
    def test_shape_mismatch_raises(self):
        """维度不匹配应报错"""
        with pytest.raises(ValueError):
            matrix_multiply(np.ones((2, 3)), np.ones((2, 3)))


class TestMatrixAdd:
    """矩阵加法 — 生产验证"""

    @pytest.mark.prod
    def test_add_square(self, random_matrix):
        a = random_matrix(4, 4)
        b = random_matrix(4, 4)
        result = matrix_add(a, b)
        np.testing.assert_allclose(result, a + b)

    @pytest.mark.prod
    def test_add_zero(self):
        a = np.array([[1.0, 2.0], [3.0, 4.0]])
        result = matrix_add(a, np.zeros_like(a))
        np.testing.assert_allclose(result, a)


class TestMatrixTranspose:
    """转置 — 生产验证"""

    @pytest.mark.prod
    def test_square_transpose(self, random_matrix):
        a = random_matrix(3, 3)
        result = matrix_transpose(a)
        np.testing.assert_allclose(result, a.T)

    @pytest.mark.prod
    def test_rect_transpose(self, random_matrix):
        a = random_matrix(2, 5)
        result = matrix_transpose(a)
        assert result.shape == (5, 2)
        np.testing.assert_allclose(result, a.T)


class TestMatrixTrace:
    """迹 — 生产验证"""

    @pytest.mark.prod
    def test_trace_square(self, random_matrix):
        a = random_matrix(3, 3)
        result = matrix_trace(a)
        np.testing.assert_allclose(result, np.trace(a))

    @pytest.mark.prod
    def test_trace_identity(self):
        result = matrix_trace(np.eye(5))
        assert result == pytest.approx(5.0)


class TestMatrixNorm:
    """范数 — 生产验证"""

    @pytest.mark.prod
    def test_frobenius(self, random_matrix):
        a = random_matrix(3, 4)
        result = matrix_norm(a, "fro")
        expected = np.linalg.norm(a, "fro")
        np.testing.assert_allclose(result, expected)

    @pytest.mark.prod
    def test_norm_zero(self):
        result = matrix_norm(np.zeros((3, 3)), "fro")
        assert result == 0.0

    @pytest.mark.prod
    def test_norm_positive(self, random_matrix):
        """范数非负"""
        a = random_matrix(5, 5)
        assert matrix_norm(a, "fro") >= 0
        assert matrix_norm(a, 2) >= 0


class TestElementwiseMultiply:
    """Hadamard 积 — 生产验证"""

    @pytest.mark.prod
    def test_elementwise(self, random_matrix):
        a = random_matrix(3, 3)
        b = random_matrix(3, 3)
        result = elementwise_multiply(a, b)
        np.testing.assert_allclose(result, a * b)

    @pytest.mark.prod
    def test_zero_element(self):
        a = np.array([[1.0, 2.0], [3.0, 4.0]])
        b = np.array([[0.0, 5.0], [6.0, 0.0]])
        result = elementwise_multiply(a, b)
        expected = np.array([[0.0, 10.0], [18.0, 0.0]])
        np.testing.assert_allclose(result, expected)


# ============================================================
# 研发环境扩展用例 (dev) — 额外覆盖
# ============================================================

class TestMatrixMultiplyDev:
    """矩阵乘法 — 研发扩展"""

    @pytest.mark.extended
    def test_large_matrix_performance(self, random_matrix):
        """大矩阵乘法 — 不应崩溃, 结果维度正确"""
        n = 200
        a = random_matrix(n, n)
        b = random_matrix(n, n)
        result = matrix_multiply(a, b)
        assert result.shape == (n, n)
        assert not np.any(np.isnan(result))

    @pytest.mark.extended
    def test_associativity(self, random_matrix):
        """(AB)C = A(BC)"""
        a = random_matrix(20, 15)
        b = random_matrix(15, 10)
        c = random_matrix(10, 5)
        left = matrix_multiply(matrix_multiply(a, b), c)
        right = matrix_multiply(a, matrix_multiply(b, c))
        np.testing.assert_allclose(left, right, rtol=1e-10)

    @pytest.mark.extended
    def test_distributivity(self, random_matrix):
        """A(B+C) = AB + AC"""
        a = random_matrix(15, 10)
        b = random_matrix(10, 8)
        c = random_matrix(10, 8)
        left = matrix_multiply(a, matrix_add(b, c))
        right = matrix_add(matrix_multiply(a, b), matrix_multiply(a, c))
        np.testing.assert_allclose(left, right, rtol=1e-10)

    @pytest.mark.extended
    def test_scalar_multiply(self):
        """标量矩阵乘法"""
        a = np.array([[1.0, 2.0], [3.0, 4.0]])
        result = matrix_multiply(3.0, a)
        expected = 3.0 * a
        np.testing.assert_allclose(result, expected)


class TestMatrixNormDev:
    """范数 — 研发扩展"""

    @pytest.mark.extended
    def test_all_norm_types(self, random_matrix):
        """验证多种范数类型"""
        a = random_matrix(4, 4)
        for ord_val in ["fro", 1, 2, np.inf]:
            result = matrix_norm(a, ord_val)
            expected = np.linalg.norm(a, ord=ord_val)
            np.testing.assert_allclose(result, expected, rtol=1e-10)

    @pytest.mark.extended
    @pytest.mark.parametrize("shape", [(1, 1), (10, 1), (1, 10), (50, 3)])
    def test_various_shapes(self, random_matrix, shape):
        """不规则矩阵的范数计算"""
        a = random_matrix(*shape)
        result = matrix_norm(a)
        assert result >= 0
