"""
Data structures for representing algorithm complexity analysis
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ComplexityClass(Enum):
    """Common complexity classes"""

    CONSTANT = "O(1)"
    LOGARITHMIC = "O(log(n))"
    LINEAR = "O(n)"
    LINEARITHMIC = "O(n log(n))"
    QUADRATIC = "O(n^2)"
    CUBIC = "O(n^3)"
    POLYNOMIAL = "O(n^k)"
    EXPONENTIAL = "O(2^n)"
    FACTORIAL = "O(n!)"
    UNKNOWN = "O(?)"


@dataclass
class Complexity:
    """
    Represents a complexity expression
    """

    notation: str
    expression: str
    simplified: str
    tight_bound: bool = False

    def __str__(self) -> str:
        return self.simplified


@dataclass
class CaseAnalysis:
    """
    Complexity analysis for a specific case (best, average, worst)
    """

    case_type: str
    big_o: Complexity
    omega: Complexity
    theta: Optional[Complexity] = None
    explanation: str = ""
    evidence: List[str] = field(default_factory=list)
    recurrence_relation: Optional[str] = None


@dataclass
class ComplexityResult:
    """
    Represents the overall complexity analysis of an algorithm
    """

    algorithm_name: str
    algorithm_type: str

    best_case: CaseAnalysis
    average_case: CaseAnalysis
    worst_case: CaseAnalysis

    space_complexity: Complexity

    is_recursive: bool = False
    recursion_depth: Optional[str] = None
    loop_structure: Dict[str, Optional[int]] = field(default_factory=dict)
    dominant_operations: List[str] = field(default_factory=list)

    algorithmic_pattern: Optional[str] = None

    detailed_explanation: str = ""
    step_by_step_analysis: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Generate a summary of the complexity analysis"""
        lines = [
            f"Algorithm: {self.algorithm_name}",
            f"Type: {self.algorithm_type}",
            "",
            "Time Complexity:",
            f"  Best case:    Ω({self.best_case.omega.expression}) "
            f"= O({self.best_case.big_o.expression})"
            f"  Average case: Ω({self.average_case.omega.expression}) "
            f"= O({self.average_case.big_o.expression})",
            f"  Worst case:   Ω({self.worst_case.omega.expression}) "
            f"= O({self.worst_case.big_o.expression})",
            "",
            f"Space Complexity: {self.space_complexity}",
        ]

        if self.best_case.theta:
            lines.insert(4, f"    Θ({self.best_case.theta.expression})")
        if self.average_case.theta:
            lines.insert(6, f"    Θ({self.average_case.theta.expression})")
        if self.worst_case.theta:
            lines.insert(8, f"    Θ({self.worst_case.theta.expression})")

        if self.algorithmic_pattern:
            lines.append(f"\nPattern: {self.algorithmic_pattern}")

        return "\n".join(lines)


@dataclass
class RecurrenceRelation:
    """
    Represents a recurrence relation and its solution
    """

    relation: str
    base_case: str
    solution: str
    method: str
    steps: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.relation}, {self.base_case} => {self.solution}"
