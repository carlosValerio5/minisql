"""
Análisis semántico: tabla de símbolos, tipos y reglas del lenguaje.

Recorre las sentencias en orden para reflejar el crecimiento del catálogo
igual que en una ejecución interpretada.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmini.ast import (
    BinaryOp,
    BinaryOpKind,
    CreateTable,
    DataType,
    Expr,
    Identifier,
    Insert,
    LiteralBool,
    LiteralInt,
    Program,
    Select,
    UnaryOp,
    UnaryOpKind,
)
from sqlmini.errors import SemanticError, SourceLocation
from sqlmini.symbols import TableSchema


@dataclass(frozen=True, slots=True)
class SemanticBundle:
    """
    Resultado del análisis semántico listo para generación de código.

    Attributes:
        program: AST validado.
        schemas: Catálogo de tablas conocidas al final del programa.
        expr_types: Mapa identidad de nodo expresión -> tipo deducido.
    """

    program: Program
    schemas: dict[str, TableSchema]
    expr_types: dict[int, DataType]


def analyze(program: Program) -> SemanticBundle:
    """
    Ejecuta el análisis semántico completo sobre el programa.

    Args:
        program: AST raíz.

    Returns:
        ``SemanticBundle`` con tipos anotados.

    Raises:
        SemanticError: Si hay conflictos de esquema o tipos incorrectos.
    """
    a = _Analyzer()
    return a.analyze(program)


def _loc_from_expr(expr: Expr) -> SourceLocation | None:
    if expr.span is None:
        return None
    return SourceLocation(expr.span.line, expr.span.column)


class _Analyzer:
    """Estado del analizador semántico (catálogo y utilidades de tipos)."""

    def __init__(self) -> None:
        self._schemas: dict[str, TableSchema] = {}
        self._expr_types: dict[int, DataType] = {}

    def analyze(self, program: Program) -> SemanticBundle:
        for stmt in program.statements:
            if isinstance(stmt, CreateTable):
                self._visit_create(stmt)
            elif isinstance(stmt, Insert):
                self._visit_insert(stmt)
            elif isinstance(stmt, Select):
                self._visit_select(stmt)
        return SemanticBundle(
            program=program,
            schemas=dict(self._schemas),
            expr_types=dict(self._expr_types),
        )

    def _visit_create(self, stmt: CreateTable) -> None:
        if stmt.name in self._schemas:
            raise SemanticError(
                f"La tabla {stmt.name!r} ya está definida",
                _loc_from_stmt(stmt),
            )
        names = [c for c, _ in stmt.columns]
        if len(set(names)) != len(names):
            raise SemanticError(
                "Definición inválida: nombres de columna duplicados",
                _loc_from_stmt(stmt),
            )
        self._schemas[stmt.name] = TableSchema(stmt.name, list(stmt.columns))

    def _visit_insert(self, stmt: Insert) -> None:
        schema = self._schemas.get(stmt.table)
        if schema is None:
            raise SemanticError(
                f"Tabla desconocida: {stmt.table!r}",
                _loc_from_stmt(stmt),
            )
        if len(stmt.values) != len(schema.columns):
            n_exp, n_got = len(schema.columns), len(stmt.values)
            raise SemanticError(
                f"INSERT: se esperaban {n_exp} valores, se obtuvieron {n_got}",
                _loc_from_stmt(stmt),
            )
        for val, (col_name, col_ty) in zip(stmt.values, schema.columns, strict=True):
            vty = self._literal_type(val)
            if vty != col_ty:
                msg = (
                    f"Tipo incompatible en columna {col_name!r}: "
                    f"se esperaba {col_ty.name}, se obtuvo {vty.name}"
                )
                raise SemanticError(msg, _loc_from_stmt(stmt))

    def _visit_select(self, stmt: Select) -> None:
        schema = self._schemas.get(stmt.table)
        if schema is None:
            raise SemanticError(
                f"Tabla desconocida: {stmt.table!r}",
                _loc_from_stmt(stmt),
            )
        env = schema.types_by_name()
        for proj in stmt.projections:
            self._type_expr(proj, env)
        if stmt.where is not None:
            wt = self._type_expr(stmt.where, env)
            if wt != DataType.BOOL:
                raise SemanticError(
                    "La cláusula WHERE debe ser de tipo BOOL",
                    _loc_from_expr(stmt.where),
                )

    def _literal_type(self, val: LiteralInt | LiteralBool) -> DataType:
        if isinstance(val, LiteralInt):
            return DataType.INT
        return DataType.BOOL

    def _type_expr(self, expr: Expr, env: dict[str, DataType]) -> DataType:
        ty = self._type_expr_inner(expr, env)
        self._expr_types[id(expr)] = ty
        return ty

    def _type_expr_inner(self, expr: Expr, env: dict[str, DataType]) -> DataType:
        if isinstance(expr, LiteralInt):
            return DataType.INT
        if isinstance(expr, LiteralBool):
            return DataType.BOOL
        if isinstance(expr, Identifier):
            if expr.name not in env:
                raise SemanticError(
                    f"Columna desconocida: {expr.name!r}",
                    _loc_from_expr(expr),
                )
            return env[expr.name]
        if isinstance(expr, UnaryOp):
            if expr.op != UnaryOpKind.NOT:
                raise SemanticError("Operador unario no soportado", _loc_from_expr(expr))
            inner = self._type_expr(expr.operand, env)
            if inner != DataType.BOOL:
                raise SemanticError("NOT requiere subexpresión BOOL", _loc_from_expr(expr))
            return DataType.BOOL
        if isinstance(expr, BinaryOp):
            return self._type_binary(expr, env)
        raise SemanticError("Nodo de expresión inesperado", _loc_from_expr(expr))

    def _type_binary(self, expr: BinaryOp, env: dict[str, DataType]) -> DataType:
        op = expr.op
        if op in (BinaryOpKind.AND, BinaryOpKind.OR):
            lt = self._type_expr(expr.left, env)
            rt = self._type_expr(expr.right, env)
            if lt != DataType.BOOL or rt != DataType.BOOL:
                raise SemanticError(
                    f"{op.name} requiere operandos BOOL",
                    _loc_from_expr(expr),
                )
            return DataType.BOOL
        if op in (BinaryOpKind.EQ, BinaryOpKind.NE):
            lt = self._type_expr(expr.left, env)
            rt = self._type_expr(expr.right, env)
            if lt != rt:
                raise SemanticError(
                    "Comparación = o != requiere el mismo tipo en ambos lados",
                    _loc_from_expr(expr),
                )
            if lt not in (DataType.INT, DataType.BOOL):
                raise SemanticError("Tipos no comparables", _loc_from_expr(expr))
            return DataType.BOOL
        if op in (BinaryOpKind.LT, BinaryOpKind.GT, BinaryOpKind.LE, BinaryOpKind.GE):
            lt = self._type_expr(expr.left, env)
            rt = self._type_expr(expr.right, env)
            if lt != DataType.INT or rt != DataType.INT:
                raise SemanticError(
                    "Comparaciones relacionales requieren INT en ambos lados",
                    _loc_from_expr(expr),
                )
            return DataType.BOOL
        if op in (BinaryOpKind.ADD, BinaryOpKind.SUB, BinaryOpKind.MUL, BinaryOpKind.DIV):
            lt = self._type_expr(expr.left, env)
            rt = self._type_expr(expr.right, env)
            if lt != DataType.INT or rt != DataType.INT:
                raise SemanticError(
                    "Aritmética requiere INT en ambos lados",
                    _loc_from_expr(expr),
                )
            return DataType.INT
        raise SemanticError(f"Operador binario no soportado: {op}", _loc_from_expr(expr))


def _loc_from_stmt(stmt: CreateTable | Insert | Select) -> SourceLocation | None:
    if stmt.span is None:
        return None
    return SourceLocation(stmt.span.line, stmt.span.column)
