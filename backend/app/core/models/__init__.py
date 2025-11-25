"""
Initialization module for complexity analysis models.
"""

from typing import Dict

from app.core.models.complexity import (CaseAnalysis, Complexity,
                                        ComplexityClass, ComplexityResult,
                                        RecurrenceRelation)


def create_complexity_notation(
    expression: str, tight_bound: bool = True
) -> Dict[str, Complexity]:
    """
    Create Complexity objects for Big O, Omega, and Theta notations
    """
    return {
        "big_o": Complexity(
            "O", expression, f"O({expression})", tight_bound=tight_bound
        ),
        "omega": Complexity(
            "Omega", expression, f"Ω({expression})", tight_bound=tight_bound
        ),
        "theta": Complexity(
            "Theta", expression, f"Θ({expression})", tight_bound=tight_bound
        ),
    }


__all__ = [
    "CaseAnalysis",
    "Complexity",
    "ComplexityClass",
    "ComplexityResult",
    "RecurrenceRelation",
    "create_complexity_notation",
]
