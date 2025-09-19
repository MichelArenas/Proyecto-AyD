from abc import ABC, abstractmethod
from typing import Any, Tuple


class IIndexerProcessor(ABC):
    """Interface for processing indexers

    This interface defines the contract for handling various types of indexers,
    such as ranges, open-ended ranges, and single expressions.
    """

    @abstractmethod
    def process_range(self, start: Any, end: Any) -> Tuple[Any, Any]:
        pass

    @abstractmethod
    def process_open_start(self, end: Any) -> Tuple[Any, Any]:
        pass

    @abstractmethod
    def process_open_end(self, start: Any) -> Tuple[Any, Any]:
        pass

    @abstractmethod
    def process_open_both(self) -> Tuple[Any, Any]:
        pass

    @abstractmethod
    def process_single(self, expr: Any) -> Any:
        pass
