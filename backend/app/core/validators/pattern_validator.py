"""
Module for validating and detecting algorithmic patterns in the AST of a program.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.language.ast import (ArrayAccess, Assignment, ASTNode, BinOp,
                                   CallStmt, ForLoop, FuncCallExpr, IfElse,
                                   Program, RepeatUntil, ReturnStmt,
                                   SubroutineDef, VarTarget, WhileLoop)


@dataclass
class PatternDetection:
    pattern_type: str
    confidence: float
    location: str
    description: str
    evidence: List[str]


@dataclass
class RecursionInfo:
    function_name: str
    is_tail_recursive: bool
    recursive_calls: int
    base_cases: int
    parameters_modified: bool


class PatternValidator:
    def __init__(self):
        self.patterns: List[PatternDetection] = []
        self.recursion_info: Dict[str, RecursionInfo] = {}
        self.current_function: Optional[str] = None
        self.function_calls: Dict[str, List[str]] = {}
        self.loop_nesting: int = 0
        self.conditional_nesting: int = 0

    def validate_patterns(self, ast_root: ASTNode) -> List[PatternDetection]:
        self.patterns = []
        self.recursion_info = {}
        self.function_calls = {}

        self._collect_function_info(ast_root)
        self._detect_patterns(ast_root)

        return self.patterns

    def _collect_function_info(self, node: ASTNode) -> None:
        if isinstance(node, SubroutineDef) and node.name:
            self.current_function = str(node.name)
            self.function_calls[str(node.name)] = []

            self._analyze_recursion(node)

        elif (
            isinstance(node, FuncCallExpr)
            and self.current_function
            and hasattr(node, "name")
        ):
            self.function_calls[self.current_function].append(str(node.name))

        elif (
            isinstance(node, CallStmt)
            and self.current_function
            and hasattr(node, "name")
        ):
            self.function_calls[self.current_function].append(str(node.name))

        self._visit_children(node)

    def _analyze_recursion(self, func_node: SubroutineDef) -> None:
        if not func_node.name:
            return

        func_name = str(func_node.name)
        recursive_calls = 0
        base_cases = 0
        is_tail_recursive = True
        parameters_modified = False

        for stmt in func_node.body:
            if self._contains_recursive_call(stmt, func_name):
                recursive_calls += 1
                if not self._is_tail_recursive_call(stmt, func_name):
                    is_tail_recursive = False

            if self._is_base_case(stmt):
                base_cases += 1

            if self._modifies_parameters(stmt, func_node.parameters):
                parameters_modified = True

        if recursive_calls > 0:
            self.recursion_info[func_name] = RecursionInfo(
                function_name=func_name,
                is_tail_recursive=is_tail_recursive and recursive_calls > 0,
                recursive_calls=recursive_calls,
                base_cases=base_cases,
                parameters_modified=parameters_modified,
            )

    def _detect_patterns(self, node: ASTNode) -> None:
        if isinstance(node, Program):
            self._detect_divide_and_conquer(node)
            self._detect_dynamic_programming(node)
            self._detect_greedy_patterns(node)
            self._detect_backtracking(node)

        elif isinstance(node, SubroutineDef) and node.name:
            self.current_function = str(node.name)
            self._detect_function_patterns(node)

        elif isinstance(node, (ForLoop, WhileLoop, RepeatUntil)):
            self.loop_nesting += 1
            self._detect_loop_patterns(node)
            self._visit_children(node)
            self.loop_nesting -= 1
            return

        elif isinstance(node, IfElse):
            self.conditional_nesting += 1
            self._visit_children(node)
            self.conditional_nesting -= 1
            return

        self._visit_children(node)

    def _detect_divide_and_conquer(self, program: Program) -> None:
        for func_name, recursion in self.recursion_info.items():
            if recursion.recursive_calls >= 2:
                confidence = 0.7
                evidence = [
                    f"Recursive function with {recursion.recursive_calls} recursive calls"
                ]

                if recursion.base_cases > 0:
                    confidence += 0.2
                    evidence.append(f"Has {recursion.base_cases} identified base cases")

                if self._has_problem_division(func_name):
                    confidence += 0.1
                    evidence.append("Evidence of problem division")

                self.patterns.append(
                    PatternDetection(
                        pattern_type="Divide and Conquer",
                        confidence=min(confidence, 1.0),
                        location=f"Function {func_name}",
                        description="Divide and conquer pattern detected by multiple recursive calls",
                        evidence=evidence,
                    )
                )

    def _detect_dynamic_programming(self, program: Program) -> None:
        """Detects dynamic programming patterns."""
        for func_name, _ in self.function_calls.items():
            if self._has_memoization(func_name):
                confidence = 0.8
                evidence = ["Use of memoization or result table detected"]

                if func_name in self.recursion_info:
                    evidence.append(
                        "Recursive function with possible subproblem overlap"
                    )
                    confidence += 0.1

                self.patterns.append(
                    PatternDetection(
                        pattern_type="Dynamic Programming",
                        confidence=min(confidence, 1.0),
                        location=f"Function {func_name}",
                        description="Dynamic programming pattern detected",
                        evidence=evidence,
                    )
                )

    def _detect_greedy_patterns(self, program: Program) -> None:
        """Detects greedy algorithm patterns."""
        for func_name, calls in self.function_calls.items():
            if self._has_greedy_selection(func_name):
                confidence = 0.6
                evidence = ["Local optimal choice selection detected"]

                if self._has_optimization_criteria(func_name):
                    confidence += 0.2
                    evidence.append("Optimization criteria identified")

                self.patterns.append(
                    PatternDetection(
                        pattern_type="Greedy Algorithm",
                        confidence=min(confidence, 1.0),
                        location=f"Function {func_name}",
                        description="Greedy algorithm pattern detected",
                        evidence=evidence,
                    )
                )

    def _detect_backtracking(self, program: Program) -> None:
        """Detects backtracking patterns."""
        for func_name, recursion in self.recursion_info.items():
            if self._has_backtracking_pattern(func_name):
                confidence = 0.7
                evidence = ["Backtracking pattern detected"]

                if recursion.recursive_calls > 0:
                    evidence.append("Recursive function that explores alternatives")
                    confidence += 0.2

                self.patterns.append(
                    PatternDetection(
                        pattern_type="Backtracking",
                        confidence=min(confidence, 1.0),
                        location=f"Function {func_name}",
                        description="Backtracking pattern for solution exploration",
                        evidence=evidence,
                    )
                )

    def _detect_function_patterns(self, func: SubroutineDef) -> None:
        """Detects function-specific patterns."""
        if self._is_helper_function(func):
            self.patterns.append(
                PatternDetection(
                    pattern_type="Helper Function",
                    confidence=0.8,
                    location=f"Function {func.name}",
                    description="Helper function detected",
                    evidence=["Function used as helper in main algorithm"],
                )
            )

    def _detect_loop_patterns(self, loop_node: ASTNode) -> None:
        """Detects patterns in loops."""
        if self.loop_nesting > 2:
            self.patterns.append(
                PatternDetection(
                    pattern_type="Nested Loops",
                    confidence=0.9,
                    location=f"Function {self.current_function or 'unknown'}",
                    description=f"Nested loops at level {self.loop_nesting}",
                    evidence=[
                        f"Loop nesting at level {self.loop_nesting} may indicate O(n^{self.loop_nesting}) complexity"
                    ],
                )
            )

    def _contains_recursive_call(self, node: ASTNode, func_name: str) -> bool:
        """Checks if a node contains a recursive call."""
        if isinstance(node, FuncCallExpr) and node.name == func_name:
            return True
        if isinstance(node, CallStmt) and node.name == func_name:
            return True

        return self._search_in_children(
            node, lambda n: self._contains_recursive_call(n, func_name)
        )

    def _is_tail_recursive_call(self, node: ASTNode, func_name: str) -> bool:
        """Checks if a recursive call is tail recursion."""
        if isinstance(node, ReturnStmt) and node.value:
            return (
                isinstance(node.value, (FuncCallExpr, CallStmt))
                and getattr(node.value, "name", None) == func_name
            )
        return False

    def _is_base_case(self, node: ASTNode) -> bool:
        """Detects base cases in recursion."""
        if isinstance(node, ReturnStmt):
            return True
        if isinstance(node, IfElse):
            return any(isinstance(stmt, ReturnStmt) for stmt in node.then_branch)
        return False

    def _modifies_parameters(self, node: ASTNode, parameters: List[Any]) -> bool:
        """Checks if function parameters are modified."""
        if isinstance(node, Assignment):
            target = node.target
            if isinstance(target, VarTarget):
                param_names = [p.name for p in parameters] if parameters else []
                return target.name in param_names
        return False

    def _has_problem_division(self, func_name: str) -> bool:
        """Detects evidence of problem division."""
        return (
            func_name in self.recursion_info
            and self.recursion_info[func_name].recursive_calls >= 2
        )

    def _has_memoization(self, func_name: str) -> bool:
        """Detects memoization pattern."""
        calls = self.function_calls.get(func_name, [])
        return any(
            "tabla" in call.lower() or "memo" in call.lower() or "cache" in call.lower()
            for call in calls
        )

    def _has_greedy_selection(self, func_name: str) -> bool:
        """Detects greedy selection pattern."""
        calls = self.function_calls.get(func_name, [])
        greedy_keywords = ["max", "min", "mejor", "optimo", "maximo", "minimo"]
        return any(
            any(keyword in call.lower() for keyword in greedy_keywords)
            for call in calls
        )

    def _has_optimization_criteria(self, func_name: str) -> bool:
        """Detects optimization criteria."""
        calls = self.function_calls.get(func_name, [])
        optimization_keywords = ["costo", "peso", "distancia", "beneficio", "valor"]
        return any(
            any(keyword in call.lower() for keyword in optimization_keywords)
            for call in calls
        )

    def _has_backtracking_pattern(self, func_name: str) -> bool:
        """Detects backtracking pattern."""
        calls = self.function_calls.get(func_name, [])
        backtrack_keywords = ["undo", "revert", "backtrack", "deshacer", "explorar"]
        return any(
            any(keyword in call.lower() for keyword in backtrack_keywords)
            for call in calls
        )

    def _is_helper_function(self, func: SubroutineDef) -> bool:
        """Detects if it is a helper function."""
        if not func.name:
            return False
        helper_indicators = ["helper", "aux", "util", "auxiliar"]
        return any(
            indicator in str(func.name).lower() for indicator in helper_indicators
        )

    def _search_in_children(self, node: ASTNode, predicate: Any) -> bool:
        """Recursively search in child nodes."""
        for child in self._get_children(node):
            if predicate(child) or self._search_in_children(child, predicate):
                return True
        return False

    def _visit_children(self, node: ASTNode) -> None:
        """Visit all child nodes."""
        for child in self._get_children(node):
            self._detect_patterns(child)

    def _get_children(self, node: ASTNode) -> List[ASTNode]:
        children = []

        if isinstance(node, Program):
            children.extend(node.statements)

        elif isinstance(node, SubroutineDef):
            if node.parameters:
                children.extend(node.parameters)
            children.extend(node.body)

        elif isinstance(node, ForLoop):
            if hasattr(node, "start") and node.start:
                children.append(node.start)
            if hasattr(node, "end") and node.end:
                children.append(node.end)
            children.extend(node.body)

        elif isinstance(node, WhileLoop):
            if hasattr(node, "cond") and node.cond:
                children.append(node.cond)
            children.extend(node.body)

        elif isinstance(node, RepeatUntil):
            children.extend(node.body)
            if node.cond:
                children.append(node.cond)

        elif isinstance(node, IfElse):
            children.append(node.cond)
            children.extend(node.then_branch)
            if node.else_branch:
                children.extend(node.else_branch)

        elif isinstance(node, Assignment):
            children.append(node.target)
            children.append(node.value)

        elif isinstance(node, FuncCallExpr):
            children.extend(node.args)

        elif isinstance(node, BinOp):
            children.append(node.left)
            children.append(node.right)

        elif isinstance(node, ArrayAccess):
            if hasattr(node, "index") and node.index:
                children.extend(node.index)

        return [child for child in children if isinstance(child, ASTNode)]

    def get_pattern_summary(self) -> Dict[str, int]:
        summary = {}
        for pattern in self.patterns:
            pattern_type = pattern.pattern_type
            summary[pattern_type] = summary.get(pattern_type, 0) + 1
        return summary

    def get_high_confidence_patterns(
        self, threshold: float = 0.7
    ) -> List[PatternDetection]:
        return [p for p in self.patterns if p.confidence >= threshold]
