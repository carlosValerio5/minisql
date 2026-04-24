"""Pruebas del intérprete en memoria."""

from sqlmini.interp import run_program
from sqlmini.lexer import lex
from sqlmini.parser import parse
from sqlmini.semantic import analyze


def test_run_select_filter() -> None:
    src = """
    CREATE TABLE t ( id INT, ok BOOL );
    INSERT INTO t VALUES ( 1, true );
    INSERT INTO t VALUES ( 2, false );
    SELECT id FROM t WHERE ok = true;
    """
    bundle = analyze(parse(lex(src)))
    out = run_program(bundle, optimize=True)
    assert out.strip() == "1"
