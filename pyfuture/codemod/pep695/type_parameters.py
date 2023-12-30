from __future__ import annotations

from typing import Any

import libcst as cst
from libcst import (
    Arg,
    Assign,
    AssignTarget,
    Call,
    ClassDef,
    FunctionDef,
    Index,
    Name,
    SimpleStatementLine,
    Subscript,
    SubscriptElement,
)
from libcst.codemod import (
    CodemodContext,
    VisitorBasedCodemodCommand,
)
from libcst.codemod.visitors import AddImportsVisitor
from libcst.metadata import Scope, ScopeProvider

from ...transformer import ReplaceTransformer
from ..utils import gen_func_wrapper, gen_type_param


class TransformTypeParametersCommand(VisitorBasedCodemodCommand):
    """
    Remove type parameters from node, and return a list of statements and a new node.

    Example:
    >>> transformer = TransformTypeParametersCommand(CodemodContext())
    >>> module = cst.parse_module(\"""
    ... def test[T: int](x: T) -> T:
    ...     return x
    ... \""")
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    from typing import TypeVar
    def __wrapper_func_test():
        __test_T = TypeVar("__test_T", bound = int)
        def test(x: __test_T) -> __test_T:
            return x
        return test
    test = __wrapper_func_test()
    >>> module = cst.parse_module(\"""
    ... def test[T: int | str](x: T) -> T:
    ...     return x
    ... \""")
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    from typing import TypeVar
    def __wrapper_func_test():
        __test_T = TypeVar("__test_T", bound = Union[int, str])
        def test(x: __test_T) -> __test_T:
            return x
        return test
    test = __wrapper_func_test()
    >>> module = cst.parse_module(\"""
    ... class Test[T: int]:
    ...     def test[P: str](self, x: T, y: P) -> tuple[T, P]:
    ...         return x, y
    ... \""")
    >>> new_module = transformer.transform_module(module)
    >>> print(new_module.code)
    from typing import Generic, TypeVar
    __Test_T = TypeVar("__Test_T", bound = int)
    class Test(Generic[__Test_T]):
        __Test_test_P = TypeVar("__Test_test_P", bound = str)
        def test(self, x: __Test_T, y: __Test_test_P) -> tuple[__Test_T, __Test_test_P]:
            return x, y
    """

    METADATA_DEPENDENCIES = (ScopeProvider,)

    def __init__(self, context: CodemodContext) -> None:
        self.node_to_wrapper: dict[FunctionDef | ClassDef, Any] = {}
        super().__init__(context)

    def remove_type_parameters[T: FunctionDef | ClassDef](
        self, node: T, prefix: str = "", suffix: str = ""
    ) -> tuple[list[SimpleStatementLine], T]:
        type_params = node.type_parameters
        if type_params is None:
            return [], node
        statements = []
        new_node = node.with_changes(type_parameters=None)

        slices = []
        for type_param in type_params.params:
            new_name = type_param.param.name.with_changes(value=f"{prefix}{type_param.param.name.value}{suffix}")

            AddImportsVisitor.add_needed_import(self.context, "typing", type_param.param.__class__.__name__)
            statements.append(gen_type_param(type_param.param, new_name))
            slices.append(
                SubscriptElement(
                    slice=Index(value=new_name),
                ),
            )

        if isinstance(new_node, ClassDef) and slices:
            AddImportsVisitor.add_needed_import(self.context, "typing", "Generic")
            generic_base = Arg(
                value=Subscript(
                    value=Name(
                        value="Generic",
                        lpar=[],
                        rpar=[],
                    ),
                    slice=slices,
                )
            )
            new_node = new_node.with_changes(bases=[*new_node.bases, generic_base])

        return statements, new_node

    def visit_FunctionDef(self, node: FunctionDef):
        type_params = node.type_parameters
        if type_params is None:
            return False

        node_scope = self.get_metadata(ScopeProvider, type_params)
        body_scope = self.get_metadata(ScopeProvider, node.body)
        replacemences = {}
        prefix = f"__{node.name.value}_"
        for type_param in type_params.params:
            for scope in [node_scope, body_scope]:
                assert isinstance(scope, Scope)
                for access in set(scope.accesses[type_param.param.name]):
                    assert isinstance(access.node, Name)
                    replacemences[access.node] = Name(value=f"{prefix}{type_param.param.name.value}")
        new_node = node.visit(ReplaceTransformer(replacemences))
        assert isinstance(new_node, FunctionDef)

        type_vars, new_node = self.remove_type_parameters(new_node, prefix=prefix)

        if type_vars:
            wrapper = gen_func_wrapper(new_node, type_vars)
            self.node_to_wrapper[node] = wrapper
        return False

    def leave_FunctionDef(self, original_node: FunctionDef, updated_node: FunctionDef):
        wrapper = self.node_to_wrapper.get(original_node, None)
        if wrapper is None:
            return updated_node
        func = SimpleStatementLine(
            [
                Assign(
                    targets=[AssignTarget(updated_node.name)],
                    value=Call(
                        func=Name(value=f"__wrapper_func_{updated_node.name.value}"),
                        args=[],
                    ),
                )
            ]
        )

        return cst.FlattenSentinel([wrapper, func])

    def visit_ClassDef(self, node: ClassDef):
        type_params = node.type_parameters
        replacemences = {}
        scopes = []
        for subnode in node.body.body:
            subnode_scope = self.get_metadata(ScopeProvider, subnode)
            scopes.append(subnode_scope)
            if isinstance(subnode, FunctionDef):
                subnode_body_scope = self.get_metadata(ScopeProvider, subnode.body)
                scopes.append(subnode_body_scope)

                subnode_type_params = subnode.type_parameters
                if subnode_type_params is None:
                    continue
                subnode_type_scope = self.get_metadata(ScopeProvider, subnode_type_params)
                scopes.append(subnode_type_scope)

                prefix = f"__{node.name.value}_{subnode.name.value}_"
                for type_param in subnode_type_params.params:
                    for scope in [subnode_type_scope, subnode_body_scope]:
                        assert isinstance(scope, Scope)
                        for access in set(scope.accesses[type_param.param.name]):
                            assert isinstance(access.node, Name)
                            replacemences[access.node] = Name(value=f"{prefix}{type_param.param.name.value}")

        prefix = f"__{node.name.value}_"
        if type_params is not None:
            scopes.append(self.get_metadata(ScopeProvider, type_params))
            for type_param in type_params.params:
                for scope in scopes:
                    assert isinstance(scope, Scope)
                    for access in set(scope.accesses[type_param.param.name]):
                        assert isinstance(access.node, Name)
                        replacemences[access.node] = Name(value=f"{prefix}{type_param.param.name.value}")

        new_node = node.visit(ReplaceTransformer(replacemences))
        assert isinstance(new_node, ClassDef)

        type_vars, new_node = self.remove_type_parameters(new_node, prefix=prefix)

        self.node_to_wrapper[node] = new_node, type_vars
        # TODO: Maybe `class in class` need True?
        return False

    def leave_ClassDef(self, original_node: ClassDef, updated_node: ClassDef):
        if self.node_to_wrapper.get(original_node, None) is None:
            return updated_node
        new_node, type_vars = self.node_to_wrapper[original_node]
        replacemences = {}
        for subnode in new_node.body.body:
            if isinstance(subnode, FunctionDef):
                prefix = f"__{new_node.name.value}_{subnode.name.value}_"
                sub_type_vars, new_subnode = self.remove_type_parameters(subnode, prefix=prefix)
                replacemences[subnode] = cst.FlattenSentinel([*sub_type_vars, new_subnode])

        new_node = new_node.visit(ReplaceTransformer(replacemences))
        return cst.FlattenSentinel([*type_vars, new_node])
