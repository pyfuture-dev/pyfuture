from __future__ import annotations

from typing import Any

import libcst as cst
from libcst import (
    ClassDef,
    FunctionDef,
)
from libcst.codemod import (
    CodemodContext,
    VisitorBasedCodemodCommand,
)
from libcst.metadata import ScopeProvider


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
                        assert isinstance(format_spec_node, cst.FormattedStringText), f"Unknown node type: {node}"
                        format_spec_str += format_spec_node.value
                string += f"{{:{format_spec_str}}}"
            else:
                assert isinstance(node, cst.FormattedStringText), f"Unknown node type: {node}"
                string += node.value
        return cst.Call(
            func=cst.Attribute(
                value=cst.SimpleString(value=f"{start}{string}{end}"),
                attr=cst.Name(value="format"),
            ),
            args=[cst.Arg(value=expression) for expression in expressions],
        )
