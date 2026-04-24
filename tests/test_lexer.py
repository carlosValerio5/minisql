"""Pruebas del analizador léxico."""

from sqlmini.errors import LexicalError
from sqlmini.lexer import lex
from sqlmini.tokens import TokenKind


def test_keywords_case_insensitive() -> None:
    toks = lex("create TaBlE x ( a int );")
    kinds = [t.kind for t in toks[:-1]]
    assert kinds[:6] == [
        TokenKind.CREATE,
        TokenKind.TABLE,
        TokenKind.IDENT,
        TokenKind.LPAREN,
        TokenKind.IDENT,
        TokenKind.INT,
    ]


def test_operators_and_literals() -> None:
    toks = lex("a != 1 <= 2 >= 3 < 4 > 5")
    kinds = [t.kind for t in toks[:-1]]
    assert kinds == [
        TokenKind.IDENT,
        TokenKind.NE,
        TokenKind.INTEGER,
        TokenKind.LE,
        TokenKind.INTEGER,
        TokenKind.GE,
        TokenKind.INTEGER,
        TokenKind.LT,
        TokenKind.INTEGER,
        TokenKind.GT,
        TokenKind.INTEGER,
    ]


def test_comment_skipped() -> None:
    toks = lex("-- hola\nSELECT 1;")
    assert [t.kind for t in toks[:-1]] == [TokenKind.SELECT, TokenKind.INTEGER, TokenKind.SEMI]


def test_lexical_error_on_bad_char() -> None:
    try:
        lex("SELECT @")
    except LexicalError as e:
        assert "@" in e.message
    else:
        raise AssertionError("expected LexicalError")
