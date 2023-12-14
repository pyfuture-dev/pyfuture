from __future__ import annotations

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
    """
    module = cst.parse_module(code)
    for transformer in transformers:
        module = transformer(CodemodContext()).transform_module(module)
    return module.code


def transfer_code(
    code: str,
    *,
    target: tuple[int, int] = (3, 8),
) -> str:
    """
    Transfer code to specified target version of python.
    """

    assert target[0] == 3, "Only support python3"
    transformers = []
    if target[1] < 12:
        transformers.extend(get_transformers(RuleSet.pep695))
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
    target: tuple[int, int] = (3, 8),
):
    """
    Transfer code from src_file and write to tgt_file.
    """
    with src_file.open("r") as f:
        code = f.read()

    tgt_file.parent.mkdir(parents=True, exist_ok=True)
    with tgt_file.open("w") as f:
        f.write(transfer_code(code, target=target))
