"""
semantic.py  –  Semantic Analyzer for C-like token streams
===========================================================
Takes the flat token list from lexer.py and checks for semantic errors.

Checks performed:
  1. Undeclared variable  –  identifier used before it was declared
  2. Type mismatch        –  wrong value type assigned to a variable

Supported statement forms:
  int a;                –  declaration
  int a = 10;           –  declaration + initialization
  int sum = a + b;      –  declaration + expression initializer
  a = 5;                –  assignment
  a = x + 20;           –  assignment with expression

Silently ignored:
  #include …, main(), { }, printf/scanf, return, if, while, …

Design rules:
  - Process in strict top-to-bottom order.
  - Never stop early — collect ALL errors.
  - Do NOT evaluate expressions; only check variable existence.

Returns:
  errors       : list of error strings
  symbol_table : dict { variable_name -> declared_type }
"""

# ──────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────

DECL_KEYWORDS = {'int', 'float', 'double', 'char'}
SKIP_KEYWORDS = {'return', 'if', 'else', 'while', 'for', 'void', 'break', 'continue'}
IGNORE_FUNCTIONS = {'printf', 'scanf', 'main'}

# Which token types are valid RHS values for each declared C type
#   NUMBER   = integer literal  42
#   FLOAT    = float literal    3.14
#   CHAR_LIT = char literal     'a'
#   STRING   = string literal   "hi"
COMPATIBLE = {
    'int':    {'NUMBER', 'IDENTIFIER'},
    'float':  {'NUMBER', 'FLOAT', 'IDENTIFIER'},
    'double': {'NUMBER', 'FLOAT', 'IDENTIFIER'},
    'char':   {'CHAR_LIT', 'STRING', 'IDENTIFIER'},
}

# Arithmetic / comparison operators — used to recognise expressions
ARITH_OPS = {'+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>='}


# ──────────────────────────────────────────────────────────────────────
# STEP 1 — Split tokens into statements
# ──────────────────────────────────────────────────────────────────────

def split_into_statements(tokens):
    """
    Break the flat token list into individual statement lists.

    - ';' closes a statement.
    - '{' and '}' are emitted as isolated single-token statements.
    - PREPROCESSOR tokens are emitted as isolated single-token statements.
    """
    statements = []
    current = []

    for tok in tokens:
        tok_type, tok_val = tok

        if tok_type == 'SYMBOL' and tok_val in ('{', '}'):
            if current:
                statements.append(current)
                current = []
            statements.append([tok])
            continue

        if tok_type == 'PREPROCESSOR':
            if current:
                statements.append(current)
                current = []
            statements.append([tok])
            continue

        current.append(tok)

        if tok_type == 'SYMBOL' and tok_val == ';':
            statements.append(current)
            current = []

    if current:
        statements.append(current)

    return statements


# ──────────────────────────────────────────────────────────────────────
# STEP 2 — Helpers
# ──────────────────────────────────────────────────────────────────────

def _find_op(stmt, op='='):
    """Return the index of the first occurrence of OPERATOR *op*, else -1."""
    for i, (t, v) in enumerate(stmt):
        if t == 'OPERATOR' and v == op:
            return i
    return -1


def _has_arith(tokens):
    """True if *tokens* contains any arithmetic / comparison operator."""
    return any(t == 'OPERATOR' and v in ARITH_OPS for t, v in tokens)


# ──────────────────────────────────────────────────────────────────────
# STEP 3 — Classify a statement
# ──────────────────────────────────────────────────────────────────────

def classify(stmt):
    """
    Return one of:
      'DECLARATION'      int a;
      'DECL_INIT'        int a = 10;
      'DECL_INIT_EXPR'   int sum = a + b;
      'ASSIGNMENT'       a = 5;
      'ASSIGNMENT_EXPR'  a = x + 20;
      'IGNORE'           everything we skip
    """
    if not stmt:
        return 'IGNORE'

    first_type, first_val = stmt[0]

    # Noise tokens
    if first_type == 'SYMBOL' and first_val in ('{', '}', ';'):
        return 'IGNORE'

    if first_type == 'PREPROCESSOR':
        return 'IGNORE'

    # Skip-keywords  (return / if / while / …)
    if first_type == 'KEYWORD' and first_val in SKIP_KEYWORDS:
        return 'IGNORE'

    # void  →  always a function definition
    if first_type == 'KEYWORD' and first_val == 'void':
        return 'IGNORE'

    # Ignored function calls / definitions
    if first_type == 'IDENTIFIER' and first_val in IGNORE_FUNCTIONS:
        return 'IGNORE'

    # Type keyword  →  declaration or initialization
    if first_type == 'KEYWORD' and first_val in DECL_KEYWORDS:
        # Has '('  →  function definition header — ignore
        if any(v == '(' for _, v in stmt):
            return 'IGNORE'

        if len(stmt) < 3:  # too short to be valid
            return 'IGNORE'

        eq_idx = _find_op(stmt, '=')
        if eq_idx == -1:
            return 'DECLARATION'  # int a;

        rhs = stmt[eq_idx + 1 : -1]  # tokens between '=' and ';'
        return 'DECL_INIT_EXPR' if _has_arith(rhs) else 'DECL_INIT'

    # Plain identifier  →  assignment
    if first_type == 'IDENTIFIER':
        eq_idx = _find_op(stmt, '=')
        if eq_idx == 1:  # IDENT = …
            rhs = stmt[eq_idx + 1 : -1]
            return 'ASSIGNMENT_EXPR' if _has_arith(rhs) else 'ASSIGNMENT'

    return 'IGNORE'


# ──────────────────────────────────────────────────────────────────────
# STEP 4 — Individual semantic checks
# ──────────────────────────────────────────────────────────────────────

def _err_undeclared(var_name, stmt_no):
    return (
        f"[Statement {stmt_no}] Undeclared variable "
        f"'{var_name}' used before declaration."
    )


def check_undeclared(var_name, symbol_table, stmt_no):
    if var_name not in symbol_table:
        return _err_undeclared(var_name, stmt_no)
    return None


def check_type_mismatch(var_name, declared_type, value_tok, symbol_table, stmt_no):
    """
    Verify that *value_tok* is compatible with *declared_type*.
    Returns an error string, or None if the types are OK.
    """
    tok_type, tok_val = value_tok
    allowed = COMPATIBLE.get(declared_type, set())

    # Direct literal match
    if tok_type in allowed:
        return None

    # RHS is an identifier — compare stored type
    if tok_type == 'IDENTIFIER':
        if tok_val not in symbol_table:
            # Undeclared — reported separately by check_expression
            return None
        rhs_type = symbol_table[tok_val]
        if rhs_type == declared_type:
            return None
        # Numeric widening / narrowing between int / float / double is OK in C
        numeric = {'int', 'float', 'double'}
        if declared_type in numeric and rhs_type in numeric:
            return None
        return (
            f"[Statement {stmt_no}] Type mismatch — "
            f"'{tok_val}' is '{rhs_type}' but "
            f"'{var_name}' is '{declared_type}'."
        )

    # Incompatible literal (e.g. NUMBER assigned to char)
    return (
        f"[Statement {stmt_no}] Type mismatch — "
        f"cannot assign {tok_type} '{tok_val}' "
        f"to '{var_name}' of type '{declared_type}'."
    )


def check_expression(rhs_tokens, symbol_table, stmt_no):
    """
    Check that every IDENTIFIER in *rhs_tokens* has been declared.
    Does NOT evaluate — existence check only.
    Returns a list of error strings (may be empty).
    """
    errors = []
    seen = set()  # avoid duplicate errors per expr

    for tok_type, tok_val in rhs_tokens:
        if tok_type != 'IDENTIFIER':
            continue
        if tok_val in DECL_KEYWORDS:  # keyword accidentally in expr
            continue
        if tok_val in seen:
            continue
        if tok_val not in symbol_table:
            errors.append(_err_undeclared(tok_val, stmt_no))
            seen.add(tok_val)

    return errors


# ──────────────────────────────────────────────────────────────────────
# STEP 5 — Main semantic analysis entry point
# ──────────────────────────────────────────────────────────────────────

def analyze(tokens):
    """
    Run semantic analysis on the token list from lexer.tokenize().

    Parameters
    ----------
    tokens : list of (str, str)   Output of lexer.tokenize().

    Returns
    -------
    errors       : list of str          All semantic errors found.
    symbol_table : dict {str -> str}    { variable_name -> declared_type }

    Design: errors are COLLECTED, never raised — the full program is
    always analysed even when earlier statements have errors.
    """
    symbol_table = {}
    errors = []

    statements = split_into_statements(tokens)

    for stmt_no, stmt in enumerate(statements, start=1):
        kind = classify(stmt)

        # ── int a; ──────────────────────────────────────────
        if kind == 'DECLARATION':
            _, var_type = stmt[0]
            _, var_name = stmt[1]
            symbol_table[var_name] = var_type

        # ── int a = 10; ─────────────────────────────────────
        elif kind == 'DECL_INIT':
            _, var_type = stmt[0]
            _, var_name = stmt[1]

            symbol_table[var_name] = var_type  # register first

            eq_idx = _find_op(stmt, '=')
            if eq_idx != -1 and eq_idx + 1 <= len(stmt) - 2:
                value_tok = stmt[eq_idx + 1]
                err = check_type_mismatch(
                    var_name, var_type, value_tok, symbol_table, stmt_no
                )
                if err:
                    errors.append(err)

        # ── int sum = a + b; ────────────────────────────────
        elif kind == 'DECL_INIT_EXPR':
            _, var_type = stmt[0]
            _, var_name = stmt[1]

            eq_idx = _find_op(stmt, '=')
            if eq_idx != -1:
                rhs = stmt[eq_idx + 1 : -1]
                # Check RHS BEFORE registering so  int a = a + 1;  is caught
                errors.extend(check_expression(rhs, symbol_table, stmt_no))

            symbol_table[var_name] = var_type  # register after RHS check

        # ── a = 5; ──────────────────────────────────────────
        elif kind == 'ASSIGNMENT':
            _, var_name = stmt[0]

            err = check_undeclared(var_name, symbol_table, stmt_no)
            if err:
                errors.append(err)
                continue  # skip type check — unknown type

            var_type = symbol_table[var_name]
            eq_idx = _find_op(stmt, '=')
            if eq_idx != -1 and eq_idx + 1 <= len(stmt) - 2:
                value_tok = stmt[eq_idx + 1]
                err = check_type_mismatch(
                    var_name, var_type, value_tok, symbol_table, stmt_no
                )
                if err:
                    errors.append(err)

        # ── a = x + 20; ─────────────────────────────────────
        elif kind == 'ASSIGNMENT_EXPR':
            _, var_name = stmt[0]

            err = check_undeclared(var_name, symbol_table, stmt_no)
            if err:
                errors.append(err)
                continue

            eq_idx = _find_op(stmt, '=')
            if eq_idx != -1:
                rhs = stmt[eq_idx + 1 : -1]
                errors.extend(check_expression(rhs, symbol_table, stmt_no))

        # ── everything else is silently skipped ─────────────

    return errors, symbol_table


# ──────────────────────────────────────────────────────────────────────
# OPTIONAL PRETTY PRINTER
# ──────────────────────────────────────────────────────────────────────

def print_results(errors, symbol_table):
    print("\n── Symbol Table ──────────────────────────────")
    if symbol_table:
        for name, typ in symbol_table.items():
            print(f"   {name:<15} : {typ}")
    else:
        print("   (empty)")

    print("\n── Semantic Errors ───────────────────────────")
    if errors:
        for e in errors:
            print(f"   ✗  {e}")
    else:
        print("   ✓  No semantic errors found.")
    print()


# ──────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from lexer import tokenize

    def run(label, code, expect_errors):
        toks = tokenize(code)
        errs, sym = analyze(toks)
        ok = bool(errs) == expect_errors
        print(f"{'✓ PASS' if ok else '✗ FAIL'}  {label}")
        for e in errs:
            print(f"       {e}")
        if sym:
            items = ', '.join(f"{k}:{v}" for k, v in sym.items())
            print(f"       symbols → {items}")
        print()

    print("=" * 60)
    print("SEMANTIC ANALYZER  –  self-tests")
    print("=" * 60)
    print()

    run("Full C program (clean)", """
        #include <stdio.h>
        int main() {
            int a = 10;
            int b = 20;
            int sum = a + b;
            a = 5;
            printf("sum = %d", sum);
            return 0;
        }
        """, expect_errors=False)

    run("Undeclared variable in expression",
        "int x = y + 1;",
        expect_errors=True)

    run("Type mismatch (NUMBER → char)",
        "char c = 42;",
        expect_errors=True)

    run("Assignment to undeclared variable",
        "z = 10;",
        expect_errors=True)

    run("Undeclared variable in assignment expression",
        "int a = 5;\na = a + undeclared;",
        expect_errors=True)