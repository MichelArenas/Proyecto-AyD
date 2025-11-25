"""
Processes different types of parameters in the AST.
"""

from abc import ABC, abstractmethod
from typing import Any, List

from app.core.language.ast import Parameter
from app.core.utils.token_extractor import TokenExtractor


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


class ParameterProcessor(IParameterProcessor):
    """
    Processes different types of parameters in the AST.
    """

    def __init__(self, token_extractor: TokenExtractor):
        """
        Initialize with a token extractor.
        """
        self._token_extractor = token_extractor or TokenExtractor()

    def process_simple_parameter(self, items: List[Any]) -> Parameter:
        """
        Process a simple variable parameter.
        """
        name = self._token_extractor.extract_name(items[0]) if items else ""
        return Parameter(name=name, param_type="var", dimensions=None, class_name=None)

    def process_array_parameter(self, items: List[Any]) -> Parameter:
        """
        Process an array parameter with dimensions.
        """
        name = self._token_extractor.extract_name(items[0]) if items else ""

        dimensions: List[Any] = []
        for item in items[1:]:
            if item:
                dimensions.append(item)

        return Parameter(
            name=name, param_type="array", dimensions=dimensions, class_name=None
        )

    def process_object_parameter(self, items: List[Any]) -> Parameter:
        """
        Process an object parameter with class name and variable name.
        """
        if len(items) < 3:
            return Parameter(
                name="", param_type="object", dimensions=None, class_name=""
            )

        class_name = self._token_extractor.extract_name(items[1])
        var_name = self._token_extractor.extract_name(items[2])
        return Parameter(
            name=var_name, param_type="object", dimensions=None, class_name=class_name
        )

    def process_graph_parameter(self, items: List[Any]) -> Parameter:
        """
        Process a graph parameter.
        """
        name = self._token_extractor.extract_name(items[1]) if len(items) > 1 else ""
        return Parameter(
            name=name, param_type="graph", dimensions=None, class_name=None
        )
