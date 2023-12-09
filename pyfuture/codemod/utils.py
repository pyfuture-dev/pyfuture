from __future__ import annotations

import libcst as cst


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
