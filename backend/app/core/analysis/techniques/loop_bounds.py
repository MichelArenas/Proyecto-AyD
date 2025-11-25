"""
Module for precise loop bounds analysis in AST.
"""

from typing import Dict, List, Optional

from app.core.language.ast import (BinOp, DefaultASTVisitor, ForLoop, IfElse,
                                   Number, Program, ReturnStmt, SubroutineDef,
                                   Var, WhileLoop)


class LoopBoundsAnalyzer(DefaultASTVisitor):
    """
    Analyze loop bounds precisely in the AST.
    """

    def __init__(self):
        self.loop_infos: List[Dict] = []
        self.early_exits: List[Dict] = []
        self.loop_guards: List[Dict] = []
        self.current_loop_depth = 0

    def analyze(self, program: Program, function_name: Optional[str] = None) -> Dict:
        """
        Analyze loop bounds in the given program.
        """
        self._reset()

        target_func = None
        if function_name:
            for stmt in program.statements:
                if isinstance(stmt, SubroutineDef) and stmt.name == function_name:
                    target_func = stmt
                    break

        if target_func:
            self._analyze_statements(target_func.body)
        else:
            self._analyze_statements(program.statements)

        return {
            "loops": self.loop_infos,
            "early_exits": self.early_exits,
            "loop_guards": self.loop_guards,
            "max_nesting": max((loop["depth"] for loop in self.loop_infos), default=0),
        }

    def _reset(self):
        """Reset analyzer state"""
        self.loop_infos = []
        self.early_exits = []
        self.loop_guards = []
        self.current_loop_depth = 0

    def _analyze_statements(self, statements: List):
        """Analyze a list of statements"""
        for stmt in statements:
            stmt.accept(self)

    def visit_for_loop(self, node: ForLoop):
        """Analyze FOR loop patterns"""
        self.current_loop_depth += 1

        start_value = self._evaluate_expression(node.start)
        end_value = self._evaluate_expression(node.end)

        iteration_pattern = self._calculate_iteration_pattern(start_value, end_value)
        has_early_exit = self._check_early_exit(node.body)
        guard_condition = self._check_guard_conditions(node.body)

        loop_info = {
            "type": "for",
            "variable": node.var,
            "start": start_value,
            "end": end_value,
            "depth": self.current_loop_depth,
            "iteration_pattern": iteration_pattern,
            "exact_iterations": self._extract_exact_count(iteration_pattern),
            "has_early_exit": has_early_exit,
            "guard_condition": guard_condition,
        }

        self.loop_infos.append(loop_info)

        self._analyze_statements(node.body)

        self.current_loop_depth -= 1

    def visit_while_loop(self, node: WhileLoop):
        """Analyze WHILE loop patterns"""
        self.current_loop_depth += 1

        condition = str(node.cond)
        pattern = self._analyze_while_pattern(condition, node.body)

        has_early_exit = self._check_early_exit(node.body)

        loop_info = {
            "type": "while",
            "condition": condition,
            "depth": self.current_loop_depth,
            "iteration_pattern": pattern,
            "has_early_exit": has_early_exit,
        }

        self.loop_infos.append(loop_info)

        self._analyze_statements(node.body)

        self.current_loop_depth -= 1

    def _evaluate_expression(self, expr) -> str:
        """Evaluate expression to string representation"""
        if isinstance(expr, Number):
            return str(expr.value)

        if isinstance(expr, Var):
            return expr.name

        if isinstance(expr, BinOp):
            left = self._evaluate_expression(expr.left)
            right = self._evaluate_expression(expr.right)
            return f"({left} {expr.op} {right})"

        return str(expr)

    def _calculate_iteration_pattern(self, start: str, end: str) -> str:
        """
        Calculate iteration pattern based on start and end values.
        """
        start_clean = start.strip()
        end_clean = end.strip()

        try:
            start_num = int(start_clean)
            if any(var in end_clean for var in ["n", "length", "size"]):
                if start_num == 0:
                    if "-1" in end_clean or "- 1" in end_clean:
                        return "n"

                    if "/" in end_clean or "div" in end_clean:
                        if "/2" in end_clean or "div 2" in end_clean:
                            return "n/2"
                        if "/3" in end_clean or "div 3" in end_clean:
                            return "n/3"
                        return "n/k"
                    return "n"

                if start_num == 1:
                    if "log" in end_clean.lower():
                        return "log(n)"
                    return "n"
        except ValueError:
            pass

        if "log" in end_clean.lower():
            return "log(n)"

        if "/" in end_clean or "div" in end_clean:
            if "2" in end_clean:
                return "n/2"
            if "3" in end_clean:
                return "n/3"
            return "n/k"

        if "sqrt" in end_clean.lower():
            return "sqrt(n)"

        if any(var in end_clean for var in ["n", "length", "size"]):
            return "n"

        try:
            int(end_clean)
            return f"constant({end_clean})"
        except ValueError:
            return "n"

    def _extract_exact_count(self, pattern: str) -> Optional[str]:
        """Extract exact iteration count if determinable"""
        if pattern == "n":
            return "n"
        if pattern == "n/2":
            return "n/2"
        if pattern == "log(n)":
            return "log(n)"
        if pattern.startswith("constant("):
            return pattern.replace("constant(", "").replace(")", "")

        return None

    def _analyze_while_pattern(self, condition: str, body: List) -> str:
        """
        Analyze WHILE loop condition and body to determine iteration pattern.
        """
        condition_lower = condition.lower()
        body_str = " ".join(str(stmt) for stmt in body).lower()

        if any(
            pattern in body_str
            for pattern in ["* 2", "*2", "/ 2", "/2", "div 2", "* 3", "/3"]
        ):
            return "log(n)"

        if "* *" in body_str or "^" in body_str or "power" in body_str:
            return "2^n"

        if any(
            pattern in body_str for pattern in ["+ 1", "+1", "- 1", "-1", "++", "--"]
        ):
            return "n"

        if any(op in condition_lower for op in ["<", "<=", ">", ">="]):
            return "n"

        return "unknown"

    def _check_early_exit(self, body: List) -> bool:
        """Check if loop body contains early exit (return, break)"""
        for stmt in body:
            if isinstance(stmt, ReturnStmt):
                return True
            if isinstance(stmt, IfElse):
                if any(isinstance(s, ReturnStmt) for s in stmt.then_branch):
                    return True
                if any(isinstance(s, ReturnStmt) for s in stmt.else_branch):
                    return True
        return False

    def _check_guard_conditions(self, body: List) -> Optional[str]:
        """Check for guard conditions in loop body"""
        for stmt in body:
            if isinstance(stmt, IfElse):
                condition = str(stmt.cond)
                if any(
                    keyword in condition.lower()
                    for keyword in ["skip", "continue", "==", "!="]
                ):
                    return condition
        return None
