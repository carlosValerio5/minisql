"""
Intérprete en memoria para el mini lenguaje sqlmini.

Ejecuta sentencias DDL/DML y evalúa ``SELECT`` aplicando TAC fila a fila
sobre un almacén de tablas en RAM.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlmini.ast import CreateTable, Insert, LiteralBool, LiteralInt, Select
from sqlmini.optimize import optimize_block
from sqlmini.semantic import SemanticBundle
from sqlmini.symbols import TableSchema
from sqlmini.tac import Quad, TACEmitter, format_quads


@dataclass
class _Runtime:
    """Estado mutable de tablas y filas durante la ejecución."""

    schemas: dict[str, TableSchema] = field(default_factory=dict)
    rows: dict[str, list[list[int | bool]]] = field(default_factory=dict)


def _operand_value(
    name: str | None,
    temps: dict[str, int | bool],
    row: dict[str, int | bool],
) -> int | bool:
    if name is None:
        raise ValueError("operando ausente")
    if name.startswith("t") and name[1:].isdigit():
        return temps[name]
    if name in ("true", "false"):
        return name == "true"
    if name.lstrip("-").isdigit():
        return int(name)
    if name in row:
        return row[name]
    raise KeyError(name)


def eval_quads(quads: list[Quad], row: dict[str, int | bool]) -> dict[str, int | bool]:
    """
    Evalúa una secuencia de cuádruplas contra una fila concreta.

    Args:
        quads: Instrucciones TAC.
        row: Mapa nombre_columna -> valor para ``COL``.

    Returns:
        Mapa temporal -> valor tras la última instrucción.
    """
    temps: dict[str, int | bool] = {}
    for q in quads:
        if q.op == "CONST_I":
            assert q.dst and q.lhs is not None
            temps[q.dst] = int(q.lhs)
        elif q.op == "CONST_B":
            assert q.dst and q.lhs is not None
            temps[q.dst] = q.lhs == "true"
        elif q.op == "COL":
            assert q.dst and q.lhs is not None
            temps[q.dst] = row[q.lhs]
        elif q.op == "NOT":
            assert q.dst and q.lhs is not None
            v = _operand_value(q.lhs, temps, row)
            if not isinstance(v, bool):
                raise TypeError("NOT requiere BOOL")
            temps[q.dst] = not v
        elif q.op in ("ADD", "SUB", "MUL", "DIV"):
            assert q.dst and q.lhs is not None and q.rhs is not None
            a = int(_operand_value(q.lhs, temps, row))
            b = int(_operand_value(q.rhs, temps, row))
            if q.op == "ADD":
                temps[q.dst] = a + b
            elif q.op == "SUB":
                temps[q.dst] = a - b
            elif q.op == "MUL":
                temps[q.dst] = a * b
            else:
                if b == 0:
                    raise ZeroDivisionError("división por cero en evaluación")
                temps[q.dst] = a // b
        elif q.op in ("EQ", "NE"):
            assert q.dst and q.lhs is not None and q.rhs is not None
            x = _operand_value(q.lhs, temps, row)
            y = _operand_value(q.rhs, temps, row)
            if type(x) is not type(y):
                raise TypeError("tipos incomparables")
            temps[q.dst] = (x == y) if q.op == "EQ" else (x != y)
        elif q.op in ("LT", "GT", "LE", "GE"):
            assert q.dst and q.lhs is not None and q.rhs is not None
            a = int(_operand_value(q.lhs, temps, row))
            b = int(_operand_value(q.rhs, temps, row))
            if q.op == "LT":
                temps[q.dst] = a < b
            elif q.op == "GT":
                temps[q.dst] = a > b
            elif q.op == "LE":
                temps[q.dst] = a <= b
            else:
                temps[q.dst] = a >= b
        elif q.op in ("AND", "OR"):
            assert q.dst and q.lhs is not None and q.rhs is not None
            a = _operand_value(q.lhs, temps, row)
            b = _operand_value(q.rhs, temps, row)
            if not isinstance(a, bool) or not isinstance(b, bool):
                raise TypeError("AND/OR requiere BOOL")
            temps[q.dst] = (a and b) if q.op == "AND" else (a or b)
        else:
            raise ValueError(f"Opcode desconocido: {q.op}")
    return temps


def _literal_py(v: LiteralInt | LiteralBool) -> int | bool:
    if isinstance(v, LiteralInt):
        return v.value
    return v.value


def run_program(bundle: SemanticBundle, *, optimize: bool = True) -> str:
    """
    Ejecuta el programa validado y devuelve la salida textual de los SELECT.

    Args:
        bundle: Resultado del análisis semántico.
        optimize: Si es True, optimiza cada fragmento TAC antes de evaluar.

    Returns:
        Texto acumulado (líneas ``SELECT`` serializadas).
    """
    return _format_select_output(bundle, optimize)


def _format_value(v: int | bool) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _format_select_output(bundle: SemanticBundle, optimize: bool) -> str:
    """Genera salida legible: cada SELECT produce líneas de filas."""
    rt = _Runtime()
    chunks: list[str] = []
    program = bundle.program

    for stmt in program.statements:
        if isinstance(stmt, CreateTable):
            sch = bundle.schemas[stmt.name]
            rt.schemas[stmt.name] = sch
            rt.rows[stmt.name] = []
        elif isinstance(stmt, Insert):
            row = [_literal_py(v) for v in stmt.values]
            rt.rows[stmt.table].append(row)
        elif isinstance(stmt, Select):
            schema = rt.schemas[stmt.table]
            col_names = [c for c, _ in schema.columns]
            table_rows = rt.rows.get(stmt.table, [])

            where_quads: list[Quad] = []
            where_res: str | None = None
            if stmt.where is not None:
                em_w = TACEmitter()
                where_res = em_w.emit_expr(stmt.where)
                where_quads = em_w.quads
                if optimize and where_res is not None:
                    where_quads = optimize_block(where_quads, {where_res})

            proj_plan: list[tuple[list[Quad], str]] = []
            for proj in stmt.projections:
                em_p = TACEmitter()
                res = em_p.emit_expr(proj)
                qs = em_p.quads
                if optimize:
                    qs = optimize_block(qs, {res})
                proj_plan.append((qs, res))

            lines: list[str] = []
            for raw_row in table_rows:
                row_map = {n: raw_row[i] for i, n in enumerate(col_names)}
                if stmt.where is not None:
                    assert where_res is not None
                    wenv = eval_quads(where_quads, row_map)
                    if not bool(wenv[where_res]):
                        continue
                cells = []
                for qs, res in proj_plan:
                    env = eval_quads(qs, row_map)
                    cells.append(_format_value(env[res]))
                lines.append(" | ".join(cells))
            chunks.append("\n".join(lines))
    return "\n".join(chunks)


def dump_tac_for_program(bundle: SemanticBundle, *, optimize: bool) -> str:
    """
    Serializa el TAC generado para cada ``SELECT`` del programa.

    Args:
        bundle: Programa tipado.
        optimize: Si aplica el optimizador antes de imprimir.

    Returns:
        Texto multisección para depuración.
    """
    parts: list[str] = []
    program = bundle.program
    for stmt in program.statements:
        if not isinstance(stmt, Select):
            continue
        block = []
        if stmt.where is not None:
            em = TACEmitter()
            r = em.emit_expr(stmt.where)
            wq = em.quads
            if optimize:
                wq = optimize_block(wq, {r})
            block.append("-- WHERE --\n" + format_quads(wq))
        for i, proj in enumerate(stmt.projections):
            em = TACEmitter()
            r = em.emit_expr(proj)
            pq = em.quads
            if optimize:
                pq = optimize_block(pq, {r})
            block.append(f"-- PROJ {i} --\n" + format_quads(pq))
        parts.append("\n\n".join(block))
    return "\n\n==== SELECT ====\n\n".join(parts) if parts else "(sin SELECT)\n"
