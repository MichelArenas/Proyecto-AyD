from abc import ABC, abstractmethod
from typing import Any, List

from app.core.language.ast.node import Parameter


class IParameterProcessor(ABC):
    """Interface for parameter processing

    This interface defines the contract for handling various types of parameters,
    such as simple variables, arrays, objects, and graphs. It ensures that any
    implementation provides methods for processing these parameter types.
    """

    @abstractmethod
    def process_simple_parameter(self, items: List[Any]) -> Parameter:
        """Processes a simple parameter: VAR"""
        pass

    @abstractmethod
    def process_array_parameter(self, items: List[Any]) -> Parameter:
        """Processes an array parameter: VAR[indexer]..."""
        pass

    @abstractmethod
    def process_object_parameter(self, items: List[Any]) -> Parameter:
        """Processes an object parameter: CLASS VAR VAR"""
        pass

    @abstractmethod
    def process_graph_parameter(self, items: List[Any]) -> Parameter:
        """Processes a graph parameter: GRAPH VAR"""
        pass
