from abc import ABC, abstractmethod
from typing import Any, List

from app.core.language.ast.node import ASTNode


class IExpressionHandler(ABC):
    """Interface for handling expressions

    This interface defines the contract for managing various types of expressions,
    such as function calls, array accesses, and field accesses.
    """

    @abstractmethod
    def handle_function_call(self, items: List[Any]) -> ASTNode:
        """Handles function calls"""

    @abstractmethod
    def handle_array_access(self, items: List[Any]) -> ASTNode:
        """Handles array access"""

    @abstractmethod
    def handle_field_access(self, items: List[Any]) -> ASTNode:
        """Handles field access"""
