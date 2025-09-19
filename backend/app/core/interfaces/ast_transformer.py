from abc import ABC, abstractmethod
from typing import Any

from app.core.language.ast.node import Program


class IASTTransformer(ABC):
    """Interface for transforming a parse tree into an AST

    This interface defines the contract for converting a parse tree into an Abstract Syntax Tree (AST).
    It ensures that any implementation provides a method to perform this transformation.
    """

    @abstractmethod
    def transform(self, tree: Any) -> Program:
        """Transforms the parse tree into an AST"""
