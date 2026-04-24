"""
Optimizaciones básicas sobre bloques TAC: propagación de constantes y DCE.

Opera sobre temporales generados por el emisor; trata ``COL`` como valor
desconocido en tiempo de compilación para no plegar expresiones que dependen
de la fila actual.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sqlmini.tac import Quad

_UNK = object()


def _is_temp(name: str | None) -> bool:
    return name is not None and name.startswith("t") and name[1:].isdigit()


def _uses(q: Quad) -> set[str]:
    out: set[str] = set()
    for x in (q.lhs, q.rhs):
        if _is_temp(x):
            out.add(x)
    return out


def _defines(q: Quad) -> str | None:
    return q.dst if _is_temp(q.dst) else None


def dead_code_elimination(quads: list[Quad], live_out: set[str]) -> list[Quad]:
    """
    Elimina asignaciones a temporales cuyos valores no son observados.

    Args:
        quads: Bloque lineal de instrucciones.
        live_out: Temporales considerados vivos al final del bloque.

    Returns:
        Subsecuencia de instrucciones conservando orden relativo.
    """
    n = len(quads)
    if n == 0:
        return []
    live = set(live_out)
    needed = [False] * n
    for i in range(n - 1, -1, -1):
        q = quads[i]
        d = _defines(q)
        uses = _uses(q)
        if d and d in live:
            needed[i] = True
        if uses & live:
            needed[i] = True
        if d:
            live.discard(d)
        live |= uses
    return [quads[i] for i in range(n) if needed[i]]


def _parse_literal(s: str | None) -> int | bool | None:
    if s is None:
        return None
    if s in ("true", "false"):
        return s == "true"
    if s.lstrip("-").isdigit():
        return int(s)
    return None


def _resolve_operand(s: str | None, val: dict[str, Any]) -> Any:
    """Devuelve int, bool, _UNK o None si no es const (temp libre)."""
    if s is None:
        return None
    if _is_temp(s):
        return val.get(s)
    lit = _parse_literal(s)
    if lit is not None:
        return lit
    return None


def _try_fold_binary(op: str, a: Any, b: Any, dst: str | None) -> Quad | None:
    if dst is None:
        return None
    if op == "ADD" and isinstance(a, int) and isinstance(b, int):
        return Quad("CONST_I", dst, str(a + b), None)
    if op == "SUB" and isinstance(a, int) and isinstance(b, int):
        return Quad("CONST_I", dst, str(a - b), None)
    if op == "MUL" and isinstance(a, int) and isinstance(b, int):
        return Quad("CONST_I", dst, str(a * b), None)
    if op == "DIV" and isinstance(a, int) and isinstance(b, int):
        if b == 0:
            return None
        return Quad("CONST_I", dst, str(a // b), None)
    if op == "EQ" and a is not _UNK and b is not _UNK and type(a) is type(b):
        return Quad("CONST_B", dst, "true" if a == b else "false", None)
    if op == "NE" and a is not _UNK and b is not _UNK and type(a) is type(b):
        return Quad("CONST_B", dst, "true" if a != b else "false", None)
    if op == "LT" and isinstance(a, int) and isinstance(b, int):
        return Quad("CONST_B", dst, "true" if a < b else "false", None)
    if op == "GT" and isinstance(a, int) and isinstance(b, int):
        return Quad("CONST_B", dst, "true" if a > b else "false", None)
    if op == "LE" and isinstance(a, int) and isinstance(b, int):
        return Quad("CONST_B", dst, "true" if a <= b else "false", None)
    if op == "GE" and isinstance(a, int) and isinstance(b, int):
        return Quad("CONST_B", dst, "true" if a >= b else "false", None)
    if op == "AND" and isinstance(a, bool) and isinstance(b, bool):
        return Quad("CONST_B", dst, "true" if (a and b) else "false", None)
    if op == "OR" and isinstance(a, bool) and isinstance(b, bool):
        return Quad("CONST_B", dst, "true" if (a or b) else "false", None)
    return None


def constant_propagation(quads: list[Quad]) -> list[Quad]:
    """
    Plegado de constantes cuando ambos operandos son valores conocidos.

    Args:
        quads: Bloque original.

    Returns:
        Bloque transformado.
    """
    val: dict[str, Any] = {}
    out: list[Quad] = []

    for q in quads:
        if q.op == "CONST_I" and q.dst and q.lhs is not None:
            out.append(q)
            val[q.dst] = int(q.lhs)
            continue
        if q.op == "CONST_B" and q.dst and q.lhs is not None:
            out.append(q)
            val[q.dst] = q.lhs == "true"
            continue
        if q.op == "COL" and q.dst:
            out.append(q)
            val[q.dst] = _UNK
            continue
        if q.op == "NOT" and q.dst and q.lhs is not None:
            a = _resolve_operand(q.lhs, val)
            if isinstance(a, bool):
                folded = Quad("CONST_B", q.dst, "false" if a else "true", None)
                out.append(folded)
                val[q.dst] = not a
                continue

        if q.op in (
            "ADD",
            "SUB",
            "MUL",
            "DIV",
            "EQ",
            "NE",
            "LT",
            "GT",
            "LE",
            "GE",
            "AND",
            "OR",
        ):
            a = _resolve_operand(q.lhs, val)
            b = _resolve_operand(q.rhs, val)
            if a is _UNK or b is _UNK or a is None or b is None:
                nl = q.lhs
                nr = q.rhs
                if _is_temp(q.lhs) and q.lhs in val and val[q.lhs] is not _UNK:
                    v = val[q.lhs]
                    nl = "true" if v is True else "false" if v is False else str(v)
                if _is_temp(q.rhs) and q.rhs in val and val[q.rhs] is not _UNK:
                    v = val[q.rhs]
                    nr = "true" if v is True else "false" if v is False else str(v)
                out.append(replace(q, lhs=nl, rhs=nr))
                if q.dst:
                    val[q.dst] = _UNK
                continue
            folded = _try_fold_binary(q.op, a, b, q.dst)
            if folded is not None:
                out.append(folded)
                if folded.op == "CONST_I" and folded.lhs is not None:
                    val[folded.dst] = int(folded.lhs)
                elif folded.op == "CONST_B" and folded.lhs is not None:
                    val[folded.dst] = folded.lhs == "true"
                continue

        out.append(q)
        if q.dst:
            val[q.dst] = _UNK

    return out


def optimize_block(quads: list[Quad], live_out: set[str]) -> list[Quad]:
    """
    Aplica propagación/plegado de constantes y eliminación de código muerto.

    Args:
        quads: Bloque lineal.
        live_out: Temporales vivos al final (por ejemplo resultados proyectados).

    Returns:
        Bloque optimizado.
    """
    folded = constant_propagation(quads)
    return dead_code_elimination(folded, live_out)
