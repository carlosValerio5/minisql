"""Pruebas del optimizador TAC."""

from sqlmini.ast import BinaryOp, BinaryOpKind, LiteralInt
from sqlmini.optimize import dead_code_elimination, optimize_block
from sqlmini.tac import Quad, emit_expression


def test_fold_const_add() -> None:
    expr = BinaryOp(BinaryOpKind.ADD, LiteralInt(2), LiteralInt(3))
    quads, res = emit_expression(expr)
    assert any(q.op == "ADD" for q in quads)
    opt = optimize_block(quads, {res})
    assert any(q.op == "CONST_I" and q.lhs == "5" for q in opt)


def test_dce_removes_unused() -> None:
    quads = [
        Quad("CONST_I", "t0", "1", None),
        Quad("CONST_I", "t1", "2", None),
        Quad("ADD", "t2", "t0", "t1"),
        Quad("CONST_I", "t3", "9", None),
    ]
    live = {"t2"}
    out = dead_code_elimination(quads, live)
    dsts = [q.dst for q in out]
    assert "t2" in dsts
    assert "t3" not in dsts
