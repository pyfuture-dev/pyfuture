from __future__ import annotations

from typing import Any

import libcst as cst
from libcst import (
    BaseStatement,
    ClassDef,
    FlattenSentinel,
    FunctionDef,
    RemovalSentinel,
)
from libcst.codemod import (
    CodemodContext,
    VisitorBasedCodemodCommand,
)
from libcst.metadata import FunctionScope, ScopeProvider

from ...transformer import ReplaceTransformer


def match_selector(left: cst.BaseExpression, case: cst.MatchCase):
    match case.pattern:
        case cst.MatchAs():
            """
                case _
            """
            if case.pattern.pattern is None and case.pattern.name is None:
                gen_if = cst.Else(body=case.body)
            elif case.pattern.name is not None:
                """
                case [x] as y
                """
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
            else:
                # TODO(gouzil): case [x] if x>0
                raise NotImplementedError()
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
            raise RuntimeError(f"no support type: {case.pattern}")
    return gen_if


def match_transform(
    left: cst.BaseExpression,
    case: cst.MatchCase,
    root_if: cst.If,
) -> cst.If | cst.Else:
    if root_if.orelse is None:
        return root_if.with_changes(orelse=match_selector(left, case))
    else:
        assert isinstance(root_if.orelse, cst.If)
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
    # TODO(gouzil): Need to support MatchOr first
    # match arg_list:
    #     case (
    #         [cst.SimpleString(), cst.SimpleString()]
    #         | [cst.Name(), cst.SimpleString()]
    #         | [cst.SimpleString(), cst.Name()]
    #         | [cst.Name(), cst.Integer()]
    #         | [cst.Integer(), cst.Name()]
    #     ):
    #         """
    #         demo:
    #             "test" == "test"
    #             "test" == 123
    #         """
    #         op = cst.Equal()
    #     case _:
    #         op = cst.Is()

    op = cst.Equal()
    return op


# TODO(gouzil): format
def replace_match_node(
    body_scope: FunctionScope,
    match_body: cst.Match,
    zero_case: cst.MatchCase,
    root_if: cst.If | None = None,
) -> FunctionDef:
    assert isinstance(body_scope.node, FunctionDef)
    new_body_code: list[cst.CSTNode] = list(body_scope.node.body.body)
    index: int = new_body_code.index(match_body)
    del new_body_code[index]
    if root_if is None:
        for body in zero_case.body.body:
            new_body_code.insert(index, body)
            index += 1
    else:
        new_body_code.insert(index, root_if)
    new_root_if = body_scope.node.body.with_changes(body=new_body_code)
    return body_scope.node.with_changes(body=new_root_if)


class TransformMatchCommand(VisitorBasedCodemodCommand):
    """
    Remove math from the node and replace it with a new function

    Example:
    >>> transformer = TransformMatchCommand(CodemodContext())

    >>> module = cst.parse_module(\"""
    ... class demo:
    ...     pass
    ... def test1():
    ...     test_class = demo()
    ...     match test_class:
    ...        case "123":
    ...            print(123)
    ...        case demo():
    ...            print("demo")
    ...        case _:
    ...            print("other")
    ... \""")
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    class demo:
        pass
    def test1():
        test_class = demo()
        if test_class == "123":
            print(123)
        elif isinstance(test_class, demo):
            print("demo")
        else:
            print("other")

    >>> module = cst.parse_module(\"""
    ... def test2():
    ...     test_value = "name"
    ...     match test_value:
    ...        case "123":
    ...            print(123)
    ...        case "name":
    ...            print("name")
    ...        case _:
    ...            print("other")
    ... \""")
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    def test2():
        test_value = "name"
        if test_value == "123":
            print(123)
        elif test_value == "name":
            print("name")
        else:
            print("other")

    >>> module = cst.parse_module(\"""
    ... def test3():
    ...     test_value = 123
    ...     match test_value:
    ...        case 123:
    ...            print(123)
    ...        case "name":
    ...            print("name")
    ...        case _:
    ...            print("other")
    ... \""")
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    def test3():
        test_value = 123
        if test_value == 123:
            print(123)
        elif test_value == "name":
            print("name")
        else:
            print("other")

    >>> module = cst.parse_module(\"""
    ... def test4():
    ...     test_value = 123
    ...     match test_value:
    ...         case _:
    ...             print("other")
    ... \""")
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    def test4():
        test_value = 123
        print("other")

    >>> module = cst.parse_module(\"""
    ... def test5():
    ...     test_value = 123
    ...     match test_value:
    ...         case [x] as y:
    ...             print("other")
    ... \""")
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    def test5():
        test_value = 123
        if test_value == y:
            print("other")
    """

    METADATA_DEPENDENCIES = (ScopeProvider,)

    def __init__(self, context: CodemodContext) -> None:
        self.node_to_body: dict[FunctionDef | ClassDef, Any] = {}
        super().__init__(context)

    def visit_FunctionDef(self, node: FunctionDef) -> bool | None:
        body_scope = self.get_metadata(ScopeProvider, node.body)
        assert isinstance(body_scope, FunctionScope)
        assert isinstance(body_scope.node, FunctionDef)
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
                root_if = match_selector(body.subject, zero_case)
                for cs in body.cases[1:]:
                    assert isinstance(root_if, cst.If)
                    root_if = match_transform(
                        body.subject,
                        cs,
                        root_if,
                    )

                assert isinstance(root_if, cst.If)
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
