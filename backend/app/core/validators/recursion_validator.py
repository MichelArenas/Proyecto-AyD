"""
Module to validate recursive function calls in a custom programming language AST.
"""

from collections import defaultdict
from typing import Any, Dict, Set

from app.core.language.ast import (CallStmt, DefaultASTVisitor, FuncCallExpr,
                                   SubroutineDef)


class RecursionValidator(DefaultASTVisitor):
    """
    Validates recursive function calls in the AST by building a call graph
    and detecting cycles.
    """

    def __init__(self) -> None:
        super().__init__()
        self.call_graph: Dict[Any, Any] = defaultdict(set)
        self.current_function = None
        self.recursive_functions: Set[Any] = set()

    def visit_subroutine_def(self, node: SubroutineDef) -> Any:
        previous_function = self.current_function
        self.current_function = node.name
        super().visit_subroutine_def(node)
        self.current_function = previous_function

    def visit_func_call_expr(self, node: FuncCallExpr) -> Any:
        if self.current_function:
            self.call_graph[self.current_function].add(node.name)
        super().visit_func_call_expr(node)

    def visit_call_stmt(self, node: CallStmt) -> Any:
        if self.current_function:
            self.call_graph[self.current_function].add(node.name)
        super().visit_call_stmt(node)

    def analyze_recursion(self):
        """
        Analyze the call graph to detect recursive functions.
        """
        visited: Set[Any] = set()
        recursion_stack: Set[Any] = set()

        def dfs(function: Any):
            if function in recursion_stack:
                self.recursive_functions.add(function)
                return
            if function in visited:
                return

            visited.add(function)
            recursion_stack.add(function)

            for callee in self.call_graph[function]:
                dfs(callee)

            recursion_stack.remove(function)

        for function in self.call_graph:
            if function not in visited:
                dfs(function)
