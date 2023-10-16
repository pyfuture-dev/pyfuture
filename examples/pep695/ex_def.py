import ast

mod = ast.parse("""
from typing import TypeAlias, TypeVar
def test[T](x: T) -> T:
    print(x)
    return x
""")

skip = 0
for index, node in enumerate(mod.body):
    if skip:
        skip = 0
        continue
    if isinstance(node, ast.FunctionDef):
        for type_param in node.type_params:
            assert isinstance(type_param, ast.TypeVar)
            # type_name = f"{node.name}_{type_param.name}"
            type_name = type_param.name
            mod.body.insert(index, ast.Assign(
                targets = [ast.Name(
                    id = type_name,
                    ctx = ast.Store(),
                )],
                value = ast.Call(func=ast.Name(id='TypeVar', ctx=ast.Load()), args=[
                    ast.Constant(value=type_name)
                ], keywords=[]),
                lineno = node.lineno,
            ))
            skip += 1
        node.type_params = []
        # print(node.type_params)
        # node.type_params = []
        # if node.returns:
        #     print(node.returns)
        #     node.returns = None
        # for arg in node.args.args:
        #     if isinstance(arg.annotation, ast.Name):
        #         print(arg.annotation.id)
        #         arg.annotation = None

print(ast.dump(mod))
# ast to code
print(ast.unparse(mod))
