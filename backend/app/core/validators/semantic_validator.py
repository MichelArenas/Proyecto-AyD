from typing import Any, Dict, List, Set, Tuple, Type

from app.core.language.ast.node import (
    ArrayAccess,
    ArrayVarDecl,
    Assignment,
    ASTNode,
    BinOp,
    Bool,
    ClassDef,
    FieldAccess,
    FuncCallExpr,
    GraphVarDecl,
    Null,
    Number,
    ObjectVarDecl,
    Parameter,
    Program,
    ReturnStmt,
    String,
    SubroutineDef,
    Var,
    VarDecl,
)
from app.core.language.ast.visitor import DefaultASTVisitor


class SemanticValidator(DefaultASTVisitor):
    def __init__(self):
        super().__init__()
        self.errors: Set[str] = set()
        self.warnings: Set[str] = set()
        self.current_scope: Dict[str, Any] = {}
        self.function_signatures: Dict[str, Dict[str, Any]] = {}
        self.class_fields: Dict[str, Set[str]] = {}
        self.scope_stack: List[Dict[str, Any]] = []

    def add_error(self, message: str):
        self.errors.add(f"Semantic Error: {message}")

    def add_warning(self, message: str):
        self.warnings.add(f"Semantic Warning: {message}")

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
        self.__clear_state()
        return list(self.errors), list(self.warnings)

    def __clear_state(self):
        """
        Clear the internal state of the validator.
        """
        self.errors.clear()
        self.warnings.clear()
        self.current_scope.clear()
        self.function_signatures.clear()
        self.class_fields.clear()
        self.scope_stack.clear()

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
        pass

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
            elif hasattr(item, "name"):
                if item.name in self.current_scope:
                    self.add_error(
                        f"Variable '{item.name}' already declared in this scope"
                    )
                else:
                    self.current_scope[item.name] = self._infer_type(item)

    def visit_assignment(self, node: Assignment) -> Any:
        target_type = self._get_expression_type(node.target)
        value_type = self._get_expression_type(node.value)

        if (
            target_type != value_type
            and target_type != "unknown"
            and value_type != "unknown"
        ):
            self.add_error(f"Incompatible assignment: {value_type} to {target_type}")

        super().visit_assignment(node)

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

    def _get_expression_type(self, expr: Any) -> str:
        types: Dict[Type[ASTNode], str] = {
            Number: "number",
            String: "string",
            Bool: "boolean",
            Null: "null",
            ArrayAccess: "array",
        }

        if type(expr) in types:
            return types[type(expr)]

        if isinstance(expr, Var):
            return self.current_scope.get(expr.name, "unknown")

        if isinstance(expr, FieldAccess):
            obj_type = self._get_expression_type(expr.obj)
            if (
                obj_type in self.class_fields
                and expr.field in self.class_fields[obj_type]
            ):
                return "unknown"

            self.add_error(
                f"Field '{expr.field}' does not exist in object of type '{obj_type}'"
            )
            return "unknown"

        if isinstance(expr, BinOp):
            left_type = self._get_expression_type(expr.left)
            right_type = self._get_expression_type(expr.right)

            if expr.op in ["+", "-", "*", "/", "mod", "div"]:
                if left_type != "number" or right_type != "number":
                    self.add_error(
                        f"Arithmetic operation '{expr.op}' requires numbers, got {left_type} and {right_type}"
                    )
                return "number"

            if expr.op in ["and", "or"]:
                if left_type != "boolean" or right_type != "boolean":
                    self.add_error(
                        f"Logical operation '{expr.op}' requires booleans, got {left_type} and {right_type}"
                    )
                return "boolean"

            if expr.op in ["=", "!=", "<", ">", "<=", ">="]:
                return "boolean"

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
