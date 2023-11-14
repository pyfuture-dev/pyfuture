import libcst as cst
from collections import defaultdict
from libcst import (
    CSTTransformer,
    TypeAlias,
    TypeParameters,
    TypeVar,
    AnnAssign,
    Annotation,
    Name,
    FunctionDef,
    Assign,
    TypeParameters,
    Parameters,
    Call,
    TypeVarTuple,
    ParamSpec,
    AssignTarget,
    Arg,
    SimpleStatementLine,
    Module,
    SimpleString,
    FlattenSentinel,
    RemovalSentinel,
    ClassDef,
    Subscript,
    SubscriptElement,
    Index
)
from libcst.codemod import (
    CodemodContext,
    gather_files,
    parallel_exec_transform_with_prettyprint,
    VisitorBasedCodemodCommand,
)
from libcst.codemod.visitors import AddImportsVisitor
from libcst import matchers
from libcst.metadata import MetadataWrapper, ScopeProvider, Assignment, Scope
from typing import Any

class ReplaceNodes(cst.CSTTransformer):
    def __init__(self, replacements: dict[cst.CSTNode, cst.CSTNode]):
        self.replacements = replacements

    def on_leave(self, original_node: cst.CSTNode, updated_node: cst.CSTNode):
        return self.replacements.get(original_node, updated_node)
    

def gen_type_param(type_param: TypeVar | TypeVarTuple | ParamSpec, type_name: Name|None=None) -> SimpleStatementLine:
    """
    To generate the following code:
        T = TypeVar("T")
        P = ParamSpec("P")
        Ts = TypeVarTuple("Ts")
    """
    type_name = type_param.name if type_name is None else type_name
    match type_param:
        case TypeVar(name, bound):
            args = [
                Arg(SimpleString(f'"{type_name.value}"')),
            ]
            if bound is not None:
                args.append(Arg(bound, keyword=Name("bound")))
            return SimpleStatementLine([Assign(
                targets=[AssignTarget(type_name)],
                value=Call(
                    func=Name("TypeVar"),
                    args=args,
                ),
            )])
        case TypeVarTuple(name)|ParamSpec(name):
            return SimpleStatementLine([Assign(
                targets=[AssignTarget(type_name)],
                value=Call(
                    func=Name(type_param.__class__.__name__),
                    args=[
                        Arg(SimpleString(f'"{type_name.value}"')),
                    ],
                ),
            )])
        case _:
            raise NotImplementedError


def remove_type_parameters[T: FunctionDef| ClassDef](node: T, prefix:str="", suffix:str="") -> tuple[list[SimpleStatementLine], T]:
    type_params = node.type_parameters
    if type_params is None:
        return [], node
    statements = []
    new_node = node.with_changes(
        type_parameters = None
    )

    slices = []
    for type_param in type_params.params:
        new_name = type_param.param.name.with_changes(value=f"{prefix}{type_param.param.name.value}{suffix}")
        statements.append(gen_type_param(type_param.param, new_name))
        slices.append(
                    SubscriptElement(
                        slice=Index(
                            value=new_name
                        ),
                    ),
                )
    
    if isinstance(new_node, ClassDef):
        generic_base = Arg(
            value= Subscript(
                value=Name(
                    value='Generic',
                    lpar=[],
                    rpar=[],
                ),
                slice=slices
        ))
        new_node = new_node.with_changes(
            bases = [*new_node.bases, generic_base]
        )

    return statements, new_node


def gen_func_wrapper(node: FunctionDef, type_vars: list[SimpleStatementLine]) -> FunctionDef:
    wrapper = cst.FunctionDef(
        name=Name(
            value=f'__wrapper_func_{node.name.value}'
        ),
        params=Parameters(),
        body=cst.IndentedBlock(
            body=[
                *type_vars,
                node,
                SimpleStatementLine([
                    cst.Return(
                        value=Name(
                            value=node.name.value,
                            lpar=[],
                            rpar=[],
                        )
                    ),
                ])
            ]
        )
    )
    return wrapper



class RemoveAnnotationCommand(VisitorBasedCodemodCommand):
    METADATA_DEPENDENCIES = (ScopeProvider, )

    def __init__(self, context: CodemodContext) -> None:
        self.node_to_wrapper: dict[FunctionDef | ClassDef, Any] = {}
        super().__init__(context)

    def visit_FunctionDef(self, node: FunctionDef):
        AddImportsVisitor.add_needed_import(self.context, "typing", "TypeAlias")
        AddImportsVisitor.add_needed_import(self.context, "typing", "TypeVar")
        AddImportsVisitor.add_needed_import(self.context, "typing", "ParamSpec")
        AddImportsVisitor.add_needed_import(self.context, "typing", "TypeVarTuple")

        type_params = node.type_parameters
        if type_params is None:
            return False
        
        type_scope = self.get_metadata(ScopeProvider, type_params)
        body_scope = self.get_metadata(ScopeProvider, node.body)
        replacemences = {}
        prefix = f"__{node.name.value}_"
        for type_param in type_params.params:
            for scope in [type_scope, body_scope]:
                assert isinstance(scope, Scope)
                for access in set(scope.accesses[type_param.param.name]):
                    assert isinstance(access.node, Name)
                    replacemences[access.node] = Name(value=f"{prefix}{type_param.param.name.value}")
        new_node = node.visit(ReplaceNodes(replacemences))
        assert isinstance(new_node, FunctionDef)

        type_vars, new_node = remove_type_parameters(new_node, prefix=prefix)

        if type_vars:
            wrapper = gen_func_wrapper(new_node, type_vars)
            self.node_to_wrapper[node] = wrapper
        return False

    def leave_FunctionDef(self, original_node: FunctionDef, updated_node: FunctionDef):
        wrapper = self.node_to_wrapper.get(original_node, None)
        if wrapper is None:
            return updated_node
        func = SimpleStatementLine([Assign(
            targets=[AssignTarget(updated_node.name)],
            value=Call(
                func=Name(
                    value=f'__wrapper_func_{updated_node.name.value}'
                ),
                args=[],
            ),
        )])

        return FlattenSentinel([wrapper, func])

    def visit_ClassDef(self, node: ClassDef):
        AddImportsVisitor.add_needed_import(self.context, "typing", "Generic")
        AddImportsVisitor.add_needed_import(self.context, "typing", "TypeVar")
        AddImportsVisitor.add_needed_import(self.context, "typing", "ParamSpec")
        AddImportsVisitor.add_needed_import(self.context, "typing", "TypeVarTuple")

        type_params = node.type_parameters
        if type_params is None:
            return True

        scopes = [self.get_metadata(ScopeProvider, type_params)]
        for b in node.body.body:
            scopes.append(self.get_metadata(ScopeProvider, b))
            if isinstance(b, FunctionDef):
                scopes.append(self.get_metadata(ScopeProvider, b.body))
        
        replacemences = {}
        prefix = f"__{node.name.value}_"
        for type_param in type_params.params:
            for scope in scopes:
                assert isinstance(scope, Scope)
                for access in set(scope.accesses[type_param.param.name]):
                    assert isinstance(access.node, Name)
                    replacemences[access.node] = Name(value=f"{prefix}{type_param.param.name.value}")
        new_node = node.visit(ReplaceNodes(replacemences))
        assert isinstance(new_node, ClassDef)

        type_vars, new_node = remove_type_parameters(new_node, prefix=prefix)

        if type_vars:
            self.node_to_wrapper[node] = new_node, type_vars
        return True

    def leave_ClassDef(self, original_node: ClassDef, updated_node: ClassDef):
        new_node, type_vars = self.node_to_wrapper.get(original_node, None)
        return FlattenSentinel([*type_vars, new_node])

module = cst.parse_module(
    """
def test[T: int | str, P](x: T, y: P) -> T:
    y: T = 1
    print(x)
    print(T)
    return x

class Test2[A](A, B):
    z: A 
    def __init__(self, x: A) -> None:
        self.x: A = x
    
    def test[B](self, y: B) -> tuple[A, B]:  # TODO: support nested type parameters
        return self.x, y
"""
)
# TODO: support nested type parameters
# print(module)
wrapper = cst.MetadataWrapper(module)
print(wrapper.module.code)
# exec(module.code)
modified_module = wrapper.visit(RemoveAnnotationCommand(CodemodContext()))
print(modified_module.code)
# exec(modified_module.code)
