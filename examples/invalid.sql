-- Error semántico: arity distinta
-- Falla en la fase de semantic analysis.
CREATE TABLE t ( a INT );
INSERT INTO t VALUES ( 1, 2 );

-- Error sintáctico: falta punto y coma
-- Falla en la fase de parsing.
SELECT a FROM t

-- Error léxico (si se usa): caracter no permitido sería detectado en escaneo
-- Falla en la fase de lexing.
SELECT @ FROM t;

-- Orden de ejecucion:
-- 1. Lexing
-- 2. Parsing
-- 3. Semantic analysis

-- Los errores se deben reportar en la fase en que ocurren.