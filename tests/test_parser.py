"""Pruebas del parser y construcción del AST."""

import pytest

from sqlmini.ast import CreateTable, DataType, Insert, LiteralInt, Select
from sqlmini.errors import ParseError
from sqlmini.lexer import lex
from sqlmini.parser import parse


def test_parse_create_insert_select() -> None:
    src = """
    CREATE TABLE t ( a INT, b BOOL );
    INSERT INTO t VALUES ( 1, true );
    SELECT a + 1, b FROM t WHERE a > 0;
    """
    prog = parse(lex(src))
    assert len(prog.statements) == 3
    ct = prog.statements[0]
    assert isinstance(ct, CreateTable)
    assert ct.name == "t"
    assert ct.columns == [("a", DataType.INT), ("b", DataType.BOOL)]
    ins = prog.statements[1]
    assert isinstance(ins, Insert)
    assert ins.table == "t"
    assert len(ins.values) == 2
    assert isinstance(ins.values[0], LiteralInt)
    sel = prog.statements[2]
    assert isinstance(sel, Select)
    assert sel.table == "t"
    assert sel.where is not None
    assert len(sel.projections) == 2


def test_parse_error_missing_semi() -> None:
    with pytest.raises(ParseError):
        parse(lex("SELECT 1 FROM t"))
