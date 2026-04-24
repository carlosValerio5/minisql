"""
Paquete principal del compilador mini SQL-like (sqlmini).

Expone la tubería de alto nivel: tokenización, parseo, análisis semántico,
generación de TAC, optimización y ejecución opcional sobre un almacén en memoria.
"""

from sqlmini.errors import LexicalError, ParseError, SemanticError, SqlMiniError
from sqlmini.lexer import lex
from sqlmini.parser import parse
from sqlmini.semantic import analyze

__all__ = [
    "LexicalError",
    "ParseError",
    "SemanticError",
    "SqlMiniError",
    "analyze",
    "lex",
    "parse",
]
