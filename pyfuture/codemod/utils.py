from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

import libcst as cst
from libcst.codemod import Codemod


class RuleSet(Enum):
    # python 3.10+
    pep604 = "pep604"  # optional
    pep622 = "pep622"
    # python 3.12+
    pep695 = "pep695"
    pep701 = "pep701"


def get_transformers(rule_sets: list[RuleSet] | RuleSet) -> Iterable[type[Codemod]]:
    """
    Get codemod transformers for specified rule set.

    Example:
    >>> transformers = get_transformers([RuleSet.pep604, RuleSet.pep622])
    >>> print([transformer.__name__ for transformer in transformers])
    ['TransformUnionTypesCommand', 'TransformMatchCommand']
    """
    from .pep604 import TransformUnionTypesCommand
    from .pep622 import TransformMatchCommand
    from .pep695 import TransformTypeParametersCommand
    from .pep701 import TransformFStringCommand

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
            case RuleSet.pep701:
                yield TransformFStringCommand
            case _:  # pragma: no cover
                raise ValueError(f"Unknown rule set: {rule_set}")


def transform_bit_or(op: cst.BinaryOperation, use_union: bool = True) -> cst.Subscript | cst.Tuple | None:
    """
    To transform bit or operation to union type.

    Example:
    >>> module = cst.parse_module(\"""
    ... a + b
    ... \""")
    >>> node = module.body[0].body[0].value
    >>> transform_bit_or(node)
    None
    >>> module = cst.parse_module(\"""
    ... a | b | (c | d)
    ... \""")
    >>> node = module.body[0].body[0].value
    >>> print(cst.Module([transform_bit_or(node)]).code)
    Union[a, b, c, d]
    >>> print(cst.Module([transform_bit_or(node, use_union=False)]).code)
    (a, b, c, d)
    """
    if not isinstance(op.operator, cst.BitOr):
        return None

    def _split_bit_or(_op: cst.BinaryOperation) -> list[cst.BaseExpression]:
        _out = []
        if isinstance((left := _op.left), cst.BinaryOperation) and isinstance(left.operator, cst.BitOr):
            _out.extend(_split_bit_or(left))
        else:
            _out.append(left)
        if isinstance((right := _op.right), cst.BinaryOperation):
            _out.extend(_split_bit_or(right))
        else:
            _out.append(right)
        return _out

    items = _split_bit_or(op)
    if not use_union:
        return cst.Tuple(elements=[cst.Element(item) for item in items])
    slices = [
        cst.SubscriptElement(
            slice=cst.Index(value=item),
        )
        for item in items
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
    To generate type parameter definition statement.

    Example:
    >>> type_param = cst.TypeVar(cst.Name("T"))
    >>> print(cst.Module([gen_type_param(type_param)]).code)
    T = TypeVar("T")
    >>> type_param = cst.TypeVarTuple(cst.Name("Ts"))
    >>> print(cst.Module([gen_type_param(type_param)]).code)
    Ts = TypeVarTuple("Ts")
    >>> type_param = cst.ParamSpec(cst.Name("P"))
    >>> print(cst.Module([gen_type_param(type_param)]).code)
    P = ParamSpec("P")
    """
    type_name = type_param.name if type_name is None else type_name

    match type_param:
        case cst.TypeVar(_, bound):
            args = [
                cst.Arg(cst.SimpleString(f'"{type_name.value}"')),
            ]
            if bound is not None:
                if isinstance(bound, cst.BinaryOperation):
                    bound = transform_bit_or(bound) or bound
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
    """
    To generate a wrapper function for the specified function definition.

    Example:
    >>> module = cst.parse_module(\"""
    ... def test(x: int) -> int:
    ...     return x
    ... \""")
    >>> node = module.body[0]
    >>> print(cst.Module([gen_func_wrapper(node, [])]).code)
    def __wrapper_func_test():
        def test(x: int) -> int:
            return x
        return test
    """
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
