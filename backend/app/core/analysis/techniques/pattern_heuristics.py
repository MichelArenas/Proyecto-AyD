"""
Module for applying pattern-based heuristics to algorithm complexity analysis.
"""

from typing import Dict, Optional

from app.core.constants import PATTERNS
from app.core.language.ast import Program


class PatternHeuristics:
    """
    Apply pattern-based heuristics to adjust complexity estimates.
    """

    @staticmethod
    def detect_pattern(
        function_name: str, program: Program, algorithm_type: str
    ) -> Optional[Dict]:
        """
        Detect if the algorithm matches a known pattern.
        """
        function_name_lower = function_name.lower()
        code_str = str(program).lower()

        best_match = None
        best_score = 0

        for pattern_name, pattern_info in PATTERNS.items():
            score = 0

            pattern_chars = pattern_info["characteristics"]
            if "recursive" in pattern_chars and algorithm_type != "recursive":
                continue
            if (
                algorithm_type == "recursive"
                and "loop" in pattern_chars
                and "recursive" not in pattern_chars
            ):
                continue

            for keyword in pattern_info["keywords"]:
                if keyword in function_name_lower:
                    score += 3

            for characteristic in pattern_info["characteristics"]:
                if (
                    characteristic in code_str
                    or characteristic.replace("_", " ") in code_str
                ):
                    score += 1

            if algorithm_type in pattern_info["characteristics"]:
                score += 2

            if score > best_score:
                best_score = score
                best_match = {
                    "pattern": pattern_name,
                    "confidence": min(0.95, score * 0.15),
                    "complexity": pattern_info["complexity"],
                    "note": pattern_info["note"],
                }

        if best_match and best_match["confidence"] >= 0.4:
            return best_match

        return None

    @staticmethod
    def suggest_optimization(pattern_name: str) -> Optional[str]:
        """
        Suggest optimizations based on known patterns.
        """
        optimizations = {
            "fibonacci_naive": "Use memoization to reduce from O(2^n) to O(n)",
            "bubble_sort": "Consider using QuickSort O(n log(n)) or MergeSort O(n log(n))",
            "selection_sort": "Consider using QuickSort O(n log(n)) or MergeSort O(n log(n))",
            "linear_search": "For sorted arrays, use binary search O(log(n))",
            "knapsack_dp": "Already optimal for 0/1 knapsack",
        }

        return optimizations.get(pattern_name)
