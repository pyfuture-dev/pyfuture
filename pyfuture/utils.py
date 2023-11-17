from libcst.codemod import CodemodContext, Codemod
from loguru import logger
import libcst as cst


def transform_code(
    transformers: list[Codemod],
    code: str,
) -> str:
    module = cst.parse_module(code)
    for transformer in transformers:
        module = transformer.transform_module(module)
    return module.code


def transfer_to(
    code: str,
    *,
    target: str|None = None,
) -> str | None:
    from .codemod import TransformTypeParametersCommand
    new_code = transform_code(
        transformers=[
            TransformTypeParametersCommand(CodemodContext()),
            # TODO: Add more codemods here
        ],
        code=code,
    )
    return new_code
