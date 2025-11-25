"""
Module for calculating the time complexity of algorithms
"""

from typing import Optional

from app.core.analysis.iterative_analyzer import IterativeAnalyzer
from app.core.analysis.recursive_analyzer import RecursiveAnalyzer
from app.core.language.ast import (LoopChecker, Program, RecursionChecker,
                                   SubroutineDef)
from app.core.models import (CaseAnalysis, Complexity, ComplexityResult,
                             create_complexity_notation)


class ComplexityCalculator:
    """
    Calculate the time complexity of algorithms in pseudocode.
    Supports recursive, iterative, hybrid, and simple algorithms.
    """

    def __init__(self):
        self.recursive_analyzer = RecursiveAnalyzer()
        self.iterative_analyzer = IterativeAnalyzer()

    def analyze(
        self, program: Program, function_name: Optional[str] = None
    ) -> ComplexityResult:
        """
        Analyze the given program to determine its time complexity.
        If function_name is provided, analyze that specific function.
        Otherwise, analyze the first defined function or the main program.
        """
        if function_name is None:
            for stmt in program.statements:
                if isinstance(stmt, SubroutineDef) and stmt.name:
                    function_name = str(stmt.name)
                    break

        algorithm_type = self._determine_algorithm_type(program, function_name)

        if algorithm_type == "recursive":
            return self._analyze_recursive(program, function_name)

        if algorithm_type == "iterative":
            return self._analyze_iterative(program, function_name)

        if algorithm_type == "hybrid":
            return self._analyze_hybrid(program, function_name)

        return self._analyze_simple(program, function_name)

    def _determine_algorithm_type(
        self, program: Program, function_name: Optional[str]
    ) -> str:
        """
        Determine if the algorithm is recursive, iterative, hybrid, or simple.
        """
        target_func = None
        if function_name:
            for stmt in program.statements:
                if isinstance(stmt, SubroutineDef) and stmt.name == function_name:
                    target_func = stmt
                    break

        if not target_func:
            has_loops = self._has_loops(program.statements)
            has_recursion = False
            return "iterative" if has_loops else "simple"

        has_recursion = self._has_recursion(target_func, str(target_func.name))

        has_loops = self._has_loops(target_func.body)

        if has_recursion and has_loops:
            return "hybrid"

        if has_recursion:
            return "recursive"

        if has_loops:
            return "iterative"

        return "simple"

    def _has_recursion(self, func_def: SubroutineDef, func_name: str) -> bool:
        """Check if function contains recursion"""

        checker = RecursionChecker(func_name)
        for stmt in func_def.body:
            stmt.accept(checker)
        return checker.found

    def _has_loops(self, statements: list) -> bool:
        """Check if statements contain loops"""

        checker = LoopChecker()
        for stmt in statements:
            stmt.accept(checker)
        return checker.found

    def _analyze_recursive(
        self, program: Program, function_name: Optional[str]
    ) -> ComplexityResult:
        """Analyze recursive algorithm"""
        result = self.recursive_analyzer.analyze(program, function_name)
        result.algorithm_type = "recursive"
        return result

    def _analyze_iterative(
        self, program: Program, function_name: Optional[str]
    ) -> ComplexityResult:
        """Analyze iterative algorithm"""
        result = self.iterative_analyzer.analyze(program, function_name)
        result.algorithm_type = "iterative"
        return result

    def _analyze_hybrid(
        self, program: Program, function_name: Optional[str]
    ) -> ComplexityResult:
        """
        Analyze hybrid algorithm (both recursion and iteration).
        Combine results from recursive and iterative analyzers.
        """

        recursive_result = self.recursive_analyzer.analyze(program, function_name)
        iterative_result = self.iterative_analyzer.analyze(program, function_name)

        def combine_complexities(
            rec_case: CaseAnalysis, iter_case: CaseAnalysis
        ) -> CaseAnalysis:
            """Combine two case analyses, taking the higher complexity"""
            combined = CaseAnalysis(
                case_type=rec_case.case_type,
                big_o=rec_case.big_o,
                omega=rec_case.omega,
                theta=rec_case.theta,
                explanation=f"Hybrid algorithm: Recursive with loops. {rec_case.explanation}",
                evidence=rec_case.evidence + iter_case.evidence,
                recurrence_relation=rec_case.recurrence_relation,
            )
            return combined

        best_case = combine_complexities(
            recursive_result.best_case, iterative_result.best_case
        )
        avg_case = combine_complexities(
            recursive_result.average_case, iterative_result.average_case
        )
        worst_case = combine_complexities(
            recursive_result.worst_case, iterative_result.worst_case
        )

        detailed_explanation = f"""
        Hybrid Algorithm Analysis:
        Recursive Component:
        {recursive_result.detailed_explanation}
        Iterative Component:
        {iterative_result.detailed_explanation}
        """

        result = ComplexityResult(
            algorithm_name=function_name or "main",
            algorithm_type="hybrid",
            best_case=best_case,
            average_case=avg_case,
            worst_case=worst_case,
            space_complexity=recursive_result.space_complexity,
            is_recursive=True,
            recursion_depth=recursive_result.recursion_depth,
            loop_structure=iterative_result.loop_structure,
            detailed_explanation=detailed_explanation,
            step_by_step_analysis=recursive_result.step_by_step_analysis
            + iterative_result.step_by_step_analysis,
        )

        return result

    def _analyze_simple(
        self, _: Program, function_name: Optional[str]
    ) -> ComplexityResult:
        """
        Analyze simple algorithm with no loops or recursion.
        """

        notations = create_complexity_notation("1", tight_bound=True)

        case = CaseAnalysis(
            case_type="all",
            big_o=notations["big_o"],
            omega=notations["omega"],
            theta=notations["theta"],
            explanation="Simple algorithm with no loops or recursion - constant time",
            evidence=["No iterative or recursive structures detected"],
        )

        space_complexity = Complexity("O", "1", "O(1)", tight_bound=True)

        return ComplexityResult(
            algorithm_name=function_name or "main",
            algorithm_type="simple",
            best_case=case,
            average_case=case,
            worst_case=case,
            space_complexity=space_complexity,
            is_recursive=False,
            detailed_explanation="This is a simple algorithm with constant time complexity O(1).",
            step_by_step_analysis=[
                "1. No loops detected",
                "2. No recursive calls detected",
                "3. All operations are O(1)",
                "4. Final complexity: O(1)",
            ],
        )
