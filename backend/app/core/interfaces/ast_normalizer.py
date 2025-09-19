from abc import ABC, abstractmethod
from typing import Any


class IASTNormalizer(ABC):
    """Interface for AST normalization

    This interface defines the contract for normalizing Abstract Syntax Trees (ASTs).
    It ensures that any implementation provides a method to normalize AST nodes.
    """

    @abstractmethod
    def normalize(self, node: Any) -> Any:
        """Normalizes an AST node"""
