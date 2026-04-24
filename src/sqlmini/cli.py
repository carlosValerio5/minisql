"""
Interfaz de línea de comandos para compilar y ejecutar programas sqlmini.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlmini.ast_dump import format_ast
from sqlmini.errors import SqlMiniError
from sqlmini.interp import dump_tac_for_program, run_program
from sqlmini.lexer import lex
from sqlmini.parser import parse
from sqlmini.semantic import analyze


def main(argv: list[str] | None = None) -> int:
    """
    Punto de entrada del ejecutable ``sqlmini``.

    Args:
        argv: Argumentos (por defecto ``sys.argv[1:]``).

    Returns:
        Código de salida del proceso (0 éxito, distinto de 0 error).
    """
    if argv is None:
        argv = sys.argv[1:]
    p = argparse.ArgumentParser(prog="sqlmini", description="Compilador mini SQL-like (PIA).")
    p.add_argument("path", type=Path, help="Archivo fuente .sql")
    p.add_argument("--dump-ast", action="store_true", help="Imprime el AST y termina.")
    p.add_argument(
        "--dump-tac",
        action="store_true",
        help="Imprime TAC (opcionalmente optimizado salvo --no-opt).",
    )
    p.add_argument("--no-opt", action="store_true", help="Desactiva optimización de TAC.")
    p.add_argument(
        "--run",
        action="store_true",
        help="Ejecuta SELECT en memoria e imprime filas resultantes.",
    )
    args = p.parse_args(argv)

    src = args.path.read_text(encoding="utf-8")
    use_opt = not args.no_opt
    try:
        tokens = lex(src)
        program = parse(tokens)
        bundle = analyze(program)
    except SqlMiniError as e:
        print(str(e), file=sys.stderr)
        return 1

    if args.dump_ast:
        print(format_ast(program))
    if args.dump_tac:
        print(dump_tac_for_program(bundle, optimize=use_opt))
    if args.run:
        print(run_program(bundle, optimize=use_opt))
    if not args.dump_ast and not args.dump_tac and not args.run:
        print("Compilación correcta. Use --dump-ast, --dump-tac o --run.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
