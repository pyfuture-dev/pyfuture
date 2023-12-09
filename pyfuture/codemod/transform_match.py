from __future__ import annotations

from typing import Any

import libcst as cst
from libcst import (
    BaseStatement,
    ClassDef,
    FunctionDef,
)
from libcst._flatten_sentinel import FlattenSentinel
from libcst._removal_sentinel import RemovalSentinel
from libcst.codemod import (
    CodemodContext,
    VisitorBasedCodemodCommand,
)
from libcst.metadata import Scope, ScopeProvider

from ..transformer import ReplaceTransformer


def match_transform(
    left: cst.CSTNode,
    case: cst.MatchCase,
    root_if: cst.If | None,
) -> cst.If | cst.Else | None:
    if root_if.orelse is None:
        match case.pattern:
            case cst.MatchAs():
                """
                    case _
                """
                if case.pattern.pattern is None and case.pattern.name is None:
                    gen_if = cst.Else(body=case.body)
                elif case.pattern.name is not None:
                    gen_if = cst.If(
                        test=cst.Comparison(
                            left=left,
                            comparisons=[
                                cst.ComparisonTarget(
                                    operator=match_op_selector([left, case.pattern.name]),
                                    comparator=case.pattern.name,
                                )
                            ],
                        ),
                        body=case.body,
                    )
                # TODO(gouzil): case [x] if x>0
            case cst.MatchClass():
                """
                class demo:
                    pass

                case demo():
                    pass
                """
                gen_if = cst.If(
                    test=cst.Call(
                        func=cst.Name(value="isinstance"),
                        args=[
                            cst.Arg(value=left),
                            cst.Arg(value=case.pattern.cls),
                        ],
                    ),
                    body=case.body,
                )
            case cst.MatchValue():
                """
                case "test":
                """
                gen_if = cst.If(
                    test=cst.Comparison(
                        left=left,
                        comparisons=[
                            cst.ComparisonTarget(
                                operator=match_op_selector([left, case.pattern.value]),
                                comparator=case.pattern.value,
                            )
                        ],
                    ),
                    body=case.body,
                )
            case _:
                RuntimeError(f"no support type: {case.pattern}")
        return root_if.with_changes(orelse=gen_if)
    else:
        return root_if.with_changes(
            orelse=match_transform(
                left=left,
                case=case,
                root_if=root_if.orelse,
            )
        )


def match_op_selector(arg_list: list[Any]):
    assert len(arg_list) == 2
    # left: cst.CSTNode,node: cst.CSTNode
    match arg_list:
        case (
            [cst.SimpleString(), cst.SimpleString()]
            | [cst.Name(), cst.SimpleString()]
            | [cst.SimpleString(), cst.Name()]
            | [cst.Name(), cst.Integer()]
            | [cst.Integer(), cst.Name()]
        ):
            """
            demo:
                "test" == "test"
                "test" == 123
            """
            op = cst.Equal()
        case _:
            op = cst.Is()

    return op


def replace_func_body(node: FunctionDef, new_body: FunctionDef) -> FunctionDef:
    body = cst.FunctionDef(
        name=node.name,
        params=node.params,
        decorators=node.decorators,
        body=node.body,
    )
    return body


# TODO(gouzil): format
def replace_match_node(
    body_scope: Scope,
    match_body,
    zero_case,
    root_if: cst.If | None = None,
) -> FunctionDef:
    new_body_code = list(body_scope.node.body.body)
    new_body_code.remove(match_body)
    if root_if is None:
        for body in zero_case.body.body:
            new_body_code.append(body)
    else:
        new_body_code.append(root_if)
    root_if = body_scope.node.body.with_changes(body=new_body_code)
    return body_scope.node.with_changes(body=root_if)


class TransformMatchCommand(VisitorBasedCodemodCommand):
    METADATA_DEPENDENCIES = (ScopeProvider,)

    def __init__(self, context: CodemodContext) -> None:
        self.node_to_body: dict[FunctionDef | ClassDef, Any] = {}
        super().__init__(context)

    def visit_FunctionDef(self, node: FunctionDef) -> bool | None:
        body_scope = self.get_metadata(ScopeProvider, node.body)
        assert isinstance(body_scope, Scope)
        replacemences = {}
        for body in body_scope.node.body.body:
            if not isinstance(body, cst.Match):
                continue
            zero_case: cst.MatchCase = body.cases[0]
            if (
                len(body.cases) == 1
                and isinstance(zero_case.pattern, cst.MatchAs)
                and zero_case.pattern.pattern is None
            ):
                # replace match
                replacemences[node] = replace_match_node(
                    body_scope,
                    body,
                    zero_case,
                    None,
                )
            else:
                root_if = cst.If(
                    test=cst.Comparison(
                        left=body.subject,
                        comparisons=[
                            cst.ComparisonTarget(
                                operator=match_op_selector([body.subject, zero_case.pattern.value]),
                                comparator=zero_case.pattern.value,
                            )
                        ],
                    ),
                    body=zero_case.body,
                )
                for cs in body.cases[1:]:
                    root_if = match_transform(
                        body.subject,
                        cs,
                        root_if,
                    )

                # replace match
                replacemences[node] = replace_match_node(
                    body_scope,
                    body,
                    zero_case,
                    root_if,
                )

        new_node = node.visit(ReplaceTransformer(replacemences))

        assert isinstance(new_node, FunctionDef)

        self.node_to_body[node] = new_node

        return False

    def leave_FunctionDef(
        self, original_node: FunctionDef, updated_node: FunctionDef
    ) -> BaseStatement | FlattenSentinel[BaseStatement] | RemovalSentinel:
        body = self.node_to_body.get(original_node, None)
        if body is None:
            return updated_node

        return FlattenSentinel([body])
