from __future__ import annotations

from typing import Any

import libcst as cst
from libcst import (
    Arg,
    ClassDef,
    FunctionDef,
    Index,
    Name,
    SimpleStatementLine,
    Subscript,
    SubscriptElement,
)
from libcst.codemod import (
    CodemodContext,
    VisitorBasedCodemodCommand,
)
from libcst.codemod.visitors import AddImportsVisitor
from libcst.metadata import ScopeProvider

from ..utils import gen_type_param


class TransformFStringCommand(VisitorBasedCodemodCommand):
    """
    Remove f-string from node, and return a new node with the formatted string.

    Example:
    >>> transformer = TransformFStringCommand(CodemodContext())
    >>> module = cst.parse_module(\"""
    ... name = "world"
    ... x = f"hello {name}"
    ... y = f"hello {"world"}"
    ... \"""
    ... )
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    name = "world"
    x = "hello {:}".format(name)
    y = "hello {:}".format("world")
    >>> module = cst.parse_module(\"""
    ... result = 3.1415926
    ... x = f"result: {result:.2f}"
    ... y = f"result: {3.1415926:.2f}"
    ... \"""
    ... )
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    result = 3.1415926
    x = "result: {:.2f}".format(result)
    y = "result: {:.2f}".format(3.1415926)
    """

    METADATA_DEPENDENCIES = (ScopeProvider,)

    def __init__(self, context: CodemodContext) -> None:
        self.node_to_wrapper: dict[FunctionDef | ClassDef, Any] = {}
        super().__init__(context)

    def remove_type_parameters[T: FunctionDef | ClassDef](
        self, node: T, prefix: str = "", suffix: str = ""
    ) -> tuple[list[SimpleStatementLine], T]:
        type_params = node.type_parameters
        if type_params is None:
            return [], node
        statements = []
        new_node = node.with_changes(type_parameters=None)

        slices = []
        for type_param in type_params.params:
            new_name = type_param.param.name.with_changes(value=f"{prefix}{type_param.param.name.value}{suffix}")

            AddImportsVisitor.add_needed_import(self.context, "typing", type_param.param.__class__.__name__)
            statements.append(gen_type_param(type_param.param, new_name))
            slices.append(
                SubscriptElement(
                    slice=Index(value=new_name),
                ),
            )

        if isinstance(new_node, ClassDef) and slices:
            AddImportsVisitor.add_needed_import(self.context, "typing", "Generic")
            generic_base = Arg(
                value=Subscript(
                    value=Name(
                        value="Generic",
                        lpar=[],
                        rpar=[],
                    ),
                    slice=slices,
                )
            )
            new_node = new_node.with_changes(bases=[*new_node.bases, generic_base])

        return statements, new_node

    def leave_FormattedString(self, original_node: cst.FormattedString, updated_node: cst.FormattedString):
        expressions = []
        string = ""
        start = updated_node.start.strip("f")
        end = updated_node.end

        for node in updated_node.parts:
            if isinstance(node, cst.FormattedStringExpression):
                expressions.append(node.expression)
                format_spec_str = ""
                if (format_spec := node.format_spec) is not None:
                    for format_spec_node in format_spec:
                        if isinstance(format_spec_node, cst.FormattedStringText):
                            format_spec_str += format_spec_node.value
                        else:
                            raise NotImplementedError(f"Unknown node type: {format_spec_node}")
                string += f"{{:{format_spec_str}}}"
            elif isinstance(node, cst.FormattedStringText):
                string += node.value
            else:
                raise NotImplementedError(f"Unknown node type: {node}")
        return cst.Call(
            func=cst.Attribute(
                value=cst.SimpleString(value=f"{start}{string}{end}"),
                attr=cst.Name(value="format"),
            ),
            args=[cst.Arg(value=expression) for expression in expressions],
        )
