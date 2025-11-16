from abc import ABC, abstractmethod
from typing import Any, List

from app.core.language.ast.node import ASTNode


class IBinaryOperationHandler(ABC):
    """Interface for handling binary operations

    This interface defines the contract for creating and processing binary operations.
    It ensures that any implementation provides methods for creating binary operations
    and processing chains of such operations.
    """

    @abstractmethod
    def create_binary_operation(self, op: str, left: Any, right: Any) -> ASTNode:
        """Creates a binary operation"""

    @abstractmethod
    def process_chain(self, items: List[Any]) -> Any:
        """Processes a chain of binary operations"""
