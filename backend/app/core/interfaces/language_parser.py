from abc import ABC, abstractmethod

from app.core.language.ast.node import Program


class ILanguageParser(ABC):
    """Interface for the main language parser

    This interface defines the contract for parsing code into an Abstract Syntax Tree (AST).
    It ensures that any implementation provides methods for parsing both code strings
    and files into ASTs.
    """

    @abstractmethod
    def parse(self, code: str) -> Program:
        """Parses code and returns the AST"""

    @abstractmethod
    def parse_file(self, file_path: str) -> Program:
        """Parses a file and returns the AST"""
