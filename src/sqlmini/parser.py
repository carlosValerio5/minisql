"""
Analizador sintáctico por descenso recursivo para sqlmini.

Construye el AST a partir de la lista de tokens emitida por el lexer.
"""

from __future__ import annotations

from sqlmini.ast import (
    BinaryOp,
    BinaryOpKind,
    CreateTable,
    DataType,
    Expr,
    Identifier,
    Insert,
    LiteralBool,
    LiteralInt,
    Program,
    Select,
    SourceSpan,
    Statement,
    UnaryOp,
    UnaryOpKind,
)
from sqlmini.errors import ParseError, SourceLocation
from sqlmini.tokens import Token, TokenKind


def parse(tokens: list[Token]) -> Program:
    """
    Parsea la lista de tokens y devuelve el AST del programa.

    Args:
        tokens: Secuencia terminada en ``EOF``.

    Returns:
        Nodo ``Program`` raíz.

    Raises:
        ParseError: Si la estructura no coincide con la gramática.
    """
    p = _Parser(tokens)
    return p.parse_program()


def _span(tok: Token) -> SourceSpan:
    """Obtiene la posición en fuente a partir de un token."""
    return SourceSpan(line=tok.line, column=tok.column)


class _Parser:
    """Estado mutable del parser sobre un buffer de tokens."""

    def __init__(self, tokens: list[Token]) -> None:
        """Inicializa el cursor al inicio del buffer de tokens."""
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token:
        """Devuelve el token actual sin consumirlo."""
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        """Consume y devuelve el token actual."""
        tok = self._peek()
        if tok.kind != TokenKind.EOF:
            self._pos += 1
        return tok

    def _expect(self, kind: TokenKind, message: str | None = None) -> Token:
        """Consume el token actual si su categoría coincide; si no, lanza error."""
        tok = self._peek()
        if tok.kind != kind:
            loc = SourceLocation(tok.line, tok.column)
            msg = message or f"Se esperaba {kind.name}, se obtuvo {tok.kind.name} ({tok.lexeme!r})"
            raise ParseError(msg, loc)
        return self._advance()

    def parse_program(self) -> Program:
        """Parsea ``program`` hasta ``EOF`` y construye el AST raíz."""
        stmts: list[Statement] = []
        while self._peek().kind != TokenKind.EOF:
            stmts.append(self._parse_statement())
        return Program(statements=stmts)

    def _parse_statement(self) -> Statement:
        """Despacha una sentencia según el token inicial."""
        tok = self._peek()
        if tok.kind == TokenKind.CREATE:
            return self._parse_create_table()
        if tok.kind == TokenKind.INSERT:
            return self._parse_insert()
        if tok.kind == TokenKind.SELECT:
            return self._parse_select()
        loc = SourceLocation(tok.line, tok.column)
        raise ParseError(
            "Sentencia no válida: se esperaba CREATE, INSERT o SELECT",
            loc,
        )

    def _parse_create_table(self) -> CreateTable:
        self._expect(TokenKind.CREATE)
        self._expect(TokenKind.TABLE)
        name_tok = self._expect(TokenKind.IDENT)
        self._expect(TokenKind.LPAREN)
        columns: list[tuple[str, DataType]] = []
        columns.append(self._parse_column_def())
        while self._peek().kind == TokenKind.COMMA:
            self._advance()
            columns.append(self._parse_column_def())
        self._expect(TokenKind.RPAREN)
        self._expect(TokenKind.SEMI)
        return CreateTable(name=name_tok.lexeme, columns=columns, span=_span(name_tok))

    def _parse_column_def(self) -> tuple[str, DataType]:
        name_tok = self._expect(TokenKind.IDENT)
        dt = self._parse_type()
        return (name_tok.lexeme, dt)

    def _parse_type(self) -> DataType:
        tok = self._peek()
        if tok.kind == TokenKind.INT:
            self._advance()
            return DataType.INT
        if tok.kind == TokenKind.BOOL:
            self._advance()
            return DataType.BOOL
        loc = SourceLocation(tok.line, tok.column)
        raise ParseError("Se esperaba tipo INT o BOOL", loc)

    def _parse_insert(self) -> Insert:
        start = self._expect(TokenKind.INSERT)
        self._expect(TokenKind.INTO)
        table_tok = self._expect(TokenKind.IDENT)
        self._expect(TokenKind.VALUES)
        self._expect(TokenKind.LPAREN)
        values: list[LiteralInt | LiteralBool] = [self._parse_literal_const()]
        while self._peek().kind == TokenKind.COMMA:
            self._advance()
            values.append(self._parse_literal_const())
        self._expect(TokenKind.RPAREN)
        self._expect(TokenKind.SEMI)
        return Insert(table=table_tok.lexeme, values=values, span=_span(start))

    def _parse_literal_const(self) -> LiteralInt | LiteralBool:
        tok = self._peek()
        if tok.kind == TokenKind.INTEGER:
            self._advance()
            return LiteralInt(value=int(tok.lexeme), span=_span(tok))
        if tok.kind == TokenKind.TRUE:
            self._advance()
            return LiteralBool(value=True, span=_span(tok))
        if tok.kind == TokenKind.FALSE:
            self._advance()
            return LiteralBool(value=False, span=_span(tok))
        loc = SourceLocation(tok.line, tok.column)
        raise ParseError("Se esperaba literal entero o booleano", loc)

    def _parse_select(self) -> Select:
        start = self._expect(TokenKind.SELECT)
        projections: list[Expr] = [self._parse_expr()]
        while self._peek().kind == TokenKind.COMMA:
            self._advance()
            projections.append(self._parse_expr())
        self._expect(TokenKind.FROM)
        table_tok = self._expect(TokenKind.IDENT)
        where_expr: Expr | None = None
        if self._peek().kind == TokenKind.WHERE:
            self._advance()
            where_expr = self._parse_expr()
        self._expect(TokenKind.SEMI)
        return Select(
            projections=projections,
            table=table_tok.lexeme,
            where=where_expr,
            span=_span(start),
        )

    def _parse_expr(self) -> Expr:
        return self._parse_or()

    def _parse_or(self) -> Expr:
        left = self._parse_and()
        while self._peek().kind == TokenKind.OR:
            op_tok = self._advance()
            right = self._parse_and()
            left = BinaryOp(
                op=BinaryOpKind.OR,
                left=left,
                right=right,
                span=_span(op_tok),
            )
        return left

    def _parse_and(self) -> Expr:
        left = self._parse_eq()
        while self._peek().kind == TokenKind.AND:
            op_tok = self._advance()
            right = self._parse_eq()
            left = BinaryOp(
                op=BinaryOpKind.AND,
                left=left,
                right=right,
                span=_span(op_tok),
            )
        return left

    def _parse_eq(self) -> Expr:
        left = self._parse_rel()
        while True:
            tok = self._peek()
            if tok.kind == TokenKind.EQ:
                self._advance()
                right = self._parse_rel()
                left = BinaryOp(BinaryOpKind.EQ, left, right, _span(tok))
            elif tok.kind == TokenKind.NE:
                self._advance()
                right = self._parse_rel()
                left = BinaryOp(BinaryOpKind.NE, left, right, _span(tok))
            else:
                break
        return left

    def _parse_rel(self) -> Expr:
        left = self._parse_add()
        while True:
            tok = self._peek()
            kind: BinaryOpKind | None = None
            if tok.kind == TokenKind.LT:
                kind = BinaryOpKind.LT
            elif tok.kind == TokenKind.GT:
                kind = BinaryOpKind.GT
            elif tok.kind == TokenKind.LE:
                kind = BinaryOpKind.LE
            elif tok.kind == TokenKind.GE:
                kind = BinaryOpKind.GE
            else:
                break
            self._advance()
            right = self._parse_add()
            left = BinaryOp(kind, left, right, _span(tok))
        return left

    def _parse_add(self) -> Expr:
        left = self._parse_mul()
        while True:
            tok = self._peek()
            if tok.kind == TokenKind.PLUS:
                self._advance()
                right = self._parse_mul()
                left = BinaryOp(BinaryOpKind.ADD, left, right, _span(tok))
            elif tok.kind == TokenKind.MINUS:
                self._advance()
                right = self._parse_mul()
                left = BinaryOp(BinaryOpKind.SUB, left, right, _span(tok))
            else:
                break
        return left

    def _parse_mul(self) -> Expr:
        left = self._parse_unary()
        while True:
            tok = self._peek()
            if tok.kind == TokenKind.STAR:
                self._advance()
                right = self._parse_unary()
                left = BinaryOp(BinaryOpKind.MUL, left, right, _span(tok))
            elif tok.kind == TokenKind.SLASH:
                self._advance()
                right = self._parse_unary()
                left = BinaryOp(BinaryOpKind.DIV, left, right, _span(tok))
            else:
                break
        return left

    def _parse_unary(self) -> Expr:
        tok = self._peek()
        if tok.kind == TokenKind.NOT:
            self._advance()
            operand = self._parse_unary()
            return UnaryOp(UnaryOpKind.NOT, operand, _span(tok))
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        tok = self._peek()
        if tok.kind == TokenKind.INTEGER:
            self._advance()
            return LiteralInt(int(tok.lexeme), _span(tok))
        if tok.kind == TokenKind.TRUE:
            self._advance()
            return LiteralBool(True, _span(tok))
        if tok.kind == TokenKind.FALSE:
            self._advance()
            return LiteralBool(False, _span(tok))
        if tok.kind == TokenKind.IDENT:
            self._advance()
            return Identifier(tok.lexeme, _span(tok))
        if tok.kind == TokenKind.LPAREN:
            self._advance()
            inner = self._parse_expr()
            self._expect(TokenKind.RPAREN)
            return inner
        loc = SourceLocation(tok.line, tok.column)
        raise ParseError("Se esperaba expresión (literal, identificador o '(')", loc)
