from __future__ import annotations

import pytest
from typer.testing import CliRunner

from pyfuture.__main__ import app

runner = CliRunner()


@pytest.fixture
def code_file(tmp_path):
    file_path = tmp_path / "example.txt"
    with open(file_path, "w") as f:
        f.write("def test[T](x: T) -> T: return x\n")
    return file_path


def test_app(code_file):
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
