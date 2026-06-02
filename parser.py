"""
syntax_analyzer.py  –  Syntax Analyzer for C-like token streams
=================================================================
Takes the flat token list from lexer.py and checks for syntax errors.

Checks performed:
  1. Missing semicolon       –  statement does not end with ';'
  2. Invalid assignment      –  nothing, or a bad token, after '='
  3. Invalid declaration     –  type keyword followed by a non-identifier
                                 (catches things like:  int 5;  int +x;)

Design rules:
  - Process statements in top-to-bottom order.
  - NEVER stop on the first error — collect ALL errors and return them.
  - Ignore:  #include, main(), { }, printf/scanf, return.

Returns:
  list of error strings  (empty list = no syntax errors)
"""

# ──────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────

# Type keywords that open a variable declaration
DECL_KEYWORDS = {'int', 'float', 'char', 'double'}

# Keywords that can open a statement but need no further syntax check
SKIP_KEYWORDS = {'return', 'if', 'else', 'while', 'for', 'void', 'break', 'continue'}

# Function names whose call statements we silently ignore
IGNORE_FUNCTIONS = {'printf', 'scanf', 'main'}

# Token types that are legal on the RIGHT side of '='
VALID_RHS_TYPES = {'NUMBER', 'FLOAT', 'STRING', 'CHAR_LIT', 'IDENTIFIER'}


# ──────────────────────────────────────────────────────────────────────
# STEP 1 — Split tokens into statements
# ──────────────────────────────────────────────────────────────────────

def split_into_statements(tokens):
    """
    Group the flat token list into individual statements.

    Rules:
      - A statement ends at ';'  (the ';' is included in the statement).
      - '{' and '}' are emitted as their own single-token statements.
      - If a DECL_KEYWORD appears while a statement is already building,
        the previous (semicolon-less) statement is saved first.
        This lets us detect missing semicolons even when two declarations
        run together:  int x = 10  int y = 20;
    """
    statements = []
    current = []

    for tok in tokens:
        tok_type, tok_val = tok

        # Braces are structural — flush and emit alone
        if tok_type == 'SYMBOL' and tok_val in ('{', '}'):
            if current:
                statements.append(current)
                current = []
            statements.append([tok])
            continue

        # Preprocessor lines are flushed as a single statement
        if tok_type == 'PREPROCESSOR':
            if current:
                statements.append(current)
                current = []
            statements.append([tok])
            continue

        # A declaration keyword while something is already being built
        # means the previous statement forgot its semicolon
        if tok_type == 'KEYWORD' and tok_val in DECL_KEYWORDS and current:
            statements.append(current)  # save the incomplete statement
            current = []

        current.append(tok)

        if tok_type == 'SYMBOL' and tok_val == ';':
            statements.append(current)
            current = []

    if current:
        statements.append(current)

    return statements


# ──────────────────────────────────────────────────────────────────────
# STEP 2 — Decide whether to skip a statement
# ──────────────────────────────────────────────────────────────────────

def should_ignore(stmt):
    """
    Return True for statements we do not need to syntax-check:
      - empty / single brace
      - preprocessor lines
      - skip-keywords (return, if, while, …)
      - known function calls (printf, scanf, main definition)
    """
    if not stmt:
        return True

    first_type, first_val = stmt[0]

    if first_type == 'SYMBOL' and first_val in ('{', '}'):
        return True

    if first_type == 'PREPROCESSOR':
        return True

    if first_type == 'KEYWORD' and first_val in SKIP_KEYWORDS:
        return True

    # void something(  →  function definition header
    if first_type == 'KEYWORD' and first_val == 'void':
        return True

    # Function call or function definition that starts with an identifier
    if first_type == 'IDENTIFIER' and first_val in IGNORE_FUNCTIONS:
        return True

    # Type keyword followed by an identifier followed by '('  →  function def
    if first_type == 'KEYWORD' and first_val in DECL_KEYWORDS:
        if any(v == '(' for _, v in stmt):
            return True

    return False


# ──────────────────────────────────────────────────────────────────────
# STEP 3 — Individual syntax checks
# ──────────────────────────────────────────────────────────────────────

def check_missing_semicolon(stmt, stmt_no):
    """
    Return an error string if the statement does not end with ';'.
    Statements ending with '{' or '}' are already filtered by should_ignore.
    """
    last_type, last_val = stmt[-1]
    if not (last_type == 'SYMBOL' and last_val == ';'):
        snippet = ' '.join(v for _, v in stmt)
        return (
            f"[Statement {stmt_no}] Missing semicolon ';' "
            f"→  {snippet}"
        )
    return None


def check_invalid_declaration(stmt, stmt_no):
    """
    A declaration must look like:   TYPE IDENTIFIER …
    Flag it when the token immediately after the type keyword is NOT
    an identifier  (e.g.  int 5;   float +x;   double;).
    """
    first_type, first_val = stmt[0]
    if not (first_type == 'KEYWORD' and first_val in DECL_KEYWORDS):
        return None  # not a declaration — skip

    if len(stmt) < 2:
        snippet = ' '.join(v for _, v in stmt)
        return (
            f"[Statement {stmt_no}] Invalid declaration — "
            f"missing variable name  →  {snippet}"
        )

    second_type, second_val = stmt[1]
    if second_type != 'IDENTIFIER':
        snippet = ' '.join(v for _, v in stmt)
        return (
            f"[Statement {stmt_no}] Invalid declaration — "
            f"expected variable name after '{first_val}', "
            f"got '{second_val}'  →  {snippet}"
        )

    return None


def check_invalid_assignment(stmt, stmt_no):
    """
    Whenever '=' appears in a statement, the very next token must be a
    valid RHS value (NUMBER, FLOAT, STRING, CHAR_LIT, or IDENTIFIER).

    Bad examples:
        int x = ;       →  ';' after '='
        int x =         →  '=' is the last token
        float y = =     →  operator after '='
    """
    for i, (tok_type, tok_val) in enumerate(stmt):
        if not (tok_type == 'OPERATOR' and tok_val == '='):
            continue

        # '=' is the very last token
        if i + 1 >= len(stmt):
            snippet = ' '.join(v for _, v in stmt)
            return (
                f"[Statement {stmt_no}] Invalid assignment — "
                f"nothing after '='  →  {snippet}"
            )

        next_type, next_val = stmt[i + 1]
        if next_type not in VALID_RHS_TYPES:
            snippet = ' '.join(v for _, v in stmt)
            return (
                f"[Statement {stmt_no}] Invalid assignment — "
                f"unexpected '{next_val}' after '='  →  {snippet}"
            )

    return None


# ──────────────────────────────────────────────────────────────────────
# STEP 4 — Main syntax analysis entry point
# ──────────────────────────────────────────────────────────────────────

def analyze(tokens):
    """
    Run all syntax checks on the token list from lexer.tokenize().

    Parameters
    ----------
    tokens : list of (str, str)   Output of lexer.tokenize().

    Returns
    -------
    errors : list of str          One string per error found.
                                  Empty list → no syntax errors.

    Design: errors are COLLECTED, not raised — analysis never stops
    mid-way so the caller always receives the full error list.
    """
    errors = []

    statements = split_into_statements(tokens)

    for stmt_no, stmt in enumerate(statements, start=1):

        if should_ignore(stmt):
            continue

        # Run each check independently so a single bad statement
        # can produce multiple distinct errors
        err = check_missing_semicolon(stmt, stmt_no)
        if err:
            errors.append(err)

        err = check_invalid_declaration(stmt, stmt_no)
        if err:
            errors.append(err)

        err = check_invalid_assignment(stmt, stmt_no)
        if err:
            errors.append(err)

    return errors


# ──────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from lexer import tokenize

    def run(label, code, expect):
        toks = tokenize(code)
        errors = analyze(toks)
        status = "✓ PASS" if (bool(errors) == expect) else "✗ FAIL"
        print(f"{status}  {label}")
        for e in errors:
            print(f"       {e}")
        print()

    print("=" * 60)
    print("SYNTAX ANALYZER  –  self-tests")
    print("=" * 60)
    print()

    # ── should produce NO errors ──────────────────────────────
    run("Full C program (clean)",
        """
        #include <stdio.h>
        int main() {
            int a = 10;
            float b = 3.14;
            int sum = a + b;
            printf("result = %d", sum);
            return 0;
        }
        """,
        expect=False)

    # ── missing semicolon ─────────────────────────────────────
    run("Missing semicolon",
        "int a = 10\nint b = 20;",
        expect=True)

    # ── invalid declaration: int 5; ───────────────────────────
    run("Invalid declaration  (int 5;)",
        "int 5;",
        expect=True)

    # ── invalid assignment: float y = ; ──────────────────────
    run("Invalid assignment  (float y = ;)",
        "float y = ;",
        expect=True)

    # ── multiple errors in one program ───────────────────────
    run("Multiple errors",
        "int a = 10\nfloat b =\nchar c = 'x';",
        expect=True)