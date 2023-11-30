from __future__ import annotations

import libcst as cst

from pyfuture.transformer import ReplaceTransformer


def test_transformers():
    node_a = cst.Name("a")
    node_b = cst.Name("b")
    node_c = cst.Name("c")
    target_a = cst.AssignTarget(target=node_a)
    target_b = cst.AssignTarget(target=node_b)
    target_c = cst.AssignTarget(target=node_c)
    assign_a = cst.Assign(targets=[target_a], value=cst.Integer("1"))
    assign_b = cst.Assign(targets=[target_b], value=cst.Integer("2"))
    assign_c = cst.Assign(targets=[target_c], value=cst.Integer("3"))
    statement_line_a = cst.SimpleStatementLine([assign_a])
    statement_line_b = cst.SimpleStatementLine([assign_b])
    statement_line_c = cst.SimpleStatementLine([assign_c])
    module = cst.Module(body=[statement_line_a, statement_line_b, statement_line_c])

    new_module = module.visit(
        ReplaceTransformer(
            {
                node_a: node_b,
                node_b: node_c,
                node_c: node_a,
            }
        )
    )

    assert new_module.code == "b = 1\nc = 2\na = 3\n"
