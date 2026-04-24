# sqlmini — compilador mini SQL-like (PIA Compiladores)

Subconjunto declarativo tipo SQL con `CREATE TABLE`, `INSERT` y `SELECT` (con `WHERE` y expresiones). Incluye lexer, parser recursivo, AST, análisis semántico, generación de TAC, optimización básica (constantes + DCE) e intérprete en memoria.

## Requisitos

- Python 3.13+

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Con Pipenv: `pipenv install --dev`.

## Uso

```bash
sqlmini examples/valid.sql --dump-ast
sqlmini examples/valid.sql --dump-tac
sqlmini examples/valid.sql --run
```

Opciones:

- `--no-opt`: desactiva optimización de TAC.
- Sin flags adicionales: solo comprueba lex + parse + semántica.

La gramática y los tokens están descritos en [docs/language.md](docs/language.md).

## Pruebas

```bash
pytest tests/ -q
```

## Estructura

- `src/sqlmini/` — compilador (lexer, parser, AST, semántica, TAC, `optimize`, `interp`, CLI).
- `tests/` — pytest.
- `examples/` — programas de ejemplo.
