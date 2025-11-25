"""
Loop Validator for a Custom Programming Language AST
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.language.ast import (Assignment, BinOp, DefaultASTVisitor,
                                   ForLoop, IfElse, Number, Program,
                                   RepeatUntil, SubroutineDef, Var, VarTarget,
                                   WhileLoop)


class LoopValidator(DefaultASTVisitor):
    """
    Validates loop constructs in the AST, ensuring correct usage of loop counters,
    proper nesting, and adherence to language-specific loop semantics.
    """

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.loop_counters: Dict[str, Dict[str, Any]] = {}
        self.nested_loops: List[Dict[str, Any]] = []
        self.current_scope_counters: Set[str] = set()

    def add_error(self, message: str):
        """Add a validation error."""
        self.errors.append(f"Loop Error: {message}")

    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(f"Loop Warning: {message}")

    def validate(self, program: Program) -> Tuple[List[str], List[str]]:
        """Validate all loops in the program."""
        self.errors.clear()
        self.warnings.clear()
        self.loop_counters.clear()
        self.nested_loops.clear()

        program.accept(self)

        return list(self.errors), list(self.warnings)

    def validate_for_loop(self, node: ForLoop) -> List[str]:
        self.errors = []
        self.visit_for_loop(node)
        return self.errors

    def validate_while_loop(self, node: WhileLoop) -> List[str]:
        self.errors = []
        self.visit_while_loop(node)
        return self.errors

    def validate_repeat_loop(self, node: RepeatUntil) -> List[str]:
        self.errors = []
        self.visit_repeat_until(node)
        return self.errors

    def visit_for_loop(self, node: ForLoop) -> None:
        if not node.var:
            self.add_error("FOR loop missing counter variable")
            return

        counter_var = str(node.var)

        if counter_var in self.current_scope_counters:
            self.add_error(
                f"Loop counter '{counter_var}' already used in nested loop scope"
            )

        self._validate_loop_bounds(node)

        self.loop_counters[counter_var] = {
            "start_expr": node.start,
            "end_expr": node.end,
            "preserve_value": node.preserve_counter_value,
            "nested_level": len(self.nested_loops),
        }

        old_scope = self.current_scope_counters.copy()
        self.current_scope_counters.add(counter_var)

        loop_info: Dict[str, Any] = {
            "type": "for",
            "counter": counter_var,
            "level": len(self.nested_loops),
            "node": node,
        }
        self.nested_loops.append(loop_info)

        self._validate_counter_modifications_in_body(node.body, counter_var)

        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

        self._validate_pascal_counter_behavior(node, counter_var)

        self.current_scope_counters = old_scope
        self.nested_loops.pop()

    def _validate_loop_bounds(self, node: ForLoop):
        """Validate that loop bounds are well-formed."""
        start_val = self._extract_constant_value(node.start)
        end_val = self._extract_constant_value(node.end)

        if start_val and end_val:
            if start_val > end_val:
                self.add_warning(
                    f"FOR loop with start ({start_val}) > end ({end_val}) will not execute"
                )

        if isinstance(node.end, BinOp) and node.end.op in ["/", "div"]:
            self.add_warning(
                "FOR loop bound involves division - verify no division by zero"
            )

    def _validate_counter_modifications_in_body(
        self, body: List[Any], counter_var: str
    ):
        """Check if loop counter is modified within the loop body (which is not allowed)."""
        for stmt in body:
            if isinstance(stmt, Assignment) and isinstance(stmt.target, VarTarget):
                if stmt.target.name == counter_var:
                    self.add_error(
                        f"Loop counter '{counter_var}' cannot be modified within FOR loop body"
                    )

            if isinstance(stmt, (ForLoop, WhileLoop, RepeatUntil)):
                self._validate_counter_modifications_in_body(stmt.body, counter_var)
            elif isinstance(stmt, IfElse):
                self._validate_counter_modifications_in_body(
                    stmt.then_branch, counter_var
                )
                if stmt.else_branch:
                    self._validate_counter_modifications_in_body(
                        stmt.else_branch, counter_var
                    )

    def _validate_pascal_counter_behavior(self, node: ForLoop, counter_var: str):
        if not node.preserve_counter_value:
            self.add_error(
                f"FOR loop counter '{counter_var} '"
                "must preserve value according to Pascal specification"
            )

    def _extract_constant_value(self, expr: Any) -> Optional[int]:
        if isinstance(expr, Number) and isinstance(expr.value, int):
            return expr.value
        return None

    def visit_while_loop(self, node: WhileLoop) -> Any:
        """Validate WHILE loop structure."""
        loop_info: Dict[str, Any] = {
            "type": "while",
            "counter": None,
            "level": len(self.nested_loops),
            "node": node,
        }
        self.nested_loops.append(loop_info)

        if hasattr(node.cond, "accept"):
            node.cond.accept(self)

        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

        self._check_while_termination_conditions(node)

        self.nested_loops.pop()

    def visit_repeat_until(self, node: RepeatUntil) -> Any:
        """Validate REPEAT-UNTIL loop structure."""
        loop_info: Dict[str, Any] = {
            "type": "repeat",
            "counter": None,
            "level": len(self.nested_loops),
            "node": node,
        }
        self.nested_loops.append(loop_info)

        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

        if hasattr(node.cond, "accept"):
            node.cond.accept(self)

        self.nested_loops.pop()

    def _check_while_termination_conditions(self, node: WhileLoop):
        """Check for potential infinite loops in WHILE statements."""
        if isinstance(node.cond, Var):
            self.add_warning(
                "WHILE loop with simple variable condition - ensure "
                f"'{node.cond.name}' is modified in loop body"
            )

    def get_nesting_analysis(self) -> Dict[str, Any]:
        """Return analysis of loop nesting structure."""
        max_depth = max((loop["level"] for loop in self.nested_loops), default=0)
        loop_types = [loop["type"] for loop in self.nested_loops]

        return {
            "max_nesting_depth": max_depth,
            "loop_types": loop_types,
            "total_loops": len(self.nested_loops),
            "for_loops": len([l for l in self.nested_loops if l["type"] == "for"]),
            "while_loops": len([l for l in self.nested_loops if l["type"] == "while"]),
            "repeat_loops": len(
                [l for l in self.nested_loops if l["type"] == "repeat"]
            ),
        }

    def visit_subroutine_def(self, node: SubroutineDef) -> Any:
        old_counters = self.loop_counters.copy()
        old_scope = self.current_scope_counters.copy()

        self.loop_counters.clear()
        self.current_scope_counters.clear()

        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

        self.loop_counters = old_counters
        self.current_scope_counters = old_scope
