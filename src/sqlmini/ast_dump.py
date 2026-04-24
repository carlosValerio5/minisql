"""
Serialización legible del AST para depuración y entregables del curso.
"""

from __future__ import annotations

from sqlmini.ast import (
    BinaryOp,
    CreateTable,
    Expr,
    Identifier,
    Insert,
    LiteralBool,
    LiteralInt,
    Program,
    Select,
    UnaryOp,
)


def format_ast(program: Program) -> str:
    """
    Construye una representación en texto indentada del programa.

    Args:
        program: Nodo raíz ``Program``.

    Returns:
        Cadena multilínea con la forma del árbol.
    """
    lines: list[str] = []
    for stmt in program.statements:
        lines.extend(_format_statement(stmt, indent=0))
    return "\n".join(lines)


def _format_statement(stmt: object, indent: int) -> list[str]:
    pad = "  " * indent
    if isinstance(stmt, CreateTable):
        cols = ", ".join(f"{n}:{t.name}" for n, t in stmt.columns)
        return [f"{pad}CreateTable({stmt.name!r}, [{cols}])"]
    if isinstance(stmt, Insert):
        vals = ", ".join(_format_literal(v) for v in stmt.values)
        return [f"{pad}Insert({stmt.table!r}, [{vals}])"]
    if isinstance(stmt, Select):
        out = [f"{pad}Select(from={stmt.table!r})"]
        for i, e in enumerate(stmt.projections):
            out.append(f"{pad}  proj[{i}]:")
            out.extend(_format_expr(e, indent + 2))
        if stmt.where is not None:
            out.append(f"{pad}  where:")
            out.extend(_format_expr(stmt.where, indent + 2))
        return out
    return [f"{pad}<??? {stmt!r}>"]


def _format_literal(v: LiteralInt | LiteralBool) -> str:
    if isinstance(v, LiteralInt):
        return str(v.value)
    return "true" if v.value else "false"


def _format_expr(expr: Expr, indent: int) -> list[str]:
    pad = "  " * indent
    if isinstance(expr, LiteralInt):
        return [f"{pad}LiteralInt({expr.value})"]
    if isinstance(expr, LiteralBool):
        return [f"{pad}LiteralBool({expr.value})"]
    if isinstance(expr, Identifier):
        return [f"{pad}Identifier({expr.name!r})"]
    if isinstance(expr, UnaryOp):
        lines = [f"{pad}UnaryOp({expr.op.name})"]
        lines.extend(_format_expr(expr.operand, indent + 1))
        return lines
    if isinstance(expr, BinaryOp):
        lines = [f"{pad}BinaryOp({expr.op.name})"]
        lines.extend(_format_expr(expr.left, indent + 1))
        lines.extend(_format_expr(expr.right, indent + 1))
        return lines
    return [f"{pad}<??? {expr!r}>"]
