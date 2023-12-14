from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.codemod import Codemod, CodemodContext


def transform_code(
    transformers: list[Codemod],
    code: str,
) -> str:
    """
    Transform code with some transformers, and return the transformed code.
    """
    module = cst.parse_module(code)
    for transformer in transformers:
        module = transformer.transform_module(module)
    return module.code


def transfer_code(
    code: str,
    *,
    target: tuple[int, int] = (3, 8),
) -> str:
    """
    Transfer code to specified target version of python.
    """
    from .codemod import TransformMatchCommand, TransformTypeParametersCommand

    assert target[0] == 3, "Only support python3"
    transformers = []
    if target[1] < 12:
        transformers.extend(
            [
                TransformTypeParametersCommand(CodemodContext()),
            ]
        )
    if target[1] < 10:
        transformers.extend(
            [
                TransformMatchCommand(CodemodContext()),
            ]
        )
    # TODO: Add more codemods here
    new_code = transform_code(
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
