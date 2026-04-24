"""
Analizador léxico del lenguaje sqlmini.

Convierte texto fuente en una secuencia de tokens usando descenso lineal y
reconocimiento de palabras clave insensible a mayúsculas.
"""

from __future__ import annotations

from sqlmini.errors import LexicalError, SourceLocation
from sqlmini.tokens import Token, TokenKind

_KEYWORDS: dict[str, TokenKind] = {
    "CREATE": TokenKind.CREATE,
    "TABLE": TokenKind.TABLE,
    "INSERT": TokenKind.INSERT,
    "INTO": TokenKind.INTO,
    "VALUES": TokenKind.VALUES,
    "SELECT": TokenKind.SELECT,
    "FROM": TokenKind.FROM,
    "WHERE": TokenKind.WHERE,
    "INT": TokenKind.INT,
    "BOOL": TokenKind.BOOL,
    "TRUE": TokenKind.TRUE,
    "FALSE": TokenKind.FALSE,
    "AND": TokenKind.AND,
    "OR": TokenKind.OR,
    "NOT": TokenKind.NOT,
}


def lex(source: str) -> list[Token]:
    """
    Tokeniza la cadena fuente completa y devuelve la lista de tokens más EOF.

    Args:
        source: Programa sqlmini como texto.

    Returns:
        Lista ordenada de tokens terminada en ``TokenKind.EOF``.

    Raises:
        LexicalError: Si aparece un carácter no permitido o lexema mal formado.
    """
    tokens: list[Token] = []
    i = 0
    line = 1
    column = 1
    n = len(source)

    def advance() -> None:
        nonlocal i, line, column
        if i < n and source[i] == "\n":
            line += 1
            column = 1
        else:
            column += 1
        i += 1

    while i < n:
        ch = source[i]
        if ch in " \t\r\n":
            advance()
            continue
        if ch == "-" and i + 1 < n and source[i + 1] == "-":
            while i < n and source[i] != "\n":
                advance()
            continue
        start_line, start_col = line, column

        def emit(
            kind: TokenKind,
            lexeme: str,
            *,
            line_tok: int = start_line,
            col_tok: int = start_col,
        ) -> None:
            """Añade un token fijando línea y columna del inicio del lexema."""
            tokens.append(Token(kind=kind, lexeme=lexeme, line=line_tok, column=col_tok))

        if ch.isalpha() or ch == "_":
            start = i
            while i < n and (source[i].isalnum() or source[i] == "_"):
                advance()
            lexeme = source[start:i]
            upper = lexeme.upper()
            kind = _KEYWORDS.get(upper, TokenKind.IDENT)
            emit(kind, lexeme)
            continue

        if ch.isdigit():
            start = i
            while i < n and source[i].isdigit():
                advance()
            emit(TokenKind.INTEGER, source[start:i])
            continue

        if ch == "(":
            advance()
            emit(TokenKind.LPAREN, "(")
            continue
        if ch == ")":
            advance()
            emit(TokenKind.RPAREN, ")")
            continue
        if ch == ",":
            advance()
            emit(TokenKind.COMMA, ",")
            continue
        if ch == ";":
            advance()
            emit(TokenKind.SEMI, ";")
            continue
        if ch == "+":
            advance()
            emit(TokenKind.PLUS, "+")
            continue
        if ch == "-":
            advance()
            emit(TokenKind.MINUS, "-")
            continue
        if ch == "*":
            advance()
            emit(TokenKind.STAR, "*")
            continue
        if ch == "/":
            advance()
            emit(TokenKind.SLASH, "/")
            continue
        if ch == "=":
            advance()
            emit(TokenKind.EQ, "=")
            continue
        if ch == "!" and i + 1 < n and source[i + 1] == "=":
            advance()
            advance()
            emit(TokenKind.NE, "!=")
            continue
        if ch == "<" and i + 1 < n and source[i + 1] == "=":
            advance()
            advance()
            emit(TokenKind.LE, "<=")
            continue
        if ch == ">" and i + 1 < n and source[i + 1] == "=":
            advance()
            advance()
            emit(TokenKind.GE, ">=")
            continue
        if ch == "<":
            advance()
            emit(TokenKind.LT, "<")
            continue
        if ch == ">":
            advance()
            emit(TokenKind.GT, ">")
            continue

        bad = SourceLocation(line=line, column=column)
        raise LexicalError(f"Carácter no reconocido: {ch!r}", bad)

    tokens.append(Token(kind=TokenKind.EOF, lexeme="", line=line, column=column))
    return tokens
