"""
Tracks and validates array dimensions in an abstract syntax tree (AST).
"""

from typing import Any, Dict, List, Optional

from app.core.language.ast import Number


class ArrayDimensionTracker:
    """
    Tracks and validates array dimensions for arrays in the AST.
    """

    def __init__(self):
        self.array_dimensions: Dict[str, List[Any]] = {}

    def register_array(self, name: str, dimensions: List[Any]):
        """
        Register an array with its dimensions.
        """
        self.array_dimensions[name] = dimensions

    def get_dimensions(self, name: str) -> Optional[List[Any]]:
        """
        Get the dimensions of a registered array.
        """
        return self.array_dimensions.get(name)

    def validate_access(self, array_name: str, indices: List[Any]) -> List[str]:
        """
        Validate access to an array with the given indices. Returns a list of error messages if any.
        """
        errors: List[str] = []

        if array_name not in self.array_dimensions:
            errors.append(f"Array '{array_name}' not declared.")
            return errors

        declared_dims = self.array_dimensions[array_name]

        if len(indices) != len(declared_dims):
            errors.append(
                f"Array '{array_name}' accessed with {len(indices)} indices, "
                f"but declared with {len(declared_dims)} dimensions."
            )
            return errors

        for i, (index, declared_dim) in enumerate(zip(indices, declared_dims)):
            if declared_dim and not self._is_within_bounds(index, declared_dim):
                errors.append(f"Index {i+1} out of bounds for array '{array_name}'.")

        return errors

    def _is_within_bounds(self, index: Any, max_dim: Any) -> bool:
        """
        Check if the index is within the bounds of the dimension.
        """
        if not max_dim:
            return True

        if isinstance(index, Number) and isinstance(max_dim, Number):
            return 0 <= index.value < max_dim.value
        return True
