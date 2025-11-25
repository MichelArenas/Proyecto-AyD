"""
Handler for multidimensional arrays in the AST.
Provides validation and suggestions for multidimensional array usage.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.core.language.ast import (ArrayAccess, ArraySlice, ArrayTarget, BinOp,
                                   DefaultASTVisitor, Number, Var)
from app.core.utils import ArrayDimensionTracker


class MultidimensionalArrayHandler(DefaultASTVisitor):
    """
    Handles multidimensional arrays in the AST, including validation and optimization suggestions.
    """

    def __init__(self, dimension_tracker: Optional[ArrayDimensionTracker] = None):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.dimension_tracker: ArrayDimensionTracker = (
            dimension_tracker or ArrayDimensionTracker()
        )

    def _is_valid_index(self, index: Any) -> bool:
        """
        Check if an index is valid for array access.
        """
        if isinstance(index, Number):
            return isinstance(index.value, int) and index.value >= 0
        if isinstance(index, Var):
            return True
        if isinstance(index, BinOp):
            return True
        return False

    def _is_valid_range(self, start: Any, end: Any) -> bool:
        """
        Check if a range defined by start and end indices is valid.
        """
        return self._is_valid_index(start) and self._is_valid_index(end)

    def validate_multidimensional_access(
        self, array_name: str, indices: List[Any]
    ) -> bool:
        """
        Validates access to a multidimensional array with the given indices.
        """
        if not indices:
            self.errors.append(f"Array '{array_name}' accessed without indices")
            return False

        for i, index in enumerate(indices):
            if not self._is_valid_index(index):
                self.errors.append(
                    f"Invalid index in dimension {i+1} of array '{array_name}'"
                )
                return False

        dimension_errors = self.dimension_tracker.validate_access(array_name, indices)
        self.errors.extend(dimension_errors)

        return len(dimension_errors) == 0

    def validate_multidimensional_slice(
        self, array_name: str, ranges: List[Any]
    ) -> bool:
        """
        Validates a slice operation on a multidimensional array.
        """
        if not ranges:
            self.errors.append(
                f"Slice of array '{array_name}' without specified ranges"
            )
            return False

        for i, range_spec in enumerate(ranges):
            if isinstance(range_spec, tuple) and len(range_spec) == 2:
                start, end = range_spec
                if not self._is_valid_range(start, end):
                    self.errors.append(
                        f"Invalid range in dimension {i+1} of slice '{array_name}'"
                    )
                    return False
            else:
                self.errors.append(
                    f"Invalid range specification in dimension {i+1} of slice '{array_name}'"
                )
                return False

        return True

    def create_enhanced_array_access(
        self, name: str, indices: List[Any]
    ) -> ArrayAccess:
        if self.validate_multidimensional_access(name, indices):
            return ArrayAccess(name=name, index=indices)
        return ArrayAccess(name=name, index=indices)

    def create_enhanced_array_slice(self, name: str, ranges: List[Any]) -> ArraySlice:
        if self.validate_multidimensional_slice(name, ranges):
            return ArraySlice(name=name, ranges=ranges)
        return ArraySlice(name=name, ranges=ranges)

    def normalize_multidimensional_declaration(
        self, name: str, dimensions: List[Any]
    ) -> Tuple[str, List[Any]]:
        """
        Normalizes the declaration of a multidimensional array.
        """
        if not dimensions:
            self.warnings.append(f"Array '{name}' declared without specific dimensions")
            return (name, [])

        normalized_dims: List[Any] = []
        for i, dim in enumerate(dimensions):
            if isinstance(dim, tuple) and len(dim) == 2:
                start, end = dim
                if self._is_valid_range(start, end):
                    normalized_dims.append(dim)
                else:
                    self.warnings.append(
                        f"Invalid range in dimension {i+1} for array '{name}'"
                    )
            else:
                if self._is_valid_index(dim):
                    normalized_dims.append(dim)
                else:
                    self.warnings.append(f"Invalid dimension {i+1} for array '{name}'")

        return (name, normalized_dims)

    def get_dimension_info(self, array_access: ArrayAccess) -> Dict[str, Any]:
        return {
            "name": array_access.name,
            "dimension_count": (
                len(array_access.index) if isinstance(array_access.index, list) else 1
            ),
            "indices": array_access.index,
        }

    def suggest_multidimensional_optimizations(
        self, array_accesses: List[ArrayAccess]
    ) -> List[str]:
        """
        Suggests optimizations for multidimensional array accesses.
        """
        suggestions: List[str] = []

        array_groups: Dict[str, List[ArrayAccess]] = {}
        for access in array_accesses:
            if access.name not in array_groups:
                array_groups[access.name] = []
            array_groups[access.name].append(access)

        for array_name, accesses in array_groups.items():
            if len(accesses) > 3:
                suggestions.append(
                    f"Consider optimizing multiple accesses to array '{array_name}'"
                )

            sequential_count = 0
            for i in range(len(accesses) - 1):
                current = accesses[i]
                next_access = accesses[i + 1]
                if self._are_sequential_accesses(current, next_access):
                    sequential_count += 1

            if sequential_count > 2:
                suggestions.append(
                    f"Sequential access pattern detected in '{array_name}': consider using slice A[start..end]"
                )

        return suggestions

    def _are_sequential_accesses(
        self, access1: ArrayAccess, access2: ArrayAccess
    ) -> bool:
        return access1.name == access2.name

    def visit_array_access(self, node: ArrayAccess) -> Any:
        self.validate_multidimensional_access(node.name, node.index)
        return super().visit_array_access(node)

    def visit_array_slice(self, node: ArraySlice) -> Any:
        self.validate_multidimensional_slice(node.name, node.ranges)
        return super().visit_array_slice(node)

    def visit_array_target(self, node: ArrayTarget) -> Any:
        self.validate_multidimensional_access(node.name, node.index)
        return super().visit_array_target(node)
