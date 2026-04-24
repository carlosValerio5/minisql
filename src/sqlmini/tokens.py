"""
Definición de categorías léxicas (tokens) del lenguaje sqlmini.

Las palabras clave se normalizan a mayúsculas en el lexer para simplificar el parser.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    """Conjunto de categorías léxicas reconocidas por el compilador."""

    CREATE = auto()
    TABLE = auto()
    INSERT = auto()
    INTO = auto()
    VALUES = auto()
    SELECT = auto()
    FROM = auto()
    WHERE = auto()
    INT = auto()
    BOOL = auto()
    TRUE = auto()
    FALSE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    IDENT = auto()
    INTEGER = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    SEMI = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    """Instancia concreta de token con lexema y posición en fuente."""

    kind: TokenKind
    lexeme: str
    line: int
    column: int
