"""
Modelo de tabla de símbolos para el catálogo de tablas y columnas.

Representa el esquema conocido tras las sentencias ``CREATE TABLE`` procesadas
en orden dentro del mismo programa.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmini.ast import DataType


@dataclass(frozen=True, slots=True)
class TableSchema:
    """
    Esquema de una tabla: nombre y columnas ordenadas con su tipo.

    Attributes:
        name: Nombre de la tabla.
        columns: Lista de pares (nombre_columna, tipo).
    """

    name: str
    columns: list[tuple[str, DataType]]

    def column_index(self, col: str) -> int | None:
        """
        Devuelve el índice de la columna por nombre o None si no existe.

        Args:
            col: Nombre buscado.

        Returns:
            Índice base cero o None.
        """
        for i, (n, _) in enumerate(self.columns):
            if n == col:
                return i
        return None

    def types_by_name(self) -> dict[str, DataType]:
        """Construye un mapa nombre de columna -> tipo."""
        return {n: t for n, t in self.columns}
