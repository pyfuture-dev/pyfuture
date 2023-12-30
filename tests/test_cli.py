from __future__ import annotations

import pytest
from typer.testing import CliRunner

from pyfuture.__main__ import app

runner = CliRunner()


@pytest.fixture
def code_dir(tmp_path):
    for i in range(5):
        file_path = tmp_path / f"example{i}.py"
        with open(file_path, "w") as f:
            f.write("def test[T](x: T) -> T: return x\n")
    return tmp_path


@pytest.fixture
def code_file(tmp_path):
    file_path = tmp_path / "example.py"
    with open(file_path, "w") as f:
        f.write("def test[T](x: T) -> T: return x\n")
    return file_path


def test_transfer(code_file):
    result = runner.invoke(app, ["transfer", str(code_file), str(code_file)])
    assert result.exit_code == 0
    assert result.stdout == ""
    assert code_file.read_text() == (
        "from typing import TypeVar\n"
        "\n"
        "def __wrapper_func_test():\n"
        '    __test_T = TypeVar("__test_T")\n'
        "    def test(x: __test_T) -> __test_T: return x\n"
        "    return test\n"
        "test = __wrapper_func_test()\n"
    )


def test_transfer_dir(code_dir):
    result = runner.invoke(app, ["transfer-dir", str(code_dir), str(code_dir)])
    assert result.exit_code == 0
    assert result.stdout == ""
    expected = (
        "from typing import TypeVar\n"
        "\n"
        "def __wrapper_func_test():\n"
        '    __test_T = TypeVar("__test_T")\n'
        "    def test(x: __test_T) -> __test_T: return x\n"
        "    return test\n"
        "test = __wrapper_func_test()\n"
    )
    for code_file in code_dir.iterdir():
        assert code_file.read_text() == expected
