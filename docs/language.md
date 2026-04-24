# Lenguaje mini SQL-like (sqlmini)

## Tokens

Palabras clave (insensibles a mayúsculas): `CREATE`, `TABLE`, `INSERT`, `INTO`, `VALUES`, `SELECT`, `FROM`, `WHERE`, `INT`, `BOOL`, `TRUE`, `FALSE`, `AND`, `OR`, `NOT`.

Símbolos: `( ) , ; + - * / = != < > <= >=`

Identificadores: letra o `_` seguido de letras, dígitos o `_`.

Literales enteros: secuencia de dígitos decimales.

## Gramática (EBNF)

```ebnf
program        ::= statement*
statement      ::= create_table | insert | select

create_table   ::= "CREATE" "TABLE" ident "(" column_defs ")" ";"
column_defs    ::= column_def ( "," column_def )*
column_def     ::= ident type
type           ::= "INT" | "BOOL"

insert         ::= "INSERT" "INTO" ident "VALUES" "(" literals ")" ";"
literals       ::= literal ( "," literal )*
literal        ::= integer | "TRUE" | "FALSE"

select         ::= "SELECT" expr_list "FROM" ident where_opt ";"
expr_list      ::= expr ( "," expr )*
where_opt      ::= ε | "WHERE" expr

expr           ::= or_expr
or_expr        ::= and_expr ( "OR" and_expr )*
and_expr       ::= eq_expr ( "AND" eq_expr )*
eq_expr        ::= rel_expr ( ( "=" | "!=" ) rel_expr )*
rel_expr       ::= add_expr ( ( "<" | ">" | "<=" | ">=" ) add_expr )*
add_expr       ::= mul_expr ( ( "+" | "-" ) mul_expr )*
mul_expr       ::= unary ( ( "*" | "/" ) unary )*
unary          ::= "NOT" unary | primary
primary        ::= literal | ident | "(" expr ")"
```

## Semántica (resumen)

- El catálogo guarda tablas y columnas con tipo `INT` o `BOOL`.
- `INSERT` exige el mismo número de valores que columnas y tipos compatibles.
- En `SELECT` / `WHERE`, `ident` se resuelve como columna de la tabla del `FROM`.
- `NOT`, `AND`, `OR` requieren subexpresiones booleanas.
- Aritmética (`+ - * /`) solo sobre `INT`. Division entera.
- Comparaciones `< > <= >=` solo entre `INT`. `=` y `!=` entre `INT` o entre `BOOL`.

## Ejemplos válidos

Ver `examples/valid.sql`.

## Ejemplos inválidos

Ver `examples/invalid.sql` (comentarios explican el error esperado).
