"""
Recursive Algorithm Complexity Analyzer Module
"""

from typing import Dict, List, Optional, Tuple

from app.core.analysis.techniques import (DynamicProgrammingDetector,
                                          PatternHeuristics, RecursionTree,
                                          RecursionTreeAnalyzer)
from app.core.language.ast import (BinOp, DefaultASTVisitor, FuncCallExpr,
                                   IfElse, Number, Program, RecursionChecker,
                                   ReturnStmt, SubroutineDef, Var,
                                   WorkAnalyzer)
from app.core.models import (CaseAnalysis, Complexity, ComplexityResult,
                             RecurrenceRelation, create_complexity_notation)


class RecursiveAnalyzer(DefaultASTVisitor):
    """
    Analyzes recursive algorithms to determine their time and space complexity.
    """

    def __init__(self):
        self.recursive_functions: Dict[str, SubroutineDef] = {}
        self.call_counts: Dict[str, int] = {}
        self.current_function: Optional[str] = None
        self.base_cases: Dict[str, List[str]] = {}
        self.problem_size_reduction: Dict[str, List[str]] = {}
        self.dp_detector = DynamicProgrammingDetector()
        self.recursion_tree: Optional[RecursionTree] = None

    def analyze(
        self, program: Program, function_name: Optional[str] = None
    ) -> ComplexityResult:
        """
        Analyze the given program for recursive algorithms using advanced techniques.
        """
        self._identify_recursive_functions(program)

        if not function_name and self.recursive_functions:
            function_name = list(self.recursive_functions.keys())[0]

        if not function_name or function_name not in self.recursive_functions:
            return self._create_empty_result("unknown")

        func_def = self.recursive_functions[function_name]

        self.current_function = function_name
        self._analyze_recursive_calls(func_def)
        self._analyze_base_cases(func_def)

        dp_result = self.dp_detector.detect(program, function_name)
        pattern_match = PatternHeuristics.detect_pattern(
            function_name, program, "recursive"
        )
        recurrence = self._build_recurrence_relation(function_name, func_def)
        best_case = self._analyze_best_case(
            function_name, recurrence, dp_result, pattern_match
        )
        worst_case = self._analyze_worst_case(
            function_name, recurrence, dp_result, pattern_match
        )
        average_case = self._analyze_average_case(
            function_name, recurrence, dp_result, pattern_match
        )

        space_complexity = self._analyze_space_complexity(function_name, func_def)

        explanation = self._generate_explanation(
            function_name, recurrence, dp_result, pattern_match
        )
        steps = self._generate_step_by_step(recurrence, dp_result, pattern_match)

        return ComplexityResult(
            algorithm_name=function_name,
            algorithm_type="recursive",
            best_case=best_case,
            average_case=average_case,
            worst_case=worst_case,
            space_complexity=space_complexity,
            is_recursive=True,
            recursion_depth=self._calculate_recursion_depth(recurrence),
            detailed_explanation=explanation,
            step_by_step_analysis=steps,
        )

    def _identify_recursive_functions(self, program: Program):
        """Identify all recursive functions in the program"""
        for stmt in program.statements:
            if isinstance(stmt, SubroutineDef) and stmt.name:
                func_name = str(stmt.name)
                if self._has_self_call(stmt, func_name):
                    self.recursive_functions[func_name] = stmt

    def _has_self_call(self, func_def: SubroutineDef, func_name: str) -> bool:
        """Check if function calls itself"""
        checker = RecursionChecker(func_name)
        for stmt in func_def.body:
            stmt.accept(checker)
        return checker.found

    def _analyze_recursive_calls(self, func_def: SubroutineDef):
        """Analyze how many recursive calls are made"""

        class CallCounter(DefaultASTVisitor):
            def __init__(self, target_name: str):
                self.target_name = target_name
                self.calls_per_statement = []
                self.current_statement_calls = 0
                self.reductions = []
                self.all_call_args = []

            def visit_call_stmt(self, node):
                """Visit call statements (sequential recursive calls)"""
                if node.name == self.target_name:
                    self.current_statement_calls += 1
                    if node.args:
                        for arg in node.args:
                            arg_str = self._stringify_expr(arg)
                            self.reductions.append(arg_str)
                            self.all_call_args.append(arg_str)
                super().visit_call_stmt(node)

            def visit_return_stmt(self, node: ReturnStmt):
                """Visit return statements for calls in return expressions"""
                self.current_statement_calls = 0
                super().visit_return_stmt(node)
                if self.current_statement_calls > 0:
                    self.calls_per_statement.append(self.current_statement_calls)

            def visit_func_call_expr(self, node: FuncCallExpr):
                if node.name == self.target_name:
                    self.current_statement_calls += 1
                    if node.args:
                        for arg in node.args:
                            arg_str = self._stringify_expr(arg)
                            self.reductions.append(arg_str)
                            self.all_call_args.append(arg_str)
                super().visit_func_call_expr(node)

            def _stringify_expr(self, expr):
                """Convert expression to string for analysis"""

                if isinstance(expr, Var):
                    return expr.name

                if isinstance(expr, Number):
                    return str(expr.value)

                if isinstance(expr, BinOp):
                    left = self._stringify_expr(expr.left)
                    right = self._stringify_expr(expr.right)
                    return f"{left} {expr.op} {right}"

                return str(expr)

        counter = CallCounter(str(func_def.name))
        consecutive_calls = 0

        for stmt in func_def.body:
            counter.current_statement_calls = 0
            stmt.accept(counter)
            if counter.current_statement_calls > 0:
                consecutive_calls += counter.current_statement_calls
            elif consecutive_calls > 0:
                counter.calls_per_statement.append(consecutive_calls)
                consecutive_calls = 0

        if consecutive_calls > 0:
            counter.calls_per_statement.append(consecutive_calls)

        max_calls = (
            max(counter.calls_per_statement) if counter.calls_per_statement else 0
        )

        self.call_counts[str(func_def.name)] = max_calls
        self.problem_size_reduction[str(func_def.name)] = counter.reductions

    def _analyze_base_cases(self, func_def: SubroutineDef):
        """Identify base cases in the recursive function"""
        base_cases = []

        for stmt in func_def.body:
            if isinstance(stmt, IfElse):
                if stmt.then_branch and isinstance(stmt.then_branch[0], ReturnStmt):
                    base_cases.append(f"Base case detected: {stmt.cond}")
            elif isinstance(stmt, ReturnStmt):
                base_cases.append("Simple return (possible base case)")

        self.base_cases[str(func_def.name)] = base_cases

    def _build_recurrence_relation(
        self, func_name: str, func_def: SubroutineDef
    ) -> RecurrenceRelation:
        """
        Build the recurrence relation for the recursive function.
        """
        num_calls = self.call_counts.get(func_name, 0)
        reductions = self.problem_size_reduction.get(func_name, [])

        work_complexity = self._analyze_non_recursive_work(func_def)

        reduction_pattern = self._infer_reduction_pattern(reductions)

        if num_calls == 0:
            relation = f"T(n) = {work_complexity}"
        elif num_calls == 1:
            relation = f"T(n) = T({reduction_pattern}) + {work_complexity}"
        else:
            relation = f"T(n) = {num_calls}T({reduction_pattern}) + {work_complexity}"

        base_case = "T(1) = O(1)" if self.base_cases.get(func_name) else "T(0) = O(1)"

        solution, method, steps = self._solve_recurrence(
            relation, base_case, num_calls, reduction_pattern, work_complexity
        )

        return RecurrenceRelation(
            relation=relation,
            base_case=base_case,
            solution=solution,
            method=method,
            steps=steps,
        )

    def _analyze_non_recursive_work(self, func_def: SubroutineDef) -> str:
        """Analyze the work done in non-recursive parts of the function"""

        analyzer = WorkAnalyzer()
        for stmt in func_def.body:
            stmt.accept(analyzer)

        if analyzer.max_nesting == 0:
            return "O(1)"

        if analyzer.max_nesting == 1:
            return "O(n)"

        return f"O(n^{analyzer.max_nesting})"

    def _infer_reduction_pattern(self, reductions: List[str]) -> str:
        """Infer the problem size reduction pattern from recursive calls"""
        if not reductions:
            return "n-1"

        reduction_text = " ".join(reductions).lower()

        if (
            "div 2" in reduction_text
            or "/ 2" in reduction_text
            or "/2" in reduction_text
        ):
            return "n/2"

        if "mid" in reduction_text:
            if (
                "- 1" in reduction_text
                or "-1" in reduction_text
                or "+ 1" in reduction_text
                or "+1" in reduction_text
            ):
                return "n/2"
            return "n/2"

        if (
            "/ 3" in reduction_text
            or "/3" in reduction_text
            or "div 3" in reduction_text
        ):
            return "n/3"
        if (
            "- 1" in reduction_text or "-1" in reduction_text
        ) and "mid" not in reduction_text:
            return "n-1"

        if "- 2" in reduction_text or "-2" in reduction_text:
            return "n-1"

        return "n-1"

    def _solve_recurrence(
        self, relation: str, base_case: str, num_calls: int, reduction: str, work: str
    ) -> Tuple[str, str, List[str]]:
        """
        Solve the recurrence relation using appropriate methods
        and return the solution, method used, and step-by-step analysis.
        """
        steps = []

        if "n/" in reduction or "n/" in reduction.replace(" ", ""):
            if RecursionTreeAnalyzer.should_use_tree_method(num_calls, reduction):
                tree_result = self._solve_with_recursion_tree(
                    num_calls, reduction, work, steps
                )
                if tree_result:
                    return tree_result

            return self._solve_with_master_theorem(num_calls, reduction, work, steps)

        if num_calls == 1 and "n-1" in reduction and work == "O(1)":
            steps.append("Recurrence: T(n) = T(n-1) + O(1)")
            steps.append("This is a linear recursion with constant work per call")
            steps.append("Using substitution method:")
            steps.append("  T(n) = T(n-1) + c")
            steps.append("  T(n) = T(n-2) + 2c")
            steps.append("  T(n) = T(n-3) + 3c")
            steps.append("  ...")
            steps.append("  T(n) = T(1) + nc = O(n)")
            steps.append("Solution: T(n) = O(n)")
            return "O(n)", "substitution", steps

        if num_calls == 1 and "n-1" in reduction and work == "O(n)":
            steps.append("Recurrence: T(n) = T(n-1) + O(n)")
            steps.append("This is linear recursion with linear work per call")
            steps.append("Using substitution method:")
            steps.append("  T(n) = T(n-1) + n")
            steps.append("  T(n) = T(n-2) + (n-1) + n")
            steps.append("  T(n) = T(n-3) + (n-2) + (n-1) + n")
            steps.append("  ...")
            steps.append("  T(n) = 1 + 2 + 3 + ... + n = n(n+1)/2")
            steps.append("Solution: T(n) = O(n^2)")
            return "O(n^2)", "substitution", steps

        if num_calls >= 2:
            if "n-1" in reduction or "n - 1" in reduction:
                steps.append(f"Recurrence: T(n) = {num_calls}T(n-1) + {work}")
                steps.append(
                    "This is exponential recursion - multiple calls with linear reduction"
                )
                steps.append(
                    f"At each level, problem makes {num_calls} recursive calls"
                )
                steps.append("Tree depth: n levels")
                steps.append(
                    f"Total nodes in tree: 1 + {num_calls} + {num_calls}^2 + ... + {num_calls}^n"
                )
                steps.append(
                    f"This is a geometric series = ({num_calls}^(n+1) - 1) / ({num_calls} - 1)"
                )
                steps.append(f"Solution: T(n) = O({num_calls}^n)")
                return f"O({num_calls}^n)", "exponential-recursion", steps

            tree_result = self._solve_with_recursion_tree(
                num_calls, reduction, work, steps
            )
            if tree_result:
                return tree_result

            steps.append(f"Recurrence: T(n) = {num_calls}T({reduction}) + {work}")
            steps.append("Multiple recursive calls lead to exponential complexity")
            steps.append(f"Solution: T(n) = O({num_calls}^n)")
            return f"O({num_calls}^n)", "recursion-tree", steps

        return "O(n)", "substitution", ["Linear recursion with single call"]

    def _solve_with_recursion_tree(
        self, num_calls: int, reduction: str, work: str, steps: List[str]
    ) -> Optional[Tuple[str, str, List[str]]]:
        """
        Solve recurrence using Recursion Tree method with visualization
        """
        try:
            tree = RecursionTree.from_recurrence(num_calls, reduction, work)
            self.recursion_tree = tree

            complexity, method, tree_steps = tree.calculate_total_complexity()

            steps.extend(tree_steps)
            steps.append("")
            steps.append("Recursion Tree Structure:")
            visualization = tree.visualize()
            steps.extend(visualization.split("\n"))

            return complexity, "recursion-tree", steps

        except Exception:
            return None

    def _solve_with_master_theorem(
        self, a: int, reduction: str, work: str, steps: List[str]
    ) -> Tuple[str, str, List[str]]:
        """Apply Master Theorem for divide-and-conquer recurrences"""
        steps.append(f"Applying Master Theorem for T(n) = {a}T({reduction}) + {work}")

        b = 2
        if "/2" in reduction or "/ 2" in reduction:
            b = 2
        elif "/3" in reduction or "/ 3" in reduction:
            b = 3

        k = 0
        if work == "O(n)":
            k = 1
        elif "n^" in work:
            k = int(work.split("^")[1].replace(")", ""))

        log_b_a = self._log_approximation(a, b)

        steps.append(f"Parameters: a={a}, b={b}, f(n)={work}")
        steps.append(f"log_b(a) = log_{b}({a}) ≈ {log_b_a:.2f}")

        if k < log_b_a - 0.1:
            result = f"O(n^{log_b_a:.2f})"
            steps.append("Case 1: f(n) grows slower than n^log_b(a)")
            steps.append(f"Solution: T(n) = {result}")
            return result, "master-theorem-case1", steps

        if abs(k - log_b_a) < 0.1:
            result = f"O(n^{k}log(n))"
            steps.append("Case 2: f(n) grows at same rate as n^log_b(a)")
            steps.append(f"Solution: T(n) = {result}")
            return result, "master-theorem-case2", steps

        result = work
        steps.append("Case 3: f(n) grows faster than n^log_b(a)")
        steps.append(f"Solution: T(n) = {result}")
        return result, "master-theorem-case3", steps

    def _log_approximation(self, a: int, b: int) -> float:
        """Approximate log_b(a)"""
        import math

        return math.log(a) / math.log(b)

    def _analyze_best_case(
        self,
        func_name: str,
        recurrence: RecurrenceRelation,
        dp_result: Dict,
        pattern_match: Optional[Dict],
    ) -> CaseAnalysis:
        """Analyze best case complexity with DP and pattern awareness"""
        if pattern_match and pattern_match["confidence"] >= 0.7:
            pattern_complexity = pattern_match["complexity"]["best"]
            expr = pattern_complexity.replace("O(", "").replace(")", "")
            notations = create_complexity_notation(expr, tight_bound=False)

            explanation = f"Best case from pattern '{pattern_match['pattern']}': {pattern_match['note']}"
            evidence = [f"Pattern match confidence: {pattern_match['confidence']:.2f}"]

            return CaseAnalysis(
                case_type="best",
                big_o=notations["big_o"],
                omega=notations["omega"],
                theta=notations["theta"],
                explanation=explanation,
                recurrence_relation=str(recurrence),
                evidence=evidence,
            )

        if dp_result["is_dynamic_programming"]:
            impact = dp_result["complexity_impact"]
            if "O(n)" in impact:
                expr = "n"
            elif "O(n^2)" in impact or "O(n^2)" in impact:
                expr = "n^2"
            else:
                expr = recurrence.solution.replace("O(", "").replace(")", "")

            notations = create_complexity_notation(expr, tight_bound=True)
            explanation = f"Best case with {dp_result['dp_type']}: {impact}"
            evidence = dp_result["evidence"] + [f"DP type: {dp_result['dp_type']}"]

            return CaseAnalysis(
                case_type="best",
                big_o=notations["big_o"],
                omega=notations["omega"],
                theta=notations["theta"],
                explanation=explanation,
                recurrence_relation=str(recurrence),
                evidence=evidence,
            )

        expr = recurrence.solution.replace("O(", "").replace(")", "")
        notations = create_complexity_notation(expr, tight_bound=True)
        explanation = "Best case occurs when recursion reaches base case quickly."

        return CaseAnalysis(
            case_type="best",
            big_o=notations["big_o"],
            omega=notations["omega"],
            theta=notations["theta"],
            explanation=explanation,
            recurrence_relation=str(recurrence),
            evidence=[f"Solved using {recurrence.method}"],
        )

    def _analyze_worst_case(
        self,
        func_name: str,
        recurrence: RecurrenceRelation,
        dp_result: Dict,
        pattern_match: Optional[Dict],
    ) -> CaseAnalysis:
        """Analyze worst case complexity with DP and pattern awareness"""
        if pattern_match and pattern_match["confidence"] >= 0.7:
            pattern_complexity = pattern_match["complexity"]["worst"]
            expr = pattern_complexity.replace("O(", "").replace(")", "")
            notations = create_complexity_notation(expr, tight_bound=False)

            explanation = f"Worst case from pattern '{pattern_match['pattern']}': {pattern_match['note']}"
            evidence = [
                f"Pattern match confidence: {pattern_match['confidence']:.2f}",
                f"Solved using {recurrence.method}",
            ]

            return CaseAnalysis(
                case_type="worst",
                big_o=notations["big_o"],
                omega=notations["omega"],
                theta=notations["theta"],
                explanation=explanation,
                recurrence_relation=str(recurrence),
                evidence=evidence,
            )

        if dp_result["is_dynamic_programming"]:
            impact = dp_result["complexity_impact"]
            if "O(n)" in impact:
                expr = "n"
            elif "O(n^2)" in impact or "O(n^2)" in impact:
                expr = "n^2"
            elif "O(n*W)" in impact:
                expr = "n*W"
            else:
                expr = recurrence.solution.replace("O(", "").replace(")", "")

            notations = create_complexity_notation(expr, tight_bound=True)
            explanation = f"Worst case with {dp_result['dp_type']}: {impact}"
            evidence = dp_result["evidence"]

            return CaseAnalysis(
                case_type="worst",
                big_o=notations["big_o"],
                omega=notations["omega"],
                theta=notations["theta"],
                explanation=explanation,
                recurrence_relation=str(recurrence),
                evidence=evidence,
            )

        expr = recurrence.solution.replace("O(", "").replace(")", "")
        notations = create_complexity_notation(expr, tight_bound=True)
        explanation = "Worst case follows full recursion depth."

        return CaseAnalysis(
            case_type="worst",
            big_o=notations["big_o"],
            omega=notations["omega"],
            theta=notations["theta"],
            explanation=explanation,
            recurrence_relation=str(recurrence),
            evidence=[f"Solved using {recurrence.method}"],
        )

    def _analyze_average_case(
        self,
        func_name: str,
        recurrence: RecurrenceRelation,
        dp_result: Dict,
        pattern_match: Optional[Dict],
    ) -> CaseAnalysis:
        """Analyze average case complexity with DP and pattern awareness"""
        if pattern_match and pattern_match["confidence"] >= 0.7:
            pattern_complexity = pattern_match["complexity"]["avg"]
            expr = pattern_complexity.replace("O(", "").replace(")", "")
            notations = create_complexity_notation(expr, tight_bound=False)

            explanation = f"Average case from pattern '{pattern_match['pattern']}'"
            evidence = [f"Pattern confidence: {pattern_match['confidence']:.2f}"]

            return CaseAnalysis(
                case_type="average",
                big_o=notations["big_o"],
                omega=notations["omega"],
                theta=notations["theta"],
                explanation=explanation,
                recurrence_relation=str(recurrence),
                evidence=evidence,
            )

        if dp_result["is_dynamic_programming"]:
            worst_case = self._analyze_worst_case(
                func_name, recurrence, dp_result, None
            )
            return CaseAnalysis(
                case_type="average",
                big_o=worst_case.big_o,
                omega=worst_case.omega,
                theta=worst_case.theta,
                explanation="Average case matches worst case for DP algorithms",
                recurrence_relation=str(recurrence),
                evidence=worst_case.evidence
                + ["DP typically has consistent performance"],
            )

        expr = recurrence.solution.replace("O(", "").replace(")", "")
        notations = create_complexity_notation(expr, tight_bound=True)

        return CaseAnalysis(
            case_type="average",
            big_o=notations["big_o"],
            omega=notations["omega"],
            theta=notations["theta"],
            explanation="Average case typically matches worst case for recursive algorithms",
            recurrence_relation=str(recurrence),
            evidence=[f"Based on {recurrence.method}"],
        )

    def _analyze_space_complexity(
        self, func_name: str, func_def: SubroutineDef
    ) -> Complexity:
        """Analyze space complexity (recursion depth + local variables)"""
        depth = self._calculate_recursion_depth_expr()
        return Complexity("O", depth, f"O({depth})", tight_bound=True)

    def _calculate_recursion_depth(self, recurrence: RecurrenceRelation) -> str:
        """Estimate recursion depth from recurrence relation"""
        if "n/2" in recurrence.relation:
            return "O(log(n))"

        if "n-1" in recurrence.relation:
            return "O(n)"

        return "O(n)"

    def _calculate_recursion_depth_expr(self) -> str:
        """Estimate recursion depth expression"""
        if (
            self.current_function
            and self.current_function in self.problem_size_reduction
        ):
            reductions = self.problem_size_reduction[self.current_function]
            if reductions and ("/ 2" in reductions[0] or "/2" in reductions[0]):
                return "log(n)"
            return "n"
        return "n"

    def _generate_explanation(
        self,
        func_name: str,
        recurrence: RecurrenceRelation,
        dp_result: Dict,
        pattern_match: Optional[Dict],
    ) -> str:
        """Generate detailed explanation with DP and pattern information"""
        explanation_parts = [f" Recursive Analysis for {func_name}:"]

        if pattern_match and pattern_match["confidence"] >= 0.5:
            explanation_parts.append(f"\nDetected Pattern: {pattern_match['pattern']}")
            explanation_parts.append(
                f"Pattern Confidence: {pattern_match['confidence']:.2%}"
            )
            explanation_parts.append(f"Note: {pattern_match['note']}")

        if dp_result["is_dynamic_programming"]:
            explanation_parts.append("\nDynamic Programming Detected:")
            explanation_parts.append(f"  Type: {dp_result['dp_type']}")
            explanation_parts.append(
                f"  Table Dimensions: {dp_result['table_dimensions']}D"
            )
            explanation_parts.append(
                f"  Complexity Impact: {dp_result['complexity_impact']}"
            )
            explanation_parts.append("\n  Evidence:")
            for evidence in dp_result["evidence"]:
                explanation_parts.append(f"    - {evidence}")

        explanation_parts.append(f"\nRecurrence Relation: {recurrence.relation}")
        explanation_parts.append(f"Base Case: {recurrence.base_case}")
        explanation_parts.append(f"\nSolution Method: {recurrence.method}")
        explanation_parts.append(f"Result: {recurrence.solution}")

        if self.recursion_tree:
            explanation_parts.append("\nRecursion Tree Analysis:")
            explanation_parts.append(self.recursion_tree.visualize())

        explanation_parts.append(
            "\nThe algorithm uses recursion to break down the problem."
        )
        explanation_parts.append(
            "The complexity is determined by the recurrence relation which captures:"
        )
        explanation_parts.append("  1. Number of recursive calls")
        explanation_parts.append("  2. Problem size reduction per call")
        explanation_parts.append("  3. Work done at each level")

        if recurrence.steps:
            explanation_parts.append("\nSolution Steps:")
            for step in recurrence.steps:
                explanation_parts.append(f"  {step}")

        return "\n".join(explanation_parts)

    def _generate_step_by_step(
        self,
        recurrence: RecurrenceRelation,
        dp_result: Dict,
        pattern_match: Optional[Dict],
    ) -> List[str]:
        """Generate step-by-step analysis with enhanced information"""
        steps = [
            f"1. Identified recurrence: {recurrence.relation}",
            f"2. Base case: {recurrence.base_case}",
        ]

        if pattern_match and pattern_match["confidence"] >= 0.5:
            steps.append(
                f"3. Detected pattern '{pattern_match['pattern']}' "
                f"with {pattern_match['confidence']:.0%} confidence"
            )

        if dp_result["is_dynamic_programming"]:
            steps.append(f"4. Dynamic Programming detected: {dp_result['dp_type']}")
            steps.append(
                f"   Complexity optimized to: {dp_result['complexity_impact']}"
            )

        step_num = len(steps) + 1
        steps.append(f"{step_num}. Applied {recurrence.method} to solve")

        if self.recursion_tree:
            steps.append(f"{step_num+1}. Built recursion tree visualization")

        steps.append(f"{len(steps)+1}. Final complexity: {recurrence.solution}")

        if recurrence.steps:
            steps.extend(recurrence.steps)

        return steps

    def _create_empty_result(self, name: str) -> ComplexityResult:
        """Create an empty complexity result for non-recursive algorithms"""
        empty_complexity = Complexity("O", "1", "O(1)")
        empty_case = CaseAnalysis(
            case_type="unknown",
            big_o=empty_complexity,
            omega=empty_complexity,
            explanation="Not a recursive algorithm",
        )

        return ComplexityResult(
            algorithm_name=name,
            algorithm_type="unknown",
            best_case=empty_case,
            average_case=empty_case,
            worst_case=empty_case,
            space_complexity=empty_complexity,
        )
