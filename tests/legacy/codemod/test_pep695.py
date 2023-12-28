from __future__ import annotations

import libcst as cst
import pytest
from libcst.codemod import CodemodContext

from pyfuture.codemod import TransformTypeParametersCommand


def print_string(s: str):
    cc = s.split("\n")
    for c in cc[:-1]:
        print(f"\"{c.replace("\"", "\\\"")}\\n\"")
    print(f"\"{cc[-1].replace("\"", "\\\"")}\"")


@pytest.mark.parametrize(
    ("src", "expected"),
    (
        pytest.param(
            "def test(x: int) -> int:\n" "    return x",
            "def test(x: int) -> int:\n" "    return x",
            id="no generic function",
        ),
        pytest.param(
            "def test[T: int](x: T) -> T:\n" "    return x",
            "from typing import TypeVar\n"
            "\n"
            "def __wrapper_func_test():\n"
            '    __test_T = TypeVar("__test_T", bound = int)\n'
            "    def test(x: __test_T) -> __test_T:\n"
            "        return x\n"
            "    return test\n"
            "test = __wrapper_func_test()",
            id="single bound function",
        ),
        pytest.param(
            "def test[T: int | str](x: T) -> T:\n" "    return x",
            "from typing import TypeVar\n\n"
            "def __wrapper_func_test():\n"
            '    __test_T = TypeVar("__test_T", bound = Union[int, str])\n'
            "    def test(x: __test_T) -> __test_T:\n"
            "        return x\n"
            "    return test\n"
            "test = __wrapper_func_test()",
            id="union bonud function",
        ),
    ),
)
def test_type_parameters(src: str, expected: str):
    module = cst.parse_module(src)
    new_module = TransformTypeParametersCommand(CodemodContext()).transform_module(module)
    print_string(new_module.code)
    assert new_module.code == expected
