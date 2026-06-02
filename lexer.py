"""
lexer.py  –  Tokenizer for C-like source code
==============================================
Converts a raw source string into a flat list of (token_type, value) tuples.

Token types produced:
  KEYWORD     – reserved word:  int, float, char, double, void, return, …
  IDENTIFIER  – variable / function name:  myVar, sum, main, printf
  NUMBER      – integer literal:  0, 42, 100
  FLOAT       – floating-point literal:  3.14, 0.5
  STRING      – double-quoted string:  "hello"
  CHAR_LIT    – single-quoted char:  'a'
  OPERATOR    – operator:  = + - * / % == != < > <= >=
  SYMBOL      – punctuation:  ( ) { } [ ] ; , .
  PREPROCESSOR– lines that start with #:  #include <stdio.h>
  UNKNOWN     – anything the lexer cannot classify (reported but not fatal)
"""

import re

# ──────────────────────────────────────────────────────────────────────
# KEYWORDS
# ──────────────────────────────────────────────────────────────────────

KEYWORDS = {
    'int', 'float', 'char', 'double', 'void',
    'if', 'else', 'while', 'for', 'return',
    'break', 'continue', 'struct', 'true', 'false',
}

# ──────────────────────────────────────────────────────────────────────
# TOKEN RULES  (order matters — most specific first)
# ──────────────────────────────────────────────────────────────────────

TOKEN_RULES = [
    # Preprocessor  —  whole line starting with #
    ('PREPROCESSOR', r'#[^\n]*'),

    # Literals
    ('FLOAT',      r'\d+\.\d+'),          # 3.14  must come before NUMBER
    ('NUMBER',     r'\d+'),               # 42
    ('STRING',     r'"[^"]*"'),           # "hello world"
    ('CHAR_LIT',   r"'[^'\\]'|'\\.'"),    # 'a'  '\n'

    # Multi-character operators first, then single-character
    ('OPERATOR',   r'==|!=|<=|>=|&&|\|\||[+\-*/%=<>!]'),

    # Punctuation
    ('SYMBOL',     r'[(){}\[\];,.]'),

    # Names
    ('IDENTIFIER', r'[A-Za-z_]\w*'),

    # Noise — skip
    ('WHITESPACE', r'\s+'),

    # Catch-all
    ('UNKNOWN',    r'.'),
]

MASTER_PATTERN = re.compile(
    '|'.join(f'(?P<{name}>{pat})' for name, pat in TOKEN_RULES)
)


# ──────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────

def tokenize(source_code: str) -> list:
    """
    Convert *source_code* into a list of (token_type, value) tuples.

    - Whitespace is discarded.
    - IDENTIFIER tokens that are reserved words become KEYWORD.
    - UNKNOWN tokens are kept so downstream stages can report them.

    Parameters
    ----------
    source_code : str   Raw C-like source text.

    Returns
    -------
    list of (str, str)  e.g.  [('KEYWORD','int'), ('IDENTIFIER','x'), …]
    """
    tokens = []

    for match in MASTER_PATTERN.finditer(source_code):
        tok_type = match.lastgroup
        value = match.group()

        if tok_type == 'WHITESPACE':
            continue  # whitespace carries no meaning

        if tok_type == 'IDENTIFIER' and value in KEYWORDS:
            tok_type = 'KEYWORD'  # promote reserved words

        tokens.append((tok_type, value))

    return tokens


# ──────────────────────────────────────────────────────────────────────
# OPTIONAL PRETTY PRINTER
# ──────────────────────────────────────────────────────────────────────

def print_tokens(tokens: list) -> None:
    """Print the token list in a neat aligned table."""
    print(f"\n{'TOKEN TYPE':<16}  VALUE")
    print("─" * 36)
    for tok_type, value in tokens:
        print(f"  {tok_type:<14}  {value}")
    print()


# ──────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample = """
#include <stdio.h>

int main() {
    int a = 10;
    float b = 3.14;
    int sum = a + b;
    printf("result = %d", sum);
    return 0;
}
"""
    print("Source:")
    print(sample)
    toks = tokenize(sample)
    print_tokens(toks)