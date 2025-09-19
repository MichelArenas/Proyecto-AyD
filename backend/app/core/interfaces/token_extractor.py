from abc import ABC, abstractmethod
from typing import Any


class ITokenExtractor(ABC):
    """Interface for extracting token information

    This interface defines the contract for extracting meaningful information
    from tokens or nodes, such as their names and values.
    """

    @abstractmethod
    def extract_name(self, item: Any) -> str:
        """Extracts the name of a token or node"""

    @abstractmethod
    def extract_value(self, item: Any) -> Any:
        """Extracts the value of a token or node"""

