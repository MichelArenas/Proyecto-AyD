"""
Semantic Validator for a Custom Programming Language AST
"""

from typing import Any, Dict, List, Set, Tuple, Type

from app.core.language.ast import (ArrayAccess, ArrayVarDecl, Assignment,
                                   ASTNode, BinOp, Bool, CallMethod, ClassDef,
                                   FieldAccess, ForLoop, FuncCallExpr,
                                   GraphVarDecl, IfElse, Null, Number,
                                   ObjectVarDecl, Parameter, PrintStmt,
                                   Program, ReturnStmt, String, SubroutineDef,
                                   Var, VarDecl, WhileLoop)
from app.core.validators import BaseValidator


class SemanticValidator(BaseValidator):
    """
    Validator that performs semantic analysis on the AST.
    """

    def __init__(self):
        super().__init__()
        self.current_scope: Dict[str, Any] = {}
        self.function_signatures: Dict[str, Dict[str, Any]] = {}
        self.class_fields: Dict[str, Set[str]] = {}
        self.scope_stack: List[Dict[str, Any]] = []
        self.array_dimensions: Dict[str, int] = {}
        self.loop_variables: Set[str] = set()

    def enter_scope(self):
        self.scope_stack.append(self.current_scope.copy())

    def exit_scope(self):
        if self.scope_stack:
            self.current_scope = self.scope_stack.pop()

    def validate(self, program: Program) -> Tuple[List[str], List[str]]:
        """
        Validate the program for semantic errors and warnings.
        """
        self.visit_program(program)
        self._clear_extended_state()
        return list(self.errors), list(self.warnings)

    def _clear_extended_state(self):
        """
        Clear the internal state of the validator.
        """
        self.clear_state()
        self.current_scope.clear()
        self.function_signatures.clear()
        self.class_fields.clear()
        self.scope_stack.clear()
        self.array_dimensions.clear()
        self.loop_variables.clear()

    def visit_program(self, node: Program) -> Any:
        for stmt in node.statements:
            if isinstance(stmt, ClassDef):
                stmt.accept(self)
            elif isinstance(stmt, SubroutineDef):
                param_types = [self._get_param_type(p) for p in stmt.parameters]
                self.function_signatures[str(stmt.name)] = {
                    "parameters": param_types,
                    "return_type": self._infer_return_type(stmt.body),
                }

        for stmt in node.statements:
            if not isinstance(stmt, (ClassDef, SubroutineDef)):
                stmt.accept(self)
            elif isinstance(stmt, SubroutineDef):
                self.enter_scope()
                for param in stmt.parameters:
                    self.current_scope[str(param.name)] = self._get_param_type(param)

                for body_stmt in stmt.body:
                    body_stmt.accept(self)

                self.exit_scope()

    def visit_class_def(self, node: ClassDef) -> Any:
        self.class_fields[str(node.name)] = set(node.fields)

    def visit_subroutine_def(self, node: SubroutineDef) -> Any:
        """Visit function definition and register parameters in scope"""
        if hasattr(node, "parameters") and node.parameters:
            for param in node.parameters:
                if hasattr(param, "name"):
                    if hasattr(param, "param_type") and param.param_type == "array":
                        self.current_scope[param.name] = "array"
                    else:
                        self.current_scope[param.name] = "unknown"

        super().visit_subroutine_def(node)

    def visit_var_decl(self, node: VarDecl) -> Any:
        for item in node.items:
            if isinstance(item, tuple):
                var_name, value = item
                var_type = self._infer_type(value)
                if var_name in self.current_scope:
                    self.add_error(
                        f"Variable '{var_name}' already declared in this scope"
                    )
                else:
                    self.current_scope[var_name] = var_type
                    if isinstance(value, ArrayVarDecl):
                        self.array_dimensions[var_name] = self._count_array_dimensions(
                            value
                        )
            elif hasattr(item, "name"):
                if item.name in self.current_scope:
                    self.add_error(
                        f"Variable '{item.name}' already declared in this scope"
                    )
                else:
                    self.current_scope[item.name] = self._infer_type(item)
                    if isinstance(item, ArrayVarDecl):
                        self.array_dimensions[item.name] = self._count_array_dimensions(
                            item
                        )

    def visit_assignment(self, node: Assignment) -> Any:
        target_type = self._get_expression_type(node.target)
        value_type = self._get_expression_type(node.value)

        if not self._types_compatible(target_type, value_type):
            self.add_error(f"Incompatible assignment: {value_type} to {target_type}")

        if isinstance(node.target, Var) and isinstance(node.value, ArrayAccess):
            target_var = node.target.name
            value_var = node.value.name
            if (
                target_var in self.array_dimensions
                and value_var in self.array_dimensions
            ):
                target_dims = self.array_dimensions[target_var]
                value_dims = self.array_dimensions[value_var] - len(node.value.index)
                if target_dims != value_dims:
                    self.add_warning(
                        f"Array dimension mismatch: assigning {value_dims}D array to {target_dims}D variable"
                    )

        super().visit_assignment(node)

    def visit_for_loop(self, node: ForLoop) -> Any:
        """Validate for loop semantics"""
        self.enter_scope()

        if hasattr(node, "var"):
            loop_var = node.var
            self.loop_variables.add(loop_var)
            self.current_scope[loop_var] = "number"

        if hasattr(node, "start"):
            start_type = self._get_expression_type(node.start)
            if start_type not in ["number", "unknown"]:
                self.add_error(f"Loop start value must be numeric, got {start_type}")

        if hasattr(node, "end"):
            end_type = self._get_expression_type(node.end)
            if end_type not in ["number", "unknown"]:
                self.add_error(f"Loop end value must be numeric, got {end_type}")

        if hasattr(node, "step"):
            step_type = self._get_expression_type(node.step)
            if step_type not in ["number", "unknown"]:
                self.add_error(f"Loop step value must be numeric, got {step_type}")

        if hasattr(node, "body"):
            for stmt in node.body:
                stmt.accept(self)

        self.exit_scope()

    def visit_while_loop(self, node: WhileLoop) -> Any:
        """Validate while loop semantics"""
        if hasattr(node, "cond"):
            cond_type = self._get_expression_type(node.cond)
            if cond_type not in ["boolean", "unknown"]:
                self.add_warning(f"Loop condition should be boolean, got {cond_type}")

        self.enter_scope()
        if hasattr(node, "body"):
            for stmt in node.body:
                stmt.accept(self)
        self.exit_scope()

    def visit_if_else(self, node: IfElse) -> Any:
        """Validate if-else statement with proper scoping"""
        if hasattr(node, "cond") and node.cond:
            node.cond.accept(self)

        self.enter_scope()
        if hasattr(node, "then_branch"):
            for stmt in node.then_branch:
                if hasattr(stmt, "accept"):
                    stmt.accept(self)
        self.exit_scope()

        self.enter_scope()
        if hasattr(node, "else_branch"):
            for stmt in node.else_branch:
                if hasattr(stmt, "accept"):
                    stmt.accept(self)
        self.exit_scope()

    def visit_func_call_expr(self, node: FuncCallExpr) -> Any:
        if node.name not in self.function_signatures:
            self.add_error(f"Function '{node.name}' is not defined")
            return

        signature = self.function_signatures.get(str(node.name))

        if not signature:
            self.add_error(f"Function '{node.name}' is not defined")
            return

        expected_params = signature["parameters"]

        actual_params = [self._get_expression_type(arg) for arg in node.args]

        if len(expected_params) != len(actual_params):
            self.add_error(
                f"Incorrect number of parameters for '{node.name}'. Expected: {len(expected_params)}, got: {len(actual_params)}"
            )
        else:
            for i, (expected, actual) in enumerate(zip(expected_params, actual_params)):
                if expected != actual and expected != "unknown" and actual != "unknown":
                    self.add_error(
                        f"Incorrect type for parameter {i+1} in call to '{node.name}'. Expected: {expected}, got: {actual}"
                    )

        super().visit_func_call_expr(node)

    def visit_print_stmt(self, node: PrintStmt) -> Any:
        if node.value and hasattr(node.value, "accept"):
            node.value.accept(self)

    def visit_call_method(self, node: CallMethod) -> Any:
        if hasattr(node.obj, "accept"):
            node.obj.accept(self)

        for arg in node.args:
            if hasattr(arg, "accept"):
                arg.accept(self)

    def _get_expression_type(self, expr: Any) -> str:
        types: Dict[Type[ASTNode], str] = {
            Number: "number",
            String: "string",
            Bool: "boolean",
            Null: "null",
        }

        if type(expr) in types:
            return types[type(expr)]

        if isinstance(expr, ArrayAccess):
            self._validate_array_access(expr)
            return "number"

        if isinstance(expr, Var):
            var_type = self.current_scope.get(expr.name, None)
            if var_type is None:
                self.add_error(f"Variable '{expr.name}' not declared")
                return "unknown"
            return var_type

        if isinstance(expr, FieldAccess):
            obj_type = self._get_expression_type(expr.obj)
            if (
                obj_type in self.class_fields
                and expr.field in self.class_fields[obj_type]
            ):
                return "unknown"

            if obj_type != "unknown":
                self.add_error(
                    f"Field '{expr.field}' does not exist in object of type '{obj_type}'"
                )
            return "unknown"

        if isinstance(expr, BinOp):
            left_type = self._get_expression_type(expr.left)
            right_type = self._get_expression_type(expr.right)

            if expr.op in ["+", "-", "*", "/", "mod", "div"]:
                if not self._validate_numeric_operation(expr.op, left_type, right_type):
                    self.add_error(
                        f"Arithmetic operation '{expr.op}' requires numbers, got {left_type} and {right_type}"
                    )
                return "number"

            if expr.op in ["and", "or"]:
                if not self._validate_boolean_operation(expr.op, left_type, right_type):
                    self.add_error(
                        f"Logical operation '{expr.op}' requires booleans, got {left_type} and {right_type}"
                    )
                return "boolean"

            if expr.op in ["=", "!=", "<", ">", "<=", ">="]:
                if (
                    left_type != right_type
                    and left_type != "unknown"
                    and right_type != "unknown"
                ):
                    self.add_warning(
                        f"Comparing different types: {left_type} and {right_type}"
                    )
                return "boolean"

        if isinstance(expr, FuncCallExpr):
            if expr.name in self.function_signatures:
                return self.function_signatures[expr.name].get("return_type", "unknown")

        return "unknown"

    def _infer_type(self, value: Any) -> str:
        types: Dict[Type[ASTNode], str] = {
            Number: "number",
            String: "string",
            Bool: "boolean",
            Null: "null",
            ArrayVarDecl: "array",
            GraphVarDecl: "graph",
        }

        if type(value) in types:
            return types[type(value)]

        if isinstance(value, Var):
            return self.current_scope.get(value.name, "unknown")

        if isinstance(value, ObjectVarDecl):
            return value.class_name

        return "unknown"

    def _get_param_type(self, param: Parameter) -> str:
        if param.param_type == "array":
            return "array"

        if param.param_type == "object":
            return str(param.class_name)

        if param.param_type == "graph":
            return "graph"

        return param.param_type

    def _infer_return_type(self, body: List[Any]) -> str:
        for stmt in reversed(body):
            if isinstance(stmt, ReturnStmt):
                return self._get_expression_type(stmt.value)
        return "void"

    def _types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two types are compatible for assignment"""
        if type1 == "unknown" or type2 == "unknown":
            return True
        if type1 == type2:
            return True
        if type1 == "number" and type2 in ["number", "boolean"]:
            return True
        return False

    def _count_array_dimensions(self, node: ArrayVarDecl) -> int:
        """Count the dimensions of an array declaration"""
        dimensions = 0
        if hasattr(node, "dimensions") and node.dimensions:
            dimensions = len(node.dimensions)
        return dimensions

    def _validate_array_access(self, node: ArrayAccess) -> None:
        """Validate array access dimensions"""
        if node.name not in self.current_scope:
            self.add_error(f"Array '{node.name}' not declared")
            return

        if node.name in self.array_dimensions:
            expected_dims = self.array_dimensions[node.name]
            actual_dims = (
                len(node.index) if hasattr(node, "index") and node.index else 0
            )

            if actual_dims > expected_dims:
                self.add_error(
                    f"Too many indices for array '{node.name}': expected {expected_dims}, got {actual_dims}"
                )
            elif actual_dims < expected_dims:
                self.add_warning(
                    f"Array '{node.name}' has {expected_dims} dimensions but accessed with {actual_dims} indices"
                )

        if hasattr(node, "index") and node.index:
            for i, idx in enumerate(node.index):
                idx_type = self._get_expression_type(idx)
                if idx_type not in ["number", "unknown"]:
                    self.add_error(f"Array index {i+1} must be numeric, got {idx_type}")

    def _validate_numeric_operation(
        self, op: str, left_type: str, right_type: str
    ) -> bool:
        """Validate that both operands are numeric for arithmetic operations"""
        if left_type == "unknown" or right_type == "unknown":
            return True
        if left_type == "number" and right_type == "number":
            return True
        return False

    def _validate_boolean_operation(
        self, op: str, left_type: str, right_type: str
    ) -> bool:
        """Validate that both operands are boolean for logical operations"""
        if left_type == "unknown" or right_type == "unknown":
            return True
        if left_type == "boolean" and right_type == "boolean":
            return True
        return False
