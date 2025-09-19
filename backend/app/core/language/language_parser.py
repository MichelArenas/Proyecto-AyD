"""
Module that contains the implementation of the main parser for the refactored language.
"""

from app.core.exceptions.exception import ParsingError
from app.core.interfaces.language_parser import ILanguageParser
from app.core.language.ast.node import Program
from app.core.language.lark_parser import LarkParser
from app.core.language.ast_builder import ASTBuilder
from app.core.utils import FileReader


class LanguageParser(ILanguageParser):
    """
    Main parser for the refactored language.
    """

    def __init__(self):
        """
        Initializes the components needed for parsing.
        """
        self._file_reader = FileReader()
        self._lark_parser = LarkParser()
        self._transformer = ASTBuilder()
        self._lark_parser.set_transformer(self._transformer)

    def parse(self, code: str) -> Program:
        """
        Parse code and return the AST.
        """
        try:
            parse_tree = self._lark_parser.parse(code)
            return self._transformer.transform(parse_tree)
        except ParsingError as e:
            raise ParsingError(f"Error parsing code: {str(e)}") from e

    def parse_file(self, file_path: str) -> Program:
        """
        Parse a file and return the AST.
        """
        try:
            code = self._file_reader.read_file(file_path)
            return self.parse(code)
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(f"Error parsing file '{file_path}': {str(e)}") from e
