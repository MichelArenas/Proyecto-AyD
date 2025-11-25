"""
Iterative Algorithm Complexity Analyzer Module
"""

from typing import Dict, List, Optional

from app.core.analysis.techniques import LoopBoundsAnalyzer, PatternHeuristics
from app.core.language.ast import (Assignment, DefaultASTVisitor, ForLoop,
                                   IfElse, Program, RepeatUntil, SubroutineDef,
                                   VarDecl, WhileLoop)
from app.core.models import (CaseAnalysis, Complexity, ComplexityResult,
                             create_complexity_notation)


class IterativeAnalyzer(DefaultASTVisitor):
    """
    Analyze iterative algorithms for time and space complexity.
    """

    def __init__(self):
        self.loop_structures: List[Dict] = []
        self.current_nesting = 0
        self.max_nesting = 0
        self.conditional_branches: List[Dict] = []
        self.operations_count: Dict[str, int] = {}
        self.loop_bounds_analyzer = LoopBoundsAnalyzer()
        self.pattern_heuristics = PatternHeuristics()
        self.program_ast = None
        self.target_function = None

    def analyze(
        self, program: Program, function_name: Optional[str] = None
    ) -> ComplexityResult:
        """
        Analyze the given program or function for complexity.
        """
        self.loop_structures = []
        self.current_nesting = 0
        self.max_nesting = 0
        self.conditional_branches = []
        self.operations_count = {}
        self.program_ast = program

        target_code = None
        self.target_function = None

        if function_name:
            for stmt in program.statements:
                if isinstance(stmt, SubroutineDef) and stmt.name == function_name:
                    target_code = stmt.body
                    self.target_function = stmt
                    break

        if not target_code:
            target_code = [
                s for s in program.statements if not isinstance(s, (SubroutineDef,))
            ]

        loop_analysis = self.loop_bounds_analyzer.analyze(program, function_name)

        pattern_match = None
        if self.target_function:
            pattern_match = self.pattern_heuristics.detect_pattern(
                str(self.target_function.name), program, "iterative"
            )

        for stmt in target_code:
            stmt.accept(self)

        if pattern_match and pattern_match["confidence"] >= 0.7:
            best_case = self._create_case_from_pattern(
                "best", pattern_match, loop_analysis
            )
            worst_case = self._create_case_from_pattern(
                "worst", pattern_match, loop_analysis
            )
            average_case = self._create_case_from_pattern(
                "average", pattern_match, loop_analysis
            )
        else:
            best_case = self._calculate_best_case(loop_analysis)
            worst_case = self._calculate_worst_case(loop_analysis)
            average_case = self._calculate_average_case(loop_analysis)

        space_complexity = self._calculate_space_complexity()

        algorithm_name = function_name or "main"

        return ComplexityResult(
            algorithm_name=algorithm_name,
            algorithm_type="iterative",
            best_case=best_case,
            average_case=average_case,
            worst_case=worst_case,
            space_complexity=space_complexity,
            is_recursive=False,
            loop_structure=self._get_loop_summary(loop_analysis),
            dominant_operations=self._get_dominant_operations(loop_analysis),
            detailed_explanation=self._generate_explanation(
                algorithm_name, loop_analysis, pattern_match
            ),
            step_by_step_analysis=self._generate_step_by_step(
                loop_analysis, pattern_match
            ),
        )

    def visit_for_loop(self, node: ForLoop):
        """Analyze FOR loop"""
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)

        iterations = self._estimate_iterations(node)

        loop_info = {
            "type": "for",
            "nesting_level": self.current_nesting,
            "iterations": iterations,
            "variable": node.var,
            "complexity_contribution": iterations,
        }
        self.loop_structures.append(loop_info)

        for stmt in node.body:
            stmt.accept(self)

        self.current_nesting -= 1

    def visit_while_loop(self, node: WhileLoop):
        """Analyze WHILE loop"""
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)

        iterations = self._estimate_while_iterations(node)

        loop_info = {
            "type": "while",
            "nesting_level": self.current_nesting,
            "iterations": iterations,
            "condition": str(node.cond),
            "complexity_contribution": iterations,
        }
        self.loop_structures.append(loop_info)

        for stmt in node.body:
            stmt.accept(self)

        self.current_nesting -= 1

    def visit_repeat_until(self, node: RepeatUntil):
        """Analyze REPEAT-UNTIL loop"""
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)

        iterations = "n"

        loop_info = {
            "type": "repeat",
            "nesting_level": self.current_nesting,
            "iterations": iterations,
            "condition": str(node.cond),
            "complexity_contribution": iterations,
        }
        self.loop_structures.append(loop_info)

        for stmt in node.body:
            stmt.accept(self)

        self.current_nesting -= 1

    def visit_if_else(self, node: IfElse):
        """Analyze conditional branches"""
        branch_info = {
            "condition": str(node.cond),
            "has_else": len(node.else_branch) > 0,
            "then_complexity": self._analyze_branch_complexity(node.then_branch),
            "else_complexity": (
                self._analyze_branch_complexity(node.else_branch)
                if node.else_branch
                else "O(1)"
            ),
        }
        self.conditional_branches.append(branch_info)

        super().visit_if_else(node)

    def visit_assignment(self, node: Assignment):
        """Count assignments as O(1) operations"""
        self.operations_count["assignments"] = (
            self.operations_count.get("assignments", 0) + 1
        )
        super().visit_assignment(node)

    def visit_print_stmt(self, node):
        """Count print statements as O(1) operations"""
        self.operations_count["print_operations"] = (
            self.operations_count.get("print_operations", 0) + 1
        )
        if hasattr(node, "value") and hasattr(node.value, "accept"):
            node.value.accept(self)

    def _estimate_iterations(self, node: ForLoop) -> str:
        """
        Estimate iterations for FOR loop based on range pattern.
        """
        end_expr = str(node.end)

        if "length" in end_expr.lower():
            return "n"
        if "/" in end_expr or "div" in end_expr:
            if "2" in end_expr:
                return "n/2"
            return "n/k"
        return "n"

    def _estimate_while_iterations(self, node: WhileLoop) -> str:
        """
        Estimate iterations for WHILE loop based on condition.
        """
        condition = str(node.cond)

        if "/" in condition or "div" in condition.lower():
            return "log(n)"
        if "*" in condition:
            return "n"
        return "n"

    def _analyze_branch_complexity(self, branch: List) -> str:
        """Analyze complexity of a conditional branch"""
        if not branch:
            return "O(1)"

        has_loop = any(
            isinstance(stmt, (ForLoop, WhileLoop, RepeatUntil)) for stmt in branch
        )

        return "O(n)" if has_loop else "O(1)"

    def _create_case_from_pattern(
        self, case_type: str, pattern_match: Dict, loop_analysis: Dict
    ) -> CaseAnalysis:
        """Create case analysis from pattern match"""
        case_key_map = {"best": "best", "worst": "worst", "average": "avg"}

        complexity_key = case_key_map.get(case_type, "worst")
        complexity_str = pattern_match["complexity"].get(
            complexity_key, pattern_match["complexity"]["worst"]
        )

        if complexity_str.startswith("O(") and complexity_str.endswith(")"):
            complexity_expr = complexity_str[2:-1]
        else:
            complexity_expr = complexity_str

        notations = create_complexity_notation(complexity_expr, tight_bound=True)

        explanation = (
            f"Pattern '{pattern_match['pattern']}' detected "
            f"({pattern_match['confidence']:.0%} confidence): {pattern_match['note']}"
        )

        evidence = [
            f"Pattern: {pattern_match['pattern']}",
            f"Confidence: {pattern_match['confidence']:.2%}",
            pattern_match["note"],
        ]

        if loop_analysis.get("loops"):
            evidence.append(f"Total loops analyzed: {len(loop_analysis['loops'])}")
            for loop_info in loop_analysis["loops"][:3]:
                iterations = loop_info.get(
                    "iteration_pattern", loop_info.get("exact_iterations", "n")
                )
                pattern = loop_info.get("type", "unknown")
                evidence.append(f"Loop: {iterations} iterations, Type: {pattern}")

        return CaseAnalysis(
            case_type=case_type,
            big_o=notations["big_o"],
            omega=notations["omega"],
            theta=notations["theta"],
            explanation=explanation,
            evidence=evidence,
        )

    def _calculate_best_case(self, loop_analysis: Dict) -> CaseAnalysis:
        """
        Calculate best case complexity with early exit analysis.
        """
        if not self.loop_structures:
            return self._create_constant_case_analysis(
                "best",
                "No loops or recursion - constant time operations only",
                ["No iterative structures found"],
            )

        early_exits = loop_analysis.get("early_exits", [])
        has_early_exit = any(
            exit_info.get("can_exit_early", False) for exit_info in early_exits
        )

        if has_early_exit:
            complexity_expr = "1"
            explanation = "Best case when early exit condition is met immediately"
            evidence = [
                "Early exit detected in loop",
                f"Exit conditions: {len(early_exits)}",
            ]
            for exit_info in early_exits[:2]:
                evidence.append(f"Exit type: {exit_info.get('type', 'unknown')}")
        elif self.max_nesting == 1:
            first_loop = loop_analysis.get("loops", [{}])[0]
            complexity_expr = first_loop.get(
                "iteration_pattern", first_loop.get("exact_iterations", "n")
            )
            explanation = f"Best case with single loop: {complexity_expr} iterations"
            evidence = [
                f"Loop type: {first_loop.get('type', 'unknown')}",
                f"Iterations: {complexity_expr}",
            ]
        else:
            complexity_expr = self._calculate_nested_complexity()
            explanation = f"Best case with {self.max_nesting} level(s) of nesting"
            evidence = [
                f"Loop nesting depth: {self.max_nesting}",
                f"Total loops: {len(self.loop_structures)}",
            ]

        notations = create_complexity_notation(complexity_expr, tight_bound=True)

        return CaseAnalysis(
            case_type="best",
            big_o=notations["big_o"],
            omega=notations["omega"],
            theta=notations["theta"],
            explanation=explanation,
            evidence=evidence,
        )

    def _calculate_worst_case(self, loop_analysis: Dict) -> CaseAnalysis:
        """
        Calculate worst case complexity using precise loop bounds.
        """
        if not self.loop_structures:
            return self._create_constant_case_analysis(
                "worst", "No loops - constant time", ["No iterative structures"]
            )

        if self.max_nesting == 0:
            complexity_expr = "1"
        elif self.max_nesting == 1:
            loops = loop_analysis.get("loops", [])
            if loops:
                first_loop = loops[0]
                complexity_expr = first_loop.get(
                    "iteration_pattern", first_loop.get("exact_iterations", "n")
                )

                if "log" in str(complexity_expr).lower():
                    complexity_expr = "log(n)"
                elif "/2" in str(complexity_expr) or "n/2" in str(complexity_expr):
                    complexity_expr = "n/2"
            else:
                complexity_expr = self._get_single_loop_complexity()
        else:
            complexity_expr = self._calculate_nested_complexity()

        notations = create_complexity_notation(complexity_expr, tight_bound=True)

        explanation = self._explain_worst_case(loop_analysis)
        evidence = self._gather_evidence(loop_analysis)

        return CaseAnalysis(
            case_type="worst",
            big_o=notations["big_o"],
            omega=notations["omega"],
            theta=notations["theta"],
            explanation=explanation,
            evidence=evidence,
        )

    def _calculate_average_case(self, loop_analysis: Dict) -> CaseAnalysis:
        """
        Calculate average case complexity.
        """
        worst = self._calculate_worst_case(loop_analysis)

        return CaseAnalysis(
            case_type="average",
            big_o=worst.big_o,
            omega=worst.omega,
            theta=worst.theta,
            explanation="Average case typically matches worst case for iterative algorithms",
            evidence=worst.evidence
            + ["Average case analysis based on expected iterations"],
        )

    def _get_single_loop_complexity(self) -> str:
        """Get complexity for single loop"""
        if self.loop_structures:
            first_loop = self.loop_structures[0]
            iterations = first_loop.get("iterations", "n")
            return iterations
        return "n"

    def _calculate_nested_complexity(self) -> str:
        """Calculate complexity for nested loops"""
        loops_by_level: Dict[int, List] = {}
        for loop in self.loop_structures:
            level = loop.get("nesting_level", 1)
            if level not in loops_by_level:
                loops_by_level[level] = []
            loops_by_level[level].append(loop)

        if self.max_nesting == 2:
            return "n^2"

        if self.max_nesting == 3:
            return "n^3"

        if self.max_nesting > 3:
            return f"n^{self.max_nesting}"

        return "n"

    def _explain_worst_case(self, loop_analysis: Dict) -> str:
        """Generate explanation for worst case"""
        if self.max_nesting == 0:
            return "No loops present - constant time operations only"

        if self.max_nesting == 1:
            loops = loop_analysis.get("loops", [])
            if loops:
                first_loop = loops[0]
                iter_pattern = first_loop.get(
                    "iteration_pattern", first_loop.get("exact_iterations", "n")
                )
                loop_type = first_loop.get("type", "unknown")

                if "log" in str(iter_pattern).lower():
                    return "Single loop with logarithmic pattern: log(n) iterations"

                if "/2" in str(iter_pattern):
                    return (
                        f"Single loop iterating through half: {iter_pattern} iterations"
                    )
                return f"Single {loop_type} loop: {iter_pattern} iterations"
            return f"Single loop iterating {self._get_single_loop_complexity()} times"

        return f"Nested loops with depth {self.max_nesting} result in polynomial time complexity"

    def _gather_evidence(self, loop_analysis: Dict) -> List[str]:
        """Gather evidence for complexity analysis with precise loop bounds"""
        evidence = [
            f"Maximum loop nesting depth: {self.max_nesting}",
            f"Total number of loops: {len(self.loop_structures)}",
        ]

        loops = loop_analysis.get("loops", [])
        for i, loop in enumerate(loops[:5]):
            loop_type = loop.get("type", "unknown")
            iterations = loop.get(
                "iteration_pattern", loop.get("exact_iterations", "n")
            )
            evidence.append(f"Loop {i+1}: {loop_type}, ~{iterations} iterations")

        early_exits = loop_analysis.get("early_exits", [])
        if early_exits:
            evidence.append(f"Early exits detected: {len(early_exits)}")
            for exit_info in early_exits[:2]:
                if exit_info.get("can_exit_early"):
                    evidence.append(
                        f"  {exit_info.get('type', 'unknown')} can exit early"
                    )

        if self.conditional_branches:
            evidence.append(f"Conditional branches: {len(self.conditional_branches)}")

        return evidence

    def _create_constant_case_analysis(
        self, case_type: str, explanation: str, evidence: List[str]
    ) -> CaseAnalysis:
        """
        Create a constant time case analysis.
        """
        notations = create_complexity_notation("1", tight_bound=True)

        return CaseAnalysis(
            case_type=case_type,
            big_o=notations["big_o"],
            omega=notations["omega"],
            theta=notations["theta"],
            explanation=explanation,
            evidence=evidence,
        )

    def _calculate_space_complexity(self) -> Complexity:
        """Calculate space complexity including auxiliary structures"""
        space = "1"
        auxiliary_structures = []

        if self.program_ast:
            for stmt in self.program_ast.statements:
                if isinstance(stmt, SubroutineDef):
                    for body_stmt in stmt.body:
                        if isinstance(body_stmt, VarDecl):
                            for item in body_stmt.items:
                                item_str = str(item)
                                if "[" in item_str:
                                    dimensions = item_str.count("[")
                                    if dimensions == 1:
                                        auxiliary_structures.append("array[n]")
                                        space = "n"
                                    elif dimensions == 2:
                                        auxiliary_structures.append("matrix[n][m]")
                                        space = "n^2"
                                    else:
                                        auxiliary_structures.append(
                                            f"array[{dimensions}D]"
                                        )
                                        space = f"n^{dimensions}"

        if space == "1" and self.max_nesting > 1:
            space = "1"

        return Complexity("O", space, f"O({space})", tight_bound=True)

    def _get_loop_summary(self, loop_analysis: Dict) -> Dict:
        """Get summary of loop structures with precise analysis"""
        loops = loop_analysis.get("loops", [])

        return {
            "max_nesting": self.max_nesting,
            "total_loops": len(self.loop_structures),
            "loop_types": [loop["type"] for loop in self.loop_structures],
            "has_conditionals": len(self.conditional_branches) > 0,
            "precise_iterations": [
                loop.get("iteration_pattern", loop.get("exact_iterations", "n"))
                for loop in loops
            ],
            "loop_patterns": [loop.get("type", "unknown") for loop in loops],
            "has_early_exits": any(
                exit_info.get("can_exit_early", False)
                for exit_info in loop_analysis.get("early_exits", [])
            ),
        }

    def _get_dominant_operations(self, loop_analysis: Dict) -> List[str]:
        """Identify dominant operations with precise analysis"""
        operations = []

        if self.loop_structures:
            operations.append(f"Loop iterations (nested depth: {self.max_nesting})")

            loops = loop_analysis.get("loops", [])
            for loop in loops[:3]:
                loop_type = loop.get("type", "unknown")
                iterations = loop.get(
                    "iteration_pattern", loop.get("exact_iterations", "n")
                )
                operations.append(f"  {loop_type} loop: {iterations} iterations")

        if self.operations_count.get("assignments", 0) > 0:
            operations.append(f"Assignments: {self.operations_count['assignments']}")

        return operations

    def _generate_explanation(
        self, algorithm_name: str, loop_analysis: Dict, pattern_match: Optional[Dict]
    ) -> str:
        """Generate detailed explanation with pattern and loop analysis"""
        explanation_parts = [f"  Iterative Analysis for {algorithm_name}:"]

        if pattern_match and pattern_match["confidence"] >= 0.5:
            explanation_parts.append(f"\nDetected Pattern: {pattern_match['pattern']}")
            explanation_parts.append(
                f"Pattern Confidence: {pattern_match['confidence']:.2%}"
            )
            explanation_parts.append(f"Note: {pattern_match['note']}")

        explanation_parts.append("\nLoop Structure:")
        explanation_parts.append(f"- Maximum nesting depth: {self.max_nesting}")
        explanation_parts.append(f"- Total loops: {len(self.loop_structures)}")

        loops = loop_analysis.get("loops", [])
        for i, loop in enumerate(loops[:5]):
            loop_type = loop.get("type", "unknown")
            iterations = loop.get(
                "iteration_pattern", loop.get("exact_iterations", "n")
            )
            explanation_parts.append(
                f"Loop {i+1}: {loop_type}, ~{iterations} iterations"
            )

        early_exits = loop_analysis.get("early_exits", [])
        if early_exits:
            explanation_parts.append(f"\nEarly Exits: {len(early_exits)} detected")
            for exit_info in early_exits[:2]:
                if exit_info.get("can_exit_early"):
                    explanation_parts.append(
                        f"  - {exit_info.get('type', 'unknown')} can terminate early"
                    )

        if self.conditional_branches:
            explanation_parts.append(
                f"\nConditional branches: {len(self.conditional_branches)}"
            )

        explanation_parts.append(
            f"\nDominant complexity: O({self._calculate_nested_complexity()})"
        )

        return "\n".join(explanation_parts)

    def _generate_step_by_step(
        self, loop_analysis: Dict, pattern_match: Optional[Dict]
    ) -> List[str]:
        """Generate step-by-step analysis with enhanced information"""
        steps = []

        if pattern_match and pattern_match["confidence"] >= 0.5:
            steps.append(
                f"1. Detected pattern '{pattern_match['pattern']}' "
                f"with {pattern_match['confidence']:.0%} confidence"
            )

        step_num = len(steps) + 1
        steps.append(f"{step_num}. Analyzed loop structures and nesting levels")
        steps.append(
            f"{step_num+1}. Identified {len(self.loop_structures)} loops "
            f"with max nesting {self.max_nesting}"
        )

        loops = loop_analysis.get("loops", [])
        if loops:
            step_num = len(steps) + 1
            steps.append(f"{step_num}. Precise loop analysis:")
            for i, loop in enumerate(loops[:3]):
                loop_type = loop.get("type", "unknown")
                iterations = loop.get(
                    "iteration_pattern", loop.get("exact_iterations", "n")
                )
                steps.append(f"     Loop {i+1}: {loop_type}, {iterations} iterations")

        early_exits = loop_analysis.get("early_exits", [])
        if any(e.get("can_exit_early") for e in early_exits):
            step_num = len(steps) + 1
            steps.append(f"{step_num}. Early exit conditions detected")

        step_num = len(steps) + 1
        if self.max_nesting == 0:
            steps.append(f"{step_num}. No loops found - constant time O(1)")
        elif self.max_nesting == 1:
            complexity = (
                loops[0].get("iteration_pattern", loops[0].get("exact_iterations", "n"))
                if loops
                else "n"
            )
            steps.append(f"{step_num}. Single loop with O({complexity}) iterations")
        else:
            steps.append(
                f"{step_num}. Nested loops contribute "
                f"O({self._calculate_nested_complexity()}) complexity"
            )

        steps.append(
            f"{len(steps)+1}. Space complexity: "
            f"O({self._calculate_space_complexity().expression})"
        )

        return steps
