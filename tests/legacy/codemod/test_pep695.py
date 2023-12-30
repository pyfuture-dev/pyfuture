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
            id="function",
        ),
        pytest.param(
            "class Test: pass",
            "class Test: pass",
            id="class",
        ),
    ),
)
def test_no_generic(src: str, expected: str):
    module = cst.parse_module(src)
    new_module = TransformTypeParametersCommand(CodemodContext()).transform_module(module)
    print_string(new_module.code)
    assert new_module.code == expected
