"""
Processes different indexer types for arrays in the AST.
"""

from typing import Any, Tuple

from app.core.interfaces.indexer_processor import IIndexerProcessor
from app.core.language.ast.node import Null



class IndexerProcessor(IIndexerProcessor):
    """
    Handles different indexer types for arrays in the AST.
    """

    def process_range(self, start: Any, end: Any) -> Tuple[Any, Any]:
        """
        Process a range indexer (start, end).
        """
        return (start, end)

    def process_open_start(self, end: Any) -> Tuple[Any, Any]:
        """
        Process an open start indexer (:end).
        """
        return (Null(), end)

    def process_open_end(self, start: Any) -> Tuple[Any, Any]:
        """
        Process an open end indexer (start:).
        """
        return (start, Null())

    def process_open_both(self) -> Tuple[Any, Any]:
        """
        Process an open both indexer (:).
        """
        return (Null(), Null())

    def process_single(self, expr: Any) -> Any:
        """
        Process a single indexer (expr).
        """
        return expr
