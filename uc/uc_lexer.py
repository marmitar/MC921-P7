from __future__ import annotations
import argparse
import pathlib
import re
import sys
from typing import Callable
import ply.lex as lex


class UCLexer:
    """A lexer for the uC language. After building it, set the
    input text with input(), and call token() to get new
    tokens.
    """

    def __init__(self, error_func: Callable[[str, int, int], None]):
        """Create a new Lexer.
        An error function. Will be called with an error
        message, line and column as arguments, in case of
        an error during lexing.
        """
        self.error_func = error_func
        self.filename = ""

        # Keeps track of the last token returned from self.token()
        self.last_token = None

    def build(self, **kwargs) -> None:
        """Builds the lexer from the specification. Must be
        called after the lexer object is created.

        This method exists separately, because the PLY
        manual warns against calling lex.lex inside __init__
        """
        self.lexer = lex.lex(object=self, reflags=re.VERBOSE, **kwargs)

    def reset_lineno(self) -> None:
        """Resets the internal line number counter of the lexer."""
        self.lexer.lineno = 1

    def input(self, text: str) -> None:
        self.lexer.input(text)

    def token(self):
        self.last_token = self.lexer.token()
        return self.last_token

    def find_tok_column(self, token) -> int:
        """Find the column of the token in its line."""
        last_cr = self.lexer.lexdata.rfind("\n", 0, token.lexpos)
        return token.lexpos - last_cr

    # Internal auxiliary methods
    def _error(self, msg: str, token) -> None:
        location = self._make_tok_location(token)
        self.error_func(msg, location[0], location[1])
        self.lexer.skip(1)

    def _make_tok_location(self, token) -> tuple[int, int]:
        return (token.lineno, self.find_tok_column(token))

    # Reserved keywords
    keywords = (
        "ASSERT",
        "BOOL",
        "BREAK",
        "CHAR",
        "ELSE",
        "FALSE",
        "FLOAT",
        "FOR",
        "IF",
        "INT",
        "PRINT",
        "READ",
        "RETURN",
        "TRUE",
        "VOID",
        "WHILE",
    )

    keyword_map = {}
    for keyword in keywords:
        keyword_map[keyword.lower()] = keyword

    #
    # All the tokens recognized by the lexer
    #
    tokens = keywords + (
        # Identifiers
        "ID",
        # constants
        "INT_CONST",
        "STRING_LITERAL",
        "CHAR_CONST",
        "FLOAT_CONST",
        # delimiters
        "LPAREN",
        "RPAREN",
        "LBRACE",
        "RBRACE",
        "LBRACKET",
        "RBRACKET",
        # comparators
        "EQ",
        "NE",
        "LT",
        "GT",
        "LE",
        "GE",
        # operators
        "EQUALS",
        "PLUS",
        "MOD",
        "MINUS",
        "TIMES",
        "DIVIDE",
        "AND",
        "OR",
        "NOT",
        "ADDRESS",
        # punctuation
        "SEMI",
        "COMMA",
    )

    #
    # Rules
    #
    t_ignore = " \t"

    # delimiters
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_LBRACE = r"\{"
    t_RBRACE = r"\}"
    t_LBRACKET = r"\["
    t_RBRACKET = r"\]"

    # comparators
    t_EQ = r"=="
    t_NE = r"!="
    t_LT = r"<"
    t_GT = r">"
    t_LE = r"<="
    t_GE = r">="

    # operators
    t_EQUALS = r"="
    t_PLUS = r"\+"
    t_MOD = r"%"
    t_MINUS = r"-"
    t_TIMES = r"\*"
    t_DIVIDE = r"/"
    t_AND = r"&&"
    t_OR = r"\|\|"
    t_NOT = r"!"
    t_ADDRESS = r"&"

    # punctuation
    t_SEMI = r";"
    t_COMMA = r","

    # constants
    t_INT_CONST = r"\d(\d|_\d)*"
    t_CHAR_CONST = r"\'(\\.|.)+?\'"
    t_FLOAT_CONST = r"""
        (
            (
                (   # numbers like 123.
                    \d(\d|_\d)*\.(\d(\d|_\d)*)?
                )|( # and .456
                    (\d(\d|_\d)*)?\.\d(\d|_\d)*
                )   # can be 1.23e-2
                ((E|e)(\+|-)?\d(\d|_\d)*)?
            ) | (   # fractional isn't required with exponents
                \d(\d|_\d)(E|e)(\+|-)?\d(\d|_\d)
            )
        )
    """

    def t_STRING_LITERAL(self, t):
        r"\"(\\.|.|\n)*?\""
        t.value = t.value[1:-1]
        return t

    def t_ID(self, t):
        r"[^\d\W]\w*"
        t.type = self.keyword_map.get(t.value, "ID")
        return t

    # newlines
    def t_NEWLINE(self, t):
        r"\n+"
        t.lexer.lineno += t.value.count("\n")

    def t_comment(self, t):
        r"(/\*(.|\n)*?\*/)|(//.*)"
        t.lexer.lineno += t.value.count("\n")

    # errors
    def t_unterminated_string(self, t):
        r"\"(\\.|.|\n)*"
        # must come after 't_STRING_LITERAL'
        self._error("Unterminated string", t)

    def t_unterminated_comment(self, t):
        r"/\*(.|\n)*"
        # must come after 't_comment'
        self._error("Unterminated comment", t)

    def t_error(self, t):
        msg = "Illegal character %s" % repr(t.value[0])
        self._error(msg, t)

    # Scanner (used only for test)
    def scan(self, data: str) -> str:
        self.lexer.input(data)
        output = ""
        while True:
            tok = self.lexer.token()
            if not tok:
                break
            print(tok)
            output += str(tok) + "\n"
        return output


if __name__ == "__main__":

    # create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Path to file to be scanned", type=str)
    args = parser.parse_args()

    # get input path
    input_file = args.input_file
    input_path = pathlib.Path(input_file)

    # check if file exists
    if not input_path.exists():
        print("Input", input_path, "not found", file=sys.stderr)
        sys.exit(1)

    def print_error(msg: str, x: int, y: int):
        # use stdout to match with the output in the .out test files
        print("Lexical error: %s at %d:%d" % (msg, x, y), file=sys.stdout)

    # set error function
    m = UCLexer(print_error)
    # Build the lexer
    m.build()
    # open file and print tokens
    with open(input_path) as f:
        m.scan(f.read())
