"""
Module providing a base class for AST validators with error and warning management.
"""

from typing import List, Set, Tuple

from app.core.language.ast import DefaultASTVisitor, Program


class BaseValidator(DefaultASTVisitor):
    """
    Base class for AST validators, providing error and warning management.
    """

    def __init__(self):
        super().__init__()
        self.errors: Set[str] = set()
        self.warnings: Set[str] = set()

    def add_error(self, message: str, prefix: str = "Error"):
        """
        Add a validation error with optional prefix.
        """
        self.errors.add(f"{prefix}: {message}")

    def add_warning(self, message: str, prefix: str = "Warning"):
        """
        Add a validation warning with optional prefix.
        """
        self.warnings.add(f"{prefix}: {message}")

    def clear_state(self):
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()

    def validate(self, program: Program) -> Tuple[List[str], List[str]]:
        """
        Validate the given program AST and return errors and warnings.
        """
        self.clear_state()
        program.accept(self)
        return list(self.errors), list(self.warnings)

    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any validation warnings."""
        return len(self.warnings) > 0

    def get_error_count(self) -> int:
        """Get the total number of errors."""
        return len(self.errors)

    def get_warning_count(self) -> int:
        """Get the total number of warnings."""
        return len(self.warnings)
