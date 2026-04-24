"""Pruebas del análisis semántico."""

import pytest

from sqlmini.errors import SemanticError
from sqlmini.lexer import lex
from sqlmini.parser import parse
from sqlmini.semantic import analyze


def test_semantic_ok() -> None:
    src = """
    CREATE TABLE t ( x INT );
    INSERT INTO t VALUES ( 42 );
    SELECT x FROM t;
    """
    analyze(parse(lex(src)))


def test_duplicate_table() -> None:
    src = "CREATE TABLE t ( a INT ); CREATE TABLE t ( b INT );"
    with pytest.raises(SemanticError, match="ya está definida"):
        analyze(parse(lex(src)))


def test_insert_wrong_arity() -> None:
    src = "CREATE TABLE t ( a INT ); INSERT INTO t VALUES ( 1, 2 );"
    with pytest.raises(SemanticError, match="INSERT"):
        analyze(parse(lex(src)))


def test_unknown_column_in_select() -> None:
    src = "CREATE TABLE t ( a INT ); SELECT z FROM t;"
    with pytest.raises(SemanticError, match="Columna desconocida"):
        analyze(parse(lex(src)))
