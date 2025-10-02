"""
NULL safety validator for a specific programming language.
Analyzes code to detect potential NULL-related issues.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from language.ast.node import (Assignment, ASTNode, BinOp,
                                        FieldAccess, FieldTarget, ForLoop,
                                        FuncCallExpr, IfElse, NewObject, Null,
                                        Program, RepeatUntil, Var, VarTarget,
                                        WhileLoop)
from language.ast.visitor import DefaultASTVisitor


class NullSafetyValidator(DefaultASTVisitor):
    """
    Validator that analyzes the code to detect potential NULL-related problems.
    """

    def __init__(self):
        self.warnings: Set[str] = set()
        self.errors: Set[str] = set()
        self.nullable_variables: Set[str] = set()
        self.checked_variables: Set[str] = set()
        self.current_context: Optional[str] = None

    def validate_null_safety(self, ast: ASTNode) -> Tuple[List[str], List[str]]:
        """
        Validates NULL safety in the given AST.
        """
        self._clear_state()
        ast.accept(self)
        return list(self.errors), list(self.warnings)

    def add_warning(self, message: str):
        """
        Add a warning message to the validator.
        """
        self.warnings.add(message)

    def _clear_state(self):
        """
        Clear the internal state of the validator.
        """
        self.warnings.clear()
        self.errors.clear()
        self.nullable_variables.clear()
        self.checked_variables.clear()
        self.current_context = None

    def visit_assignment(self, node: Assignment) -> Any:
        """
        Analyzes assignments to track variables that can be NULL.
        """
        target_name = self._extract_variable_name(node.target)

        if isinstance(node.value, Null):
            if target_name:
                self.nullable_variables.add(target_name)

        elif isinstance(node.value, NewObject):
            if target_name and target_name in self.nullable_variables:
                self.nullable_variables.remove(target_name)

        elif isinstance(node.value, FuncCallExpr):
            if target_name:
                self.nullable_variables.add(target_name)

        elif isinstance(node.value, Var):
            if node.value.name in self.nullable_variables:
                if target_name:
                    self.nullable_variables.add(target_name)
                    self.add_warning(
                        f"Variable '{target_name}' may be assigned NULL from variable '{node.value.name}'."
                    )

        super().visit_assignment(node)

    def visit_field_access(self, node: FieldAccess) -> Any:
        """
        Analyzes field accesses to ensure NULL safety.
        """
        obj_name = node.obj

        if obj_name in self.nullable_variables:
            if obj_name not in self.checked_variables:
                self.add_warning(
                    f"Accessing field '{node.field}' of potentially NULL variable '{obj_name}' without prior NULL check."
                )

        if hasattr(node, "field") and isinstance(node.field, FieldAccess):
            node.field.accept(self)

        super().visit_field_access(node)

    def visit_if_else(self, node: IfElse) -> Any:
        """
        Analyzes if-else statements to track NULL checks.
        """
        null_checks = self._extract_null_checks(node.cond)

        old_checked = self.checked_variables.copy()
        self.checked_variables.update(null_checks)

        for stmt in node.then_branch:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

        self.checked_variables = old_checked
        for stmt in node.else_branch:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

    def visit_bin_op(self, node: BinOp) -> Any:
        """
        Analyzes binary operations to detect NULL comparisons.
        """
        if hasattr(node, "op") and node.op in ["!=", "="]:
            if isinstance(node.right, Null) and isinstance(node.left, Var):
                if node.op == "!=":
                    self.checked_variables.add(node.left.name)
                elif node.op == "=":
                    self.nullable_variables.add(node.left.name)

        super().visit_bin_op(node)

    def visit_func_call_expr(self, node: FuncCallExpr) -> Any:
        """
        Analyzes function calls to detect those that may return NULL.
        """
        potentially_null_functions = {
            "neighbors",
            "substring",
        }

        if node.name and str(node.name).lower() in potentially_null_functions:
            self.add_warning(
                f"The function '{node.name}' may return NULL. Ensure to handle its return value appropriately."
            )

        super().visit_func_call_expr(node)

    def _extract_variable_name(self, target: Any) -> Optional[str]:
        """
        Extracts the variable name from a target node.
        """
        if isinstance(target, VarTarget):
            return target.name
        if isinstance(target, FieldTarget):
            return target.obj
        if isinstance(target, Var):
            return target.name
        return None

    def _extract_null_checks(self, condition: Any) -> Set[str]:
        """
        Extracts the variables that are being checked against NULL in a condition.
        """
        null_checks: Set[str] = set()

        if isinstance(condition, BinOp):
            if hasattr(condition, "op") and condition.op == "!=":
                if isinstance(condition.right, Null) and isinstance(
                    condition.left, Var
                ):
                    null_checks.add(condition.left.name)

        elif hasattr(condition, "op") and condition.op == "and":
            left_checks = self._extract_null_checks(condition.left)
            right_checks = self._extract_null_checks(condition.right)
            null_checks.update(left_checks)
            null_checks.update(right_checks)

        return null_checks

    def generate_null_safety_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive report on NULL safety.
        """
        return {
            "nullable_variables": list(self.nullable_variables),
            "checked_variables": list(self.checked_variables),
            "unchecked_nullables": list(
                self.nullable_variables - self.checked_variables
            ),
            "warnings": self.warnings.copy(),
            "errors": self.errors.copy(),
        }

    def visit_program(self, node: Program) -> None:
        for stmt in node.statements:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

    def visit_for_loop(self, node: ForLoop) -> None:
        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

    def visit_while_loop(self, node: WhileLoop) -> None:
        if hasattr(node.cond, "accept"):
            node.cond.accept(self)
        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

    def visit_repeat_until(self, node: RepeatUntil) -> None:
        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)
        if hasattr(node.cond, "accept"):
            node.cond.accept(self)
