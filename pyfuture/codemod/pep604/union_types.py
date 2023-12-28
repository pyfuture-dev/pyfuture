from __future__ import annotations

import libcst as cst
from libcst import matchers as m
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor
from libcst.metadata import ScopeProvider

from ..utils import transform_bit_or


class TransformUnionTypesCommand(VisitorBasedCodemodCommand):
    """
    Transform union types to typing.Union.

    Example:
    >>> transformer = TransformUnionTypesCommand(CodemodContext())
    >>> module = cst.parse_module(\"""
    ... def test(x: int | str) -> int | str:
    ...     return x
    ... \""")
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    from typing import Union
    def test(x: Union[int, str]) -> Union[int, str]:
        return x
    """

    METADATA_DEPENDENCIES = (ScopeProvider,)

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call):
        if not m.matches(original_node.func, m.Name("isinstance") | m.Name("issubclass")):
            return updated_node
        args = original_node.args

        if (
            isinstance(cls_info := args[1].value, cst.BinaryOperation)
            and (cls_info := transform_bit_or(cls_info)) is not None
        ):
            return updated_node.with_changes(
                args=[
                    args[0],
                    cst.Arg(cls_info),
                ]
            )

        return updated_node

    def leave_Annotation(self, original_node: cst.Annotation, updated_node: cst.Annotation):
        if (
            isinstance((op := original_node.annotation), cst.BinaryOperation)
            and (new_annotation := transform_bit_or(op)) is not None
        ):
            AddImportsVisitor.add_needed_import(self.context, "typing", "Union")
            return updated_node.with_changes(annotation=new_annotation)
        return updated_node
