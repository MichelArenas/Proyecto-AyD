"""
Base class for complexity analyzers providing common helper methods.
"""

from app.core.language.ast import DefaultASTVisitor
from app.core.models import (CaseAnalysis, ComplexityResult,
                             create_complexity_notation)


class BaseAnalyzer(DefaultASTVisitor):
    """
    Base class for complexity analyzers providing common helper methods.
    """

    def _create_empty_result(
        self, algorithm_name: str, algorithm_type: str = "unknown"
    ) -> ComplexityResult:
        """
        Create a default ComplexityResult indicating inability to analyze complexity.
        """
        default_complexity = create_complexity_notation("O(1)")
        default_case = CaseAnalysis(
            case_type="",
            big_o=default_complexity["big_o"],
            omega=default_complexity["omega"],
            theta=default_complexity["theta"],
            explanation="Empty or simple algorithm",
            evidence=["No complex operations detected"],
        )

        return ComplexityResult(
            algorithm_name=algorithm_name,
            algorithm_type=algorithm_type,
            best_case=default_case,
            average_case=default_case,
            worst_case=default_case,
            space_complexity=default_complexity["big_o"],
            is_recursive=False,
            detailed_explanation="Unable to analyze complexity",
            step_by_step_analysis=[],
        )
