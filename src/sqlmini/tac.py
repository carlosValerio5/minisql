"""
Generación de código intermedio en forma de cuádruplas (TAC).

Cada expresión se traduce a una secuencia de instrucciones de tres direcciones
con temporales ``t0``, ``t1``, etc.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmini.ast import (
    BinaryOp,
    BinaryOpKind,
    Expr,
    Identifier,
    LiteralBool,
    LiteralInt,
    UnaryOp,
    UnaryOpKind,
)


@dataclass(frozen=True, slots=True)
class Quad:
    """
    Instrucción de tres direcciones.

    Attributes:
        op: Código de operación (por ejemplo ``CONST_I``, ``ADD``, ``COL``).
        dst: Destino (temporal) o None para futuras extensiones.
        lhs: Primer operando (temporal, literal serializado o nombre de columna).
        rhs: Segundo operando si aplica.
    """

    op: str
    dst: str | None
    lhs: str | None
    rhs: str | None


class TACEmitter:
    """
    Emite cuádruplas para subexpresiones manteniendo contador de temporales.

    Se instancia por expresión o bloque para evitar colisiones de nombres
    entre fragmentos si se desea; el CLI concatena listas.
    """

    def __init__(self) -> None:
        self._counter = 0
        self.quads: list[Quad] = []

    def new_temp(self) -> str:
        """Reserva un nombre de temporal único en esta emisión."""
        t = f"t{self._counter}"
        self._counter += 1
        return t

    def emit_expr(self, expr: Expr) -> str:
        """
        Emite instrucciones para evaluar la expresión y devuelve el temporal resultado.

        Args:
            expr: Subárbol de expresión.

        Returns:
            Nombre del temporal que contiene el valor.
        """
        if isinstance(expr, LiteralInt):
            dst = self.new_temp()
            self.quads.append(Quad("CONST_I", dst, str(expr.value), None))
            return dst
        if isinstance(expr, LiteralBool):
            dst = self.new_temp()
            self.quads.append(Quad("CONST_B", dst, "true" if expr.value else "false", None))
            return dst
        if isinstance(expr, Identifier):
            dst = self.new_temp()
            self.quads.append(Quad("COL", dst, expr.name, None))
            return dst
        if isinstance(expr, UnaryOp):
            if expr.op != UnaryOpKind.NOT:
                raise ValueError("Operador unario no soportado en TAC")
            inner = self.emit_expr(expr.operand)
            dst = self.new_temp()
            self.quads.append(Quad("NOT", dst, inner, None))
            return dst
        if isinstance(expr, BinaryOp):
            return self._emit_binary(expr)
        raise TypeError(f"Expresión no soportada: {type(expr)!r}")

    def _emit_binary(self, expr: BinaryOp) -> str:
        left = self.emit_expr(expr.left)
        right = self.emit_expr(expr.right)
        dst = self.new_temp()
        op_map: dict[BinaryOpKind, str] = {
            BinaryOpKind.OR: "OR",
            BinaryOpKind.AND: "AND",
            BinaryOpKind.EQ: "EQ",
            BinaryOpKind.NE: "NE",
            BinaryOpKind.LT: "LT",
            BinaryOpKind.GT: "GT",
            BinaryOpKind.LE: "LE",
            BinaryOpKind.GE: "GE",
            BinaryOpKind.ADD: "ADD",
            BinaryOpKind.SUB: "SUB",
            BinaryOpKind.MUL: "MUL",
            BinaryOpKind.DIV: "DIV",
        }
        if expr.op not in op_map:
            raise ValueError(f"Operador binario no soportado: {expr.op}")
        self.quads.append(Quad(op_map[expr.op], dst, left, right))
        return dst


def emit_expression(expr: Expr) -> tuple[list[Quad], str]:
    """
    Emite TAC para una expresión aislada.

    Args:
        expr: Expresión a traducir.

    Returns:
        Par (lista de cuádruplas, temporal resultado).
    """
    em = TACEmitter()
    res = em.emit_expr(expr)
    return em.quads, res


def format_quads(quads: list[Quad]) -> str:
    """
    Formatea las cuádruplas en texto legible para depuración o entregables.

    Args:
        quads: Secuencia de instrucciones.

    Returns:
        Cadena multilínea con una instrucción por línea.
    """
    lines: list[str] = []
    for q in quads:
        lines.append(f"{q.op:8} {q.dst or '-':>6} <- {q.lhs or '-'} , {q.rhs or '-'}")
    return "\n".join(lines)
