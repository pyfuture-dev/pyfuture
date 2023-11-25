import libcst as cst
from libcst._flatten_sentinel import FlattenSentinel
from libcst._removal_sentinel import RemovalSentinel
from libcst.codemod import (
    CodemodContext,
    VisitorBasedCodemodCommand,
)
from libcst.metadata import ScopeProvider, Scope
from libcst import (
    BaseStatement,
    FunctionDef,
    ClassDef,
)
from typing import Any


class ReplaceNodes(cst.CSTTransformer):
    def __init__(self, replacements: dict[cst.CSTNode, cst.CSTNode]):
        self.replacements: dict[cst.CSTNode, cst.CSTNode] = replacements

    def on_leave(self, original_node: cst.CSTNode, updated_node: cst.CSTNode):
        return self.replacements.get(original_node, updated_node)


def match_transform(left: cst.CSTNode, case: cst.MatchCase, root_if: cst.If) -> cst.If:
    breakpoint()
    match case.pattern:
        case cst.MatchAs():
            """
                case _
            """
            if case.pattern.pattern is None:
                root_if = root_if.with_changes(
                    orelse=cst.Else(body=case.body),
                )
            # TODO(gouzil): case [x] if x>0
            # root_if = root_if.with_changes(
            #     orelse=cst.If(
            #         test=cst.Comparison(
            #             left=left,
            #             comparisons=[
            #                 cst.ComparisonTarget(
            #                     operator=match_op_selector([left, case.pattern]),
            #                     comparator=case.pattern.pattern,
            #                 )
            #             ],
            #         ),
            #         body=,
            #     )
            # )
        case cst.MatchClass():
            pass
        case cst.MatchKeywordElement:
            pass
        case cst.MatchList:
            pass
        case cst.MatchMapping:
            pass
        case cst.MatchMappingElement:
            pass
        case cst.MatchOr:
            pass
        case cst.MatchOrElement:
            pass
        case cst.MatchPattern:
            pass
        case cst.MatchSequence:
            pass
        case cst.MatchSequenceElement:
            pass
        case cst.MatchSingleton:
            pass
        case cst.MatchStar:
            pass
        case cst.MatchTuple:
            pass
        case cst.MatchValue:
            # cst.If
            pass
        case _:
            RuntimeError(f"no support type: {case.pattern}")
    return root_if


def match_op_selector(arg_list: list[Any]):
    assert len(arg_list) == 2
    breakpoint()
    # left: cst.CSTNode,node: cst.CSTNode
    match arg_list:
        case (
            [cst.SimpleString(), cst.SimpleString()]
            | [cst.Name(), cst.SimpleString()]
            | [cst.SimpleString(), cst.Name()]
        ):
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
        for b in zero_case.body.body:
            new_body_code.append(b)
    else:
        new_body_code.append(root_if)
    root_if = body_scope.node.body.with_changes(body=new_body_code)
    return body_scope.node.with_changes(body=root_if)


class RemoveMatchCommand(VisitorBasedCodemodCommand):
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
                                operator=match_op_selector(
                                    [body.subject, zero_case.pattern.value]
                                ),
                                comparator=zero_case.pattern.value,
                            )
                        ],
                    ),
                    body=zero_case.body,
                )
                for cs in body.cases:
                    root_if: cst.If = match_transform(body.subject, cs, root_if)
                breakpoint()
                # replace match
                replacemences[node] = replace_match_node(
                    body_scope,
                    body,
                    zero_case,
                    root_if,
                )

        new_node = node.visit(ReplaceNodes(replacemences))

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


module = cst.parse_module(
    """

def test():
    i = "name"

    match i:
        case "test":
            print(i+"123")
        # case "test1":
        #     print(i+"123")
        # case i:
        #     print(i)
        case _:
            print(111)
            print(222)

test()
"""
)

# print(module)
wrapper = cst.MetadataWrapper(module)
# print(wrapper.module.code)
# exec(module.code)
modified_module = wrapper.visit(RemoveMatchCommand(CodemodContext()))
print(modified_module.code)
# exec(modified_module.code)
