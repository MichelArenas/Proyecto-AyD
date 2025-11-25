"""
Dynamic Programming Pattern Detector for Pseudocode Analysis
"""

from typing import Dict, List, Optional

from app.core.language.ast import (Assignment, DefaultASTVisitor, ForLoop,
                                   IfElse, Program, SubroutineDef, VarDecl)


class DynamicProgrammingDetector(DefaultASTVisitor):
    """
    Detect dynamic programming patterns in pseudocode.
    """

    def __init__(self):
        self.has_memo_table = False
        self.has_bottom_up_loop = False
        self.has_subproblem_access = False
        self.memo_variable = None
        self.dp_table_dimensions = 0
        self.evidence: List[str] = []

    def detect(self, program: Program, function_name: Optional[str] = None) -> Dict:
        """
        Detect DP patterns in the given program.
        """
        self._reset()

        target_func = None
        if function_name:
            for stmt in program.statements:
                if isinstance(stmt, SubroutineDef) and stmt.name == function_name:
                    target_func = stmt
                    break

        if target_func:
            self._analyze_function(target_func)
        else:
            for stmt in program.statements:
                if isinstance(stmt, SubroutineDef):
                    self._analyze_function(stmt)

        is_dp = self.has_memo_table or (
            self.has_bottom_up_loop and self.has_subproblem_access
        )

        dp_type = self._classify_dp_type()
        complexity_impact = self._estimate_complexity_impact()

        return {
            "is_dynamic_programming": is_dp,
            "dp_type": dp_type,
            "has_memoization": self.has_memo_table,
            "has_bottom_up": self.has_bottom_up_loop,
            "table_dimensions": self.dp_table_dimensions,
            "complexity_impact": complexity_impact,
            "evidence": self.evidence,
        }

    def _reset(self):
        """Reset detection state"""
        self.has_memo_table = False
        self.has_bottom_up_loop = False
        self.has_subproblem_access = False
        self.memo_variable = None
        self.dp_table_dimensions = 0
        self.evidence = []

    def _analyze_function(self, func_def: SubroutineDef):
        """Analyze a single function for DP patterns"""
        for stmt in func_def.body:
            stmt.accept(self)

    def visit_var_decl(self, node: VarDecl):
        """Check for memoization table declarations"""
        for item in node.items:
            item_str = str(item)

            if "[" in item_str:
                dimensions = item_str.count("[")

                var_name = item_str.split("[", maxsplit=1)[0].strip()
                if any(
                    keyword in var_name.lower()
                    for keyword in ["memo", "dp", "table", "cache", "opt"]
                ):
                    self.has_memo_table = True
                    self.memo_variable = var_name
                    self.dp_table_dimensions = dimensions
                    self.evidence.append(
                        f"Memoization table '{var_name}' with {dimensions}D array"
                    )

    def visit_for_loop(self, node: ForLoop):
        """Check for bottom-up iteration patterns"""
        start_str = str(node.start).strip()
        end_str = str(node.end).strip()

        if start_str in ["0", "1"] and any(
            term in end_str for term in ["n", "length", "size"]
        ):
            self.has_bottom_up_loop = True
            self.evidence.append(
                f"Bottom-up iteration: for {node.var} <- {start_str} to {end_str}"
            )

        super().visit_for_loop(node)

    def visit_assignment(self, node: Assignment):
        """Check for subproblem access and optimal combination"""
        rhs = str(node.value)
        lhs = str(node.target)

        if any(pattern in rhs for pattern in ["-1]", "-2]", "[i-1", "[j-1", "[k-1"]):
            self.has_subproblem_access = True
            self.evidence.append(f"Subproblem access in: {lhs} <- {rhs}")

        if any(op in rhs for op in ["min(", "max(", " + ", "max", "min"]):
            if self.has_subproblem_access:
                self.evidence.append(f"Optimal substructure: {rhs}")

        super().visit_assignment(node)

    def visit_if_else(self, node: IfElse):
        """Check for memoization checks in conditionals"""
        condition = str(node.cond)

        if self.memo_variable and self.memo_variable in condition:
            if "NULL" in condition or "!=" in condition or "=" in condition:
                self.evidence.append(f"Memoization check: if {condition}")

        super().visit_if_else(node)

    def _classify_dp_type(self) -> Optional[str]:
        """
        Classify the type of dynamic programming used.
        """
        if not (
            self.has_memo_table
            or (self.has_bottom_up_loop and self.has_subproblem_access)
        ):
            return None

        if self.has_memo_table and not self.has_bottom_up_loop:
            return "top-down-memoization"

        if self.has_memo_table and self.has_bottom_up_loop:
            return "hybrid"

        if self.has_bottom_up_loop and self.has_subproblem_access:
            return "bottom-up-tabulation"

        return "unknown"

    def _estimate_complexity_impact(self) -> str:
        """
        Estimate the impact of DP on time complexity.
        """
        if not (
            self.has_memo_table
            or (self.has_bottom_up_loop and self.has_subproblem_access)
        ):
            return "none"

        if self.dp_table_dimensions == 1:
            return "O(n) - Linear time with memoization"

        if self.dp_table_dimensions == 2:
            return "O(n^2) - Quadratic time with 2D table"

        if self.dp_table_dimensions >= 3:
            return f"O(n^{self.dp_table_dimensions}) - Polynomial time"

        if self.has_bottom_up_loop:
            return "O(n) to O(n^2) - Depends on loop nesting"

        return "O(n) - Likely linear with memoization"
