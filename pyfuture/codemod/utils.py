from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

import libcst as cst
from libcst.codemod import Codemod


class RuleSet(Enum):
    # python 3.10+
    pep604 = "pep604"
    pep622 = "pep622"
    # python 3.12+
    pep695 = "pep695"


def get_transformers(rule_sets: list[RuleSet] | RuleSet) -> Iterable[type[Codemod]]:
    """
    Get codemod transformers for specified rule set.
    """
    from .pep604 import TransformUnionTypesCommand
    from .pep622 import TransformMatchCommand
    from .pep695 import TransformTypeParametersCommand

    if not isinstance(rule_sets, list):
        rule_sets = [rule_sets]

    for rule_set in rule_sets:
        match rule_set:
            case RuleSet.pep604:
                yield TransformUnionTypesCommand
            case RuleSet.pep622:
                yield TransformMatchCommand
            case RuleSet.pep695:
                yield TransformTypeParametersCommand
            case _:
                raise ValueError(f"Unknown rule set: {rule_set}")


def transform_union(op: cst.BinaryOperation) -> cst.Subscript | None:
    if not isinstance(op.operator, cst.BitOr):
        return None
    if isinstance((left := op.left), cst.BinaryOperation):
        left = transform_union(left) or left
    if isinstance((right := op.right), cst.BinaryOperation):
        right = transform_union(right) or right
    slices = [
        cst.SubscriptElement(
            slice=cst.Index(value=left),
        ),
        cst.SubscriptElement(
            slice=cst.Index(value=right),
        ),
    ]
    return cst.Subscript(
        value=cst.Name(
            value="Union",
            lpar=[],
            rpar=[],
        ),
        slice=slices,
    )


def gen_type_param(
    type_param: cst.TypeVar | cst.TypeVarTuple | cst.ParamSpec, type_name: cst.Name | None = None
) -> cst.SimpleStatementLine:
    """
    To generate the following code:
        T = cst.TypeVar("T")
        P = cst.ParamSpec("P")
        Ts = cst.TypeVarTuple("Ts")
    """
    type_name = type_param.name if type_name is None else type_name
    match type_param:
        case cst.TypeVar(_, bound):
            args = [
                cst.Arg(cst.SimpleString(f'"{type_name.value}"')),
            ]
            if bound is not None:
                if isinstance(bound, cst.BinaryOperation):
                    bound = transform_union(bound) or bound
                args.append(cst.Arg(bound, keyword=cst.Name("bound")))
            return cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(type_name)],
                        value=cst.Call(
                            func=cst.Name("TypeVar"),
                            args=args,
                        ),
                    )
                ]
            )
        case _:  # cst.TypeVarTuple | cst.ParamSpec
            return cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(type_name)],
                        value=cst.Call(
                            func=cst.Name(type_param.__class__.__name__),
                            args=[
                                cst.Arg(cst.SimpleString(f'"{type_name.value}"')),
                            ],
                        ),
                    )
                ]
            )


def gen_func_wrapper(node: cst.FunctionDef, type_vars: list[cst.SimpleStatementLine]) -> cst.FunctionDef:
    wrapper = cst.FunctionDef(
        name=cst.Name(value=f"__wrapper_func_{node.name.value}"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(
            body=[
                *type_vars,
                node,
                cst.SimpleStatementLine(
                    [
                        cst.Return(
                            value=cst.Name(
                                value=node.name.value,
                                lpar=[],
                                rpar=[],
                            )
                        ),
                    ]
                ),
            ]
        ),
    )
    return wrapper
