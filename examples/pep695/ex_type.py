import ast


mod = ast.parse("""
from typing import Callable, Hashable, Sequence, TypeVar, TypeVarTuple, TypeAlias

type FloatPoint = tuple[float, float]
# type Point[T] = tuple[T, T]
# type IntFunc[**P] = Callable[P, int]  # ParamSpec
# type LabeledTuple[*Ts] = tuple[str, *Ts]  # TypeVarTuple
# type HashableSequence[T: Hashable] = Sequence[T]  # TypeVar with bound
# type IntOrStrSequence[T: (int, str)] = Sequence[T]  # TypeVar with constraints
""")
print(ast.dump(mod))
for index, node in enumerate(mod.body):
    if isinstance(node, ast.TypeAlias):
        mod.body[index] = ast.AnnAssign(
            target = node.name,
            annotation = ast.Name(id="TypeAlias", ctx=ast.Load()),
            value = node.value,
            simple = 1,
        )
        print(node.name.id)

print(ast.dump(mod))
# ast to code
print(ast.unparse(mod))
exec(ast.unparse(mod))
