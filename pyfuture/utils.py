from libcst.codemod import CodemodContext, Codemod
import libcst as cst
from pathlib import Path


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
    from .codemod import TransformTypeParametersCommand
    assert target >= (3, 8), "Only support transfer to python 3.8+"
    new_code = code
    if target <= (3, 11):
        new_code = transform_code(
            transformers=[
                TransformTypeParametersCommand(CodemodContext()),
                # TODO: Add more codemods here
            ],
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
