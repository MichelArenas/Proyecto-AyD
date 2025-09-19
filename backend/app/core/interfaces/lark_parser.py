from abc import ABC, abstractmethod
from typing import Any


class ILarkParser(ABC):
    """Interface for a Lark parser

    This interface defines the contract for parsing code using the Lark library.
    It ensures that any implementation provides a method to parse code and return
    the resulting parse tree.
    """

    @abstractmethod
    def parse(self, code: str) -> Any:
        """Parses code and returns the parse tree"""