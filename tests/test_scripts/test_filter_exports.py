"""AST 裁剪工具测试 — 验证物理隔离正确性"""

import os
import sys
import tempfile
import pytest

# 添加 scripts 目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
from filter_exports import prune_file, prune_from_manifest


# ============================================================
# fixtures
# ============================================================

@pytest.fixture
def sample_py_file():
    """创建包含多个函数和类的临时 Python 文件"""
    content = '''"""示例算法模块 — 含生产和实验接口"""

import numpy as np
from typing import List, Optional

# 全局常量
EPSILON = 1e-10
DEBUG = False


def public_api(data):
    """生产接口: 需要保留"""
    return _core_impl(data)


def _core_impl(data):
    """辅助函数: 被 public_api 调用, 自动保留"""
    return np.mean(data)


def experimental_feature(data):
    """实验功能: 不应保留"""
    return _experimental_helper(data) * DEBUG


def _experimental_helper(data):
    """实验辅助: 不应保留"""
    return np.std(data)


class Processor:
    """生产类: 需保留 (因为 public_method 可达)"""

    def public_method(self):
        return self._helper()

    def _helper(self):
        return 42

    def debug_dump(self):
        """不应保留: 未被可达链调用"""
        pass


class DebugTools:
    """调试类: 不应保留"""

    def analyze(self):
        pass
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        tmp_path = f.name
    yield tmp_path
    os.unlink(tmp_path)


@pytest.fixture
def polyfit_file():
    """指向实际的 polyfit/fitting.py 文件"""
    return os.path.join(
        os.path.dirname(__file__), "../../model/polyfit/fitting.py"
    )


# ============================================================
# 生产用例 (prod) — 核心裁剪逻辑
# ============================================================

class TestPruneFileBasic:
    """基本裁剪功能"""

    @pytest.mark.prod
    def test_public_api_kept(self, sample_py_file):
        """生产接口及其辅助函数被保留"""
        result = prune_file(sample_py_file, ["public_api"])
        assert "def public_api" in result
        assert "def _core_impl" in result  # 辅助函数自动保留

    @pytest.mark.prod
    def test_experimental_removed(self, sample_py_file):
        """实验接口物理删除 — 源码不存在"""
        result = prune_file(sample_py_file, ["public_api"])
        assert "def experimental_feature" not in result
        assert "def _experimental_helper" not in result

    @pytest.mark.prod
    def test_class_kept_when_method_exported(self, sample_py_file):
        """被导出方法所在的类整体保留"""
        result = prune_file(sample_py_file, ["public_api", "public_method"])
        assert "class Processor" in result

    @pytest.mark.prod
    def test_unused_class_removed(self, sample_py_file):
        """未被引用的类物理删除"""
        result = prune_file(sample_py_file, ["public_api"])
        assert "class DebugTools" not in result
        assert "class Processor" not in result  # 类方法未被导出

    @pytest.mark.prod
    def test_imports_trimmed(self, sample_py_file):
        """未使用的 import 被移除"""
        result = prune_file(sample_py_file, ["public_api"])
        # List 和 Optional 未使用, 应被移除
        assert "List" not in result
        assert "Optional" not in result
        # numpy 被使用, 应保留
        assert "numpy" in result or "import numpy" in result

    @pytest.mark.prod
    def test_global_constants_removed(self, sample_py_file):
        """未使用的全局常量被删除"""
        result = prune_file(sample_py_file, ["public_api"])
        assert "DEBUG" not in result
        # EPSILON 未被导出函数引用, 也应删除
        assert "EPSILON" not in result

    @pytest.mark.prod
    def test_empty_exports(self, sample_py_file):
        """无有效 exports 时返回空文件提示"""
        result = prune_file(sample_py_file, ["nonexistent_func"])
        assert "无有效 exports" in result

    @pytest.mark.prod
    def test_docstring_kept(self, sample_py_file):
        """模块文档字符串保留"""
        result = prune_file(sample_py_file, ["public_api"])
        assert "示例算法模块" in result


class TestPhysicalIsolation:
    """物理隔离验证"""

    @pytest.mark.prod
    def test_no_comment_stubs(self, sample_py_file):
        """裁剪不是注释 — 源码物理上不存在"""
        result = prune_file(sample_py_file, ["public_api"])
        # 不应该出现被裁剪的函数名 (即使是注释形式)
        assert "experimental_feature" not in result
        assert "experimental_helper" not in result

    @pytest.mark.prod
    def test_output_is_valid_python_syntax(self, sample_py_file):
        """裁剪后代码仍是合法 Python"""
        result = prune_file(sample_py_file, ["public_api"])
        import ast
        try:
            ast.parse(result)
        except SyntaxError as e:
            pytest.fail(f"裁剪后代码有语法错误: {e}")

    @pytest.mark.prod
    def test_output_is_executable(self, sample_py_file):
        """裁剪后代码可执行 (import 不报错)"""
        result = prune_file(sample_py_file, ["public_api"])
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write(result)
            tmp = f.name
        try:
            # 尝试编译
            compile(result, tmp, "exec")
        finally:
            os.unlink(tmp)


class TestRealFile:
    """真实算法文件裁剪"""

    @pytest.mark.prod
    def test_polyfit_pruning(self, polyfit_file):
        """对 polyfit/fitting.py 裁剪, 验证加权拟合被移除"""
        result = prune_file(polyfit_file, ["polyfit_ls", "polyval", "r2_score"])
        assert "def polyfit_ls" in result
        assert "def polyval" in result
        assert "def r2_score" in result
        # 加权拟合不应保留
        assert "def weighted_polyfit" not in result

    @pytest.mark.prod
    def test_polyfit_helper_retained(self, polyfit_file):
        """poly_residual 被 r2_score 调用, 应自动保留"""
        result = prune_file(polyfit_file, ["r2_score"])
        assert "def poly_residual" in result  # r2_score 依赖它


# ============================================================
# 研发扩展用例 (extended)
# ============================================================

class TestPruneFileExtended:
    @pytest.mark.extended
    def test_multi_export_chain(self, sample_py_file):
        """多个 exports 的合并可达链"""
        result = prune_file(
            sample_py_file, ["public_api", "experimental_feature"]
        )
        # 两者都应保留
        assert "def public_api" in result
        assert "def experimental_feature" in result
        # 两者的辅助函数都应保留
        assert "def _core_impl" in result
        assert "def _experimental_helper" in result

    @pytest.mark.extended
    def test_class_export(self, sample_py_file):
        """导出整个类时保留类所有方法"""
        result = prune_file(sample_py_file, ["Processor"])
        assert "class Processor" in result
        assert "def public_method" in result
        assert "def _helper" in result

    @pytest.mark.extended
    def test_line_count_reduced(self, polyfit_file):
        """验证行数确实减少"""
        original_lines = len(open(polyfit_file).readlines())
        result = prune_file(
            polyfit_file, ["polyfit_ls", "polyval", "r2_score"]
        )
        pruned_lines = len(result.splitlines())
        assert pruned_lines < original_lines
        print(f"  行数: {original_lines} → {pruned_lines}")

    @pytest.mark.extended
    def test_manifest_batch(self, polyfit_file, tmp_path):
        """批量模式：从 MANIFEST.yaml 批量裁剪"""
        import shutil, yaml
        # 文件拷贝到 tmp_path, 路径对齐: fitting.py 放在根下
        dest = tmp_path / "fitting.py"
        shutil.copy(polyfit_file, dest)

        # 在 tmp_path 下创建 MANIFEST.yaml (确保相对路径解析正确)
        manifest_content = {
            "version": 2,
            "target": "machine",
            "api_filter": [
                {"file": "fitting.py", "exports": ["polyfit_ls", "polyval"]}
            ]
        }
        manifest_in_tmp = tmp_path / "MANIFEST.yaml"
        with open(manifest_in_tmp, 'w') as f:
            yaml.dump(manifest_content, f)

        out_dir = tmp_path / "output"
        out_dir.mkdir()
        results = prune_from_manifest(
            str(manifest_in_tmp), str(out_dir), verbose=False
        )
        assert "fitting.py" in results
        orig, kept, pruned = results["fitting.py"]
        assert pruned > 0
        # 验证输出文件存在
        output_file = out_dir / "fitting.py"
        assert output_file.exists()
        content = output_file.read_text()
        assert "def polyfit_ls" in content
        assert "def polyval" in content
        assert "def polyval" in content
        assert "def weighted_polyfit" not in content
