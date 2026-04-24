"""
Errores estructurados del compilador sqlmini con ubicación en fuente.

Centraliza el formato de mensajes para las fases léxica, sintáctica y semántica.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Representa una posición (línea y columna) en el texto fuente."""

    line: int
    column: int


class SqlMiniError(Exception):
    """Clase base para todos los errores reportados por sqlmini."""

    def __init__(self, message: str, location: SourceLocation | None = None) -> None:
        """
        Inicializa un error con mensaje y, opcionalmente, ubicación.

        Args:
            message: Texto explicativo del error.
            location: Posición en fuente si está disponible.
        """
        self.message = message
        self.location = location
        loc = f"{location.line}:{location.column}: " if location else ""
        super().__init__(f"{loc}{message}")


class LexicalError(SqlMiniError):
    """Error detectado durante el análisis léxico (carácter o lexema inválido)."""


class ParseError(SqlMiniError):
    """Error detectado durante el análisis sintáctico (regla o token inesperado)."""


class SemanticError(SqlMiniError):
    """Error detectado durante el análisis semántico (tipos, símbolos o reglas)."""
