"""
Definición del árbol de sintaxis abstracta (AST) del lenguaje sqlmini.

Los nodos son dataclasses inmutables salvo listas internas de hijos compartidos
solo en construcción; el análisis semántico no las modifica in-place.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto


class DataType(Enum):
    """Tipos escalares del lenguaje."""

    INT = auto()
    BOOL = auto()


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Fragmento de fuente asociado a un nodo para diagnósticos."""

    line: int
    column: int


class Node(ABC):
    """Nodo base del AST con visita genérica."""

    span: SourceSpan | None

    @abstractmethod
    def accept(self, visitor: ASTVisitor) -> None:
        """Delega la visita al patrón visitor."""
        raise NotImplementedError


class ASTVisitor(ABC):
    """Contrato mínimo de visita sobre el AST."""

    @abstractmethod
    def visit_program(self, node: Program) -> None:
        """Visita el nodo raíz ``Program``."""
        raise NotImplementedError

    @abstractmethod
    def visit_create_table(self, node: CreateTable) -> None:
        """Visita una sentencia ``CREATE TABLE``."""
        raise NotImplementedError

    @abstractmethod
    def visit_insert(self, node: Insert) -> None:
        """Visita una sentencia ``INSERT``."""
        raise NotImplementedError

    @abstractmethod
    def visit_select(self, node: Select) -> None:
        """Visita una sentencia ``SELECT``."""
        raise NotImplementedError

    @abstractmethod
    def visit_identifier(self, node: Identifier) -> None:
        """Visita un identificador (columna)."""
        raise NotImplementedError

    @abstractmethod
    def visit_literal_int(self, node: LiteralInt) -> None:
        """Visita un literal entero."""
        raise NotImplementedError

    @abstractmethod
    def visit_literal_bool(self, node: LiteralBool) -> None:
        """Visita un literal booleano."""
        raise NotImplementedError

    @abstractmethod
    def visit_unary(self, node: UnaryOp) -> None:
        """Visita una expresión unaria."""
        raise NotImplementedError

    @abstractmethod
    def visit_binary(self, node: BinaryOp) -> None:
        """Visita una expresión binaria."""
        raise NotImplementedError


@dataclass
class Program(Node):
    """Raíz: secuencia de sentencias."""

    statements: list[Statement]
    span: SourceSpan | None = None

    def accept(self, visitor: ASTVisitor) -> None:
        visitor.visit_program(self)


type Statement = CreateTable | Insert | Select
type Expr = Identifier | LiteralInt | LiteralBool | UnaryOp | BinaryOp


@dataclass
class CreateTable(Node):
    """Sentencia CREATE TABLE."""

    name: str
    columns: list[tuple[str, DataType]]
    span: SourceSpan | None = None

    def accept(self, visitor: ASTVisitor) -> None:
        visitor.visit_create_table(self)


@dataclass
class Insert(Node):
    """Sentencia INSERT INTO ... VALUES (...)."""

    table: str
    values: list[LiteralInt | LiteralBool]
    span: SourceSpan | None = None

    def accept(self, visitor: ASTVisitor) -> None:
        visitor.visit_insert(self)


@dataclass
class Select(Node):
    """Sentencia SELECT ... FROM ... [WHERE ...]."""

    projections: list[Expr]
    table: str
    where: Expr | None
    span: SourceSpan | None = None

    def accept(self, visitor: ASTVisitor) -> None:
        visitor.visit_select(self)


@dataclass
class Identifier(Node):
    """Referencia a identificador (nombre de columna en expresiones)."""

    name: str
    span: SourceSpan | None = None

    def accept(self, visitor: ASTVisitor) -> None:
        visitor.visit_identifier(self)


@dataclass
class LiteralInt(Node):
    """Literal entero."""

    value: int
    span: SourceSpan | None = None

    def accept(self, visitor: ASTVisitor) -> None:
        visitor.visit_literal_int(self)


@dataclass
class LiteralBool(Node):
    """Literal booleano."""

    value: bool
    span: SourceSpan | None = None

    def accept(self, visitor: ASTVisitor) -> None:
        visitor.visit_literal_bool(self)


class UnaryOpKind(Enum):
    """Operadores unarios en expresiones."""

    NOT = auto()


@dataclass
class UnaryOp(Node):
    """Expresión unaria."""

    op: UnaryOpKind
    operand: Expr
    span: SourceSpan | None = None

    def accept(self, visitor: ASTVisitor) -> None:
        visitor.visit_unary(self)


class BinaryOpKind(Enum):
    """Operadores binarios en expresiones."""

    OR = auto()
    AND = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()


@dataclass
class BinaryOp(Node):
    """Expresión binaria."""

    op: BinaryOpKind
    left: Expr
    right: Expr
    span: SourceSpan | None = None

    def accept(self, visitor: ASTVisitor) -> None:
        visitor.visit_binary(self)


def walk_expr(visitor: ASTVisitor, expr: Expr) -> None:
    """
    Recorre un subárbol de expresión en preorden aplicando el visitor.

    Args:
        visitor: Visitor con métodos de nodo.
        expr: Raíz de la expresión.
    """
    expr.accept(visitor)
    if isinstance(expr, UnaryOp):
        walk_expr(visitor, expr.operand)
    elif isinstance(expr, BinaryOp):
        walk_expr(visitor, expr.left)
        walk_expr(visitor, expr.right)
