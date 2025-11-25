"""
Extracts names and values from tokens and AST nodes.
"""

from abc import ABC, abstractmethod
from typing import Any

from lark import Token


class ITokenExtractor(ABC):
    """
    Interface for extracting names and values from tokens and AST nodes.
    """

    @abstractmethod
    def extract_name(self, item: Any) -> str:
        """Extracts the name of a token or node"""

    @abstractmethod
    def extract_value(self, item: Any) -> Any:
        """Extracts the value of a token or node"""


class TokenExtractor(ITokenExtractor):
    """
    Extracts names and values from tokens and AST nodes.
    """

    def extract_name(self, item: Any) -> str:
        """
        Extract the name from a token or AST node.
        """
        if not item:
            return ""

        if isinstance(item, Token):
            return item.value

        if hasattr(item, "name"):
            return getattr(item, "name")

        if hasattr(item, "value") and isinstance(item.value, str):
            return item.value

        return str(item)

    def extract_value(self, item: Any) -> Any:
        """
        Extract the value from a token or AST node.
        """
        if not item:
            return None

        if isinstance(item, Token):
            return item.value

        if hasattr(item, "value"):
            return getattr(item, "value")

        return item
