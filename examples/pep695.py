from ast import FunctionDef, TypeAlias, Assign, type_param, fix_missing_locations
import ast
from typing import Any

def gen_type_params(type_params: list[type_param]) -> list[Assign]:
    assigns = []
    for type_param in type_params:
        match type_param:
            case ast.TypeVar(name, bound):
                # type_name = f"{node.name}_{name}"
                type_name = name
                assigns.append(ast.Assign(
                    targets = [ast.Name(
                        id = type_name,
                        ctx = ast.Store(),
                    )],
                    value = ast.Call(func=ast.Name(id='TypeVar', ctx=ast.Load()), args=[
                        ast.Constant(value=type_name)
                    ], keywords=[])
                ))
            case ast.TypeVarTuple(name):
                type_name = name
                assigns.append(ast.Assign(
                    targets = [ast.Name(
                        id = type_name,
                        ctx = ast.Store(),
                    )],
                    value = ast.Call(func=ast.Name(id='TypeVarTuple', ctx=ast.Load()), args=[
                        ast.Constant(value=type_name)
                    ], keywords=[])
                ))
            case ast.ParamSpec(name):
                type_name = name
                assigns.append(ast.Assign(
                    targets = [ast.Name(
                        id = type_name,
                        ctx = ast.Store(),
                    )],
                    value = ast.Call(func=ast.Name(id='ParamSpec', ctx=ast.Load()), args=[
                        ast.Constant(value=type_name)
                    ], keywords=[])
                ))

            case _:
                raise TypeError(f"Unsupported type param: {type_param}")

    return assigns




class Transformer(ast.NodeTransformer):
    def visit_TypeAlias(self, node: TypeAlias) -> Any:
        print(ast.dump(node))
        type_vars = gen_type_params(node.type_params)
        new_node = ast.AnnAssign(
            target = node.name,
            annotation = ast.Name(id="TypeAlias", ctx=ast.Load()),
            value = node.value,
            simple = 1,
        )
        return [*type_vars, new_node]
    
    def visit_FunctionDef(self, node: FunctionDef):
        type_vars = gen_type_params(node.type_params)
        node.type_params = []
        return [*type_vars, node]
    


mod = ast.parse("""
from typing import TypeAlias, TypeVar, ParamSpec, TypeVarTuple, TypeAlias
from typing import Callable, Hashable, Sequence

type FloatPoint = tuple[float, float]
type Point[T] = tuple[T, T]
type IntFunc[**P] = Callable[P, int]  # ParamSpec
type LabeledTuple[*Ts] = tuple[str, *Ts]  # TypeVarTuple
# type HashableSequence[T: Hashable] = Sequence[T]  # TypeVar with bound
# type IntOrStrSequence[T: (int, str)] = Sequence[T]  # TypeVar with constraints

def test[T](x: T) -> T:
    print(x)
    return x
""")

transformed_mod = fix_missing_locations(Transformer().visit(mod))
print(ast.unparse(transformed_mod))
exec(ast.unparse(transformed_mod))
