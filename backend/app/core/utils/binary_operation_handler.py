"""
Implements handling of binary operations in the AST.
"""

from abc import ABC, abstractmethod
from typing import Any, List

from lark import Token

from app.core.language.ast import ASTNode, BinOp
from app.core.utils.ast_normalizer import IASTNormalizer


class IBinaryOperationHandler(ABC):
    """
    Interface for handling binary operations in the AST.
    """

    @abstractmethod
    def create_binary_operation(self, op: str, left: Any, right: Any) -> ASTNode:
        """Creates a binary operation"""

    @abstractmethod
    def process_chain(self, items: List[Any]) -> Any:
        """Processes a chain of binary operations"""


class BinaryOperationHandler(IBinaryOperationHandler):
    """
    Handles binary operations in the AST.
    """

    def __init__(self, normalizer: IASTNormalizer):
        """
        Initialize with an AST normalizer.
        """
        self._normalizer = normalizer

    def create_binary_operation(self, op: str, left: Any, right: Any) -> ASTNode:
        """
        Create a binary operation node.
        """
        return BinOp(op=op, left=left, right=right)

    def process_chain(self, items: List[Any]) -> Any:
        """
        Process a chain of binary operations and return the resulting AST node.
        """
        if not items:
            return None

        left = self._normalizer.normalize(items[0])
        i = 1

        while i < len(items):
            if i + 1 >= len(items):
                break

            op = items[i]
            right = items[i + 1]
            op_sym = op.value if isinstance(op, Token) else str(op)

            left = self._normalizer.normalize(left)
            right = self._normalizer.normalize(right)

            left = self.create_binary_operation(op_sym, left, right)
            i += 2

        return left
