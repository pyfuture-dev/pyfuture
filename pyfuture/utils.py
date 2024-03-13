from __future__ import annotations

import contextlib
import io
from pathlib import Path

import libcst as cst
from libcst.codemod import Codemod, CodemodContext

from .codemod.utils import RuleSet, get_transformers


def apply_transformer(
    transformers: list[type[Codemod]],
    code: str,
) -> str:
    """
    Transform code with some transformers, and return the transformed code.

    Example:
    >>> code = "def test[T](x: T) -> T: return x"
    >>> new_code = apply_transformer(
    ...     transformers=get_transformers([RuleSet.pep695]),
    ...     code=code,
    ... )
    >>> print(new_code)
    from typing import TypeVar
    def __wrapper_func_test():
        __test_T = TypeVar("__test_T")
        def test(x: __test_T) -> __test_T:
            return x
        return test
    test = __wrapper_func_test()
    """
    with contextlib.redirect_stdout(io.StringIO()):
        module = cst.parse_module(code)
        # while True:
        for transformer in transformers:
            module = transformer(CodemodContext()).transform_module(module)
            # if code == module.code:
            #     break
    return module.code


def transfer_code(
    code: str,
    *,
    target: tuple[int, int] = (3, 9),
) -> str:
    """
    Transfer code to specified target version of python.

    Example:
    >>> code = "def test[T](x: T) -> T: return x"
    >>> new_code = transfer_code(code, target=(3, 9))
    >>> print(new_code)
    from typing import TypeVar
    def __wrapper_func_test():
        __test_T = TypeVar("__test_T")
        def test(x: __test_T) -> __test_T:
            return x
        return test
    test = __wrapper_func_test()
    """

    assert target[0] == 3, "Only support python3"
    transformers = []
    if target[1] < 12:
        transformers.extend(get_transformers([RuleSet.pep695, RuleSet.pep701]))
    if target[1] < 10:
        transformers.extend(get_transformers([RuleSet.pep622, RuleSet.pep604]))
    new_code = apply_transformer(
        transformers=transformers,
        code=code,
    )
    return new_code


def transfer_file(
    src_file: Path,
    tgt_file: Path,
    *,
    target: tuple[int, int] = (3, 9),
):
    """
    Transfer code from src_file and write to tgt_file.
    """
    with src_file.open("r") as f:
        code = f.read()

    tgt_file.parent.mkdir(parents=True, exist_ok=True)
    with tgt_file.open("w") as f:
        f.write(transfer_code(code, target=target))
