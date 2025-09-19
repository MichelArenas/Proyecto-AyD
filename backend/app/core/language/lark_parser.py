"""
Module that implements a concrete parser using Lark.
"""

import os

from lark import Lark

from .ast_builder import ASTBuilder


class LarkParser:
    """
    Concrete parser implementation using Lark.
    """

    def __init__(self):
        self._grammar_path = os.path.join(
            os.path.dirname(__file__), "parsing", "grammar", "grammar.lark"
        )
        self._parser = self._initialize_parser()
        self._transformer = None

    def _initialize_parser(self) -> Lark:
        """
        Initialize the Lark parser.
        """
        return Lark.open(
            self._grammar_path,
            rel_to=__file__,
            parser="lalr",
            propagate_positions=True,
            maybe_placeholders=False,
        )

    def set_transformer(self, transformer: ASTBuilder):
        """
        Set the transformer to convert the parse tree to an AST.
        """
        self._transformer = transformer

    def parse(self, code: str):
        """
        Parse the code and return the parse tree.
        """
        return self._parser.parse(code)
