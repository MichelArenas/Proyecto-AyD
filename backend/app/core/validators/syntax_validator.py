"""
Syntax validator for the language AST.
"""

from typing import Any, List, Optional, Set, Tuple

from app.core.language.ast import (AddEdgeFunction, AddNodeFunction,
                                   ArrayAccess, ArraySlice, ArrayTarget,
                                   ArrayVarDecl, Assignment, BinOp, Bool,
                                   CallMethod, CallStmt, CeilFunction,
                                   ClassDef, Comment, ConcatFunction,
                                   FieldAccess, FieldTarget, FloorFunction,
                                   ForLoop, FuncCallExpr, GraphVarDecl, IfElse,
                                   LengthFunction, NeighborsFunction, NewGraph,
                                   NewObject, Null, Number, ObjectVarDecl,
                                   Parameter, PrintStmt, Program, RepeatUntil,
                                   ReturnStmt, ShortCircuitBinOp, String,
                                   StrlenFunction, SubroutineDef,
                                   SubstringFunction, UnOp, Var, VarDecl,
                                   VarTarget, WhileLoop)
from app.core.utils import ArrayDimensionTracker, MultidimensionalArrayHandler
from app.core.validators import BaseValidator, LoopValidator


class SyntaxValidator(BaseValidator):
    """
    Validator that checks the syntax and structure of the AST.
    """

    def __init__(self):
        super().__init__()
        self.declared_variables: set[str] = set()
        self.declared_classes: set[str] = set()
        self.current_subroutine: Optional[str] = None
        self.dimension_tracker = ArrayDimensionTracker()
        self.loop_validator = LoopValidator()
        self.array_variables: set[str] = set()
        self.object_variables: set[str] = set()
        self.graph_variables: set[str] = set()
        self.scope_stack: List[Tuple[set[str], set[str], set[str], set[str]]] = []

    def _enter_scope(self):
        """Enter a new scope by saving current variable sets."""
        self.scope_stack.append(
            (
                self.declared_variables.copy(),
                self.array_variables.copy(),
                self.object_variables.copy(),
                self.graph_variables.copy(),
            )
        )

    def _exit_scope(self):
        """Exit current scope and restore previous variable sets."""
        if self.scope_stack:
            (
                self.declared_variables,
                self.array_variables,
                self.object_variables,
                self.graph_variables,
            ) = self.scope_stack.pop()

    def validate(self, ast: Program) -> Tuple[List[str], List[str]]:
        """
        Validates the syntax of the given AST.
        """
        self.clear_state()
        self.declared_variables.clear()
        self.declared_classes.clear()
        self.array_variables.clear()
        self.object_variables.clear()
        self.graph_variables.clear()
        self.scope_stack.clear()

        ast.accept(self)

        self._validate_declaration_order(ast)
        self._validate_unique_declarations(ast)
        self._validate_local_variable_placement(ast)

        return list(self.errors), list(self.warnings)

    def _validate_declaration_order(self, program: Program):
        """
        Validates the order of declaration of classes, subroutines, and main code.
        """
        found_subroutine = False
        found_main_code = False

        for stmt in program.statements:
            if isinstance(stmt, ClassDef):
                if found_subroutine:
                    self.add_error(
                        f"Class '{stmt.name}' defined after subroutines. "
                        "Classes must be defined before subroutines."
                    )
                if found_main_code:
                    self.add_error(
                        f"Class '{stmt.name}' defined after main code. "
                        "Classes must be defined at the beginning of the program."
                    )

            elif isinstance(stmt, SubroutineDef):
                found_subroutine = True
                if found_main_code:
                    self.add_error(
                        f"Subroutine '{stmt.name}' defined after main code. "
                        "Subroutines must be defined before main code."
                    )

            else:
                if not isinstance(stmt, (ClassDef, SubroutineDef)):
                    found_main_code = True

    def _validate_unique_declarations(self, program: Program):
        """
        Validates that there are no duplicate class or subroutine declarations.
        """
        class_definitions: Set[str] = set()
        subroutine_definitions: Set[str] = set()

        for stmt in program.statements:
            if isinstance(stmt, ClassDef):
                if stmt.name in class_definitions:
                    self.add_error(f"Class '{stmt.name}' defined multiple times")
                else:
                    class_definitions.add(str(stmt.name))

            elif isinstance(stmt, SubroutineDef):
                if stmt.name in subroutine_definitions:
                    self.add_error(f"Subroutine '{stmt.name}' defined multiple times")
                else:
                    if stmt.name:
                        subroutine_definitions.add(str(stmt.name))

    def _validate_local_variable_placement(self, program: Program):
        """
        Validates that local variables are declared at the start of blocks.
        """
        for stmt in program.statements:
            if isinstance(stmt, SubroutineDef):
                self._validate_subroutine_variable_placement(stmt)

    def _validate_subroutine_variable_placement(self, subroutine: SubroutineDef):
        """
        Validates that variables in a subroutine are declared at the start.
        """
        if not subroutine.body:
            return

        found_non_decl = False
        consecutive_var_decls_at_start = True

        for i, stmt in enumerate(subroutine.body):
            if isinstance(stmt, VarDecl):
                if found_non_decl and consecutive_var_decls_at_start:
                    self.add_error(
                        f"Variable declaration found after executable code in subroutine '{subroutine.name}'. Variables must be declared at the start of the block."
                    )
                    break
            elif not self._is_comment_or_empty(stmt):
                found_non_decl = True
                if i > 0 and isinstance(subroutine.body[i - 1], VarDecl):
                    consecutive_var_decls_at_start = False

    def _is_comment_or_empty(self, stmt: Any) -> bool:
        """
        Determines if a statement is a comment or empty.
        """
        return isinstance(stmt, Comment) or not stmt

    def visit_program(self, node: Program) -> Any:
        for stmt in node.statements:
            if isinstance(stmt, ClassDef):
                stmt.accept(self)

        for stmt in node.statements:
            if not isinstance(stmt, ClassDef):
                stmt.accept(self)

    def visit_class_def(self, node: ClassDef) -> Any:
        if node.name in self.declared_classes:
            self.add_error(f"Class '{node.name}' is already defined")
        else:
            self.declared_classes.add(str(node.name))

        field_names: Set[str] = set()
        for field in node.fields:
            if field in field_names:
                self.add_error(f"Field '{field}' duplicated in class '{node.name}'")
            field_names.add(field)

    def visit_subroutine_def(self, node: SubroutineDef) -> Any:
        old_subroutine = self.current_subroutine
        old_variables = self.declared_variables.copy()
        old_arrays = self.array_variables.copy()
        old_objects = self.object_variables.copy()
        old_graphs = self.graph_variables.copy()

        self.current_subroutine = str(node.name)

        for param in node.parameters:
            param.accept(self)

        for stmt in node.body:
            stmt.accept(self)

        self.current_subroutine = old_subroutine
        self.declared_variables = old_variables
        self.array_variables = old_arrays
        self.object_variables = old_objects
        self.graph_variables = old_graphs

    def visit_parameter(self, node: Parameter) -> Any:
        if node.name in self.declared_variables:
            self.add_error(
                f"Parameter '{node.name}' duplicated in subroutine '{self.current_subroutine}'"
            )
        else:
            self.declared_variables.add(str(node.name))

            if node.param_type == "array":
                self.array_variables.add(str(node.name))
                dimensions = node.dimensions if node.dimensions else [None]
                self.dimension_tracker.register_array(str(node.name), dimensions)
            elif node.param_type == "object":
                self.object_variables.add(str(node.name))
            elif node.param_type == "graph":
                self.graph_variables.add(str(node.name))

    def visit_var_decl(self, node: VarDecl) -> Any:
        for item in node.items:
            if isinstance(item, tuple):
                var_name, _ = item
                if var_name in self.declared_variables:
                    self.add_error(f"Variable '{var_name}' is already declared")
                else:
                    self.declared_variables.add(var_name)
            elif isinstance(item, ArrayVarDecl):
                if item.name in self.declared_variables:
                    self.add_error(f"Array variable '{item.name}' is already declared")
                else:
                    self.declared_variables.add(item.name)
                    self.array_variables.add(item.name)
                    self.dimension_tracker.register_array(item.name, item.dimensions)

                    for dim in item.dimensions:
                        if hasattr(dim, "accept"):
                            dim.accept(self)
            elif isinstance(item, ObjectVarDecl):
                if item.class_name not in self.declared_classes:
                    self.add_error(
                        f"Class '{item.class_name}' is not defined for variable '{item.name}'"
                    )
                if item.name in self.declared_variables:
                    self.add_error(f"Object variable '{item.name}' is already declared")
                else:
                    self.declared_variables.add(item.name)
                    self.object_variables.add(item.name)
            elif isinstance(item, GraphVarDecl):
                if item.name in self.declared_variables:
                    self.add_error(f"Graph variable '{item.name}' is already declared")
                else:
                    self.declared_variables.add(item.name)
                    self.graph_variables.add(item.name)

    def visit_assignment(self, node: Assignment) -> Any:
        self._validate_single_assignment(node)

        if isinstance(node.target, VarTarget):
            if node.target.name not in self.declared_variables:
                self.declared_variables.add(node.target.name)

        if hasattr(node.target, "accept"):
            node.target.accept(self)
        if hasattr(node.value, "accept"):
            node.value.accept(self)

    def _validate_single_assignment(self, node: Assignment):
        """
        Validates that the assignment is not a multiple assignment.
        Constructions like: a, b <- 1, 2 are not allowed.
        """
        if isinstance(node.target, list):
            self.add_error("Multiple assignments are not allowed")

        if isinstance(node.value, list) and len(node.value) > 1:
            self.add_error("Multiple assignments are not allowed")

    def visit_for_loop(self, node: ForLoop) -> Any:
        """
        Validates FOR loop with Pascal compliance and marks variable for specific behavior.
        """
        loop_errors = self.loop_validator.validate_for_loop(node)
        for error in loop_errors:
            self.errors.add(error)

        if hasattr(node.start, "accept"):
            node.start.accept(self)
        if hasattr(node.end, "accept"):
            node.end.accept(self)

        self._enter_scope()
        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)
        self._exit_scope()

    def visit_var_target(self, node: VarTarget) -> Any:
        pass

    def visit_array_target(self, node: ArrayTarget) -> Any:
        """
        Validates access to multidimensional arrays.
        """
        self._validate_array_access(node.name, node.index)

    def visit_field_target(self, node: FieldTarget) -> Any:
        if node.obj not in self.declared_variables:
            self.add_error(f"Object variable '{node.obj}' is not declared")

    def _validate_array_access(self, array_name: str, index: Any):
        """
        Validates that access to multidimensional arrays is correct.
        """
        if isinstance(index, list):
            if len(index) == 0:
                self.add_error(f"Access to array '{array_name}' without index")

            for idx in index:
                if hasattr(idx, "accept"):
                    idx.accept(self)
        elif hasattr(index, "accept"):
            index.accept(self)

    def visit_comment(self, node: Comment) -> Any:
        pass

    def visit_while_loop(self, node: WhileLoop) -> Any:
        loop_errors = self.loop_validator.validate_while_loop(node)
        for error in loop_errors:
            self.errors.add(error)

        if hasattr(node.cond, "accept"):
            node.cond.accept(self)

        self._enter_scope()
        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)
        self._exit_scope()

    def visit_repeat_until(self, node: RepeatUntil) -> Any:
        loop_errors = self.loop_validator.validate_repeat_loop(node)
        for error in loop_errors:
            self.errors.add(error)

        self._enter_scope()
        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)
        if hasattr(node.cond, "accept"):
            node.cond.accept(self)
        self._exit_scope()

    def visit_if_else(self, node: IfElse) -> Any:
        if hasattr(node.cond, "accept"):
            node.cond.accept(self)

        self._enter_scope()
        for stmt in node.then_branch:
            if hasattr(stmt, "accept"):
                stmt.accept(self)
        self._exit_scope()

        self._enter_scope()
        for stmt in node.else_branch:
            if hasattr(stmt, "accept"):
                stmt.accept(self)
        self._exit_scope()

    def visit_call_stmt(self, node: CallStmt) -> Any:
        for arg in node.args:
            if hasattr(arg, "accept"):
                arg.accept(self)

    def visit_call_method(self, node: CallMethod) -> Any:
        if hasattr(node.obj, "accept"):
            node.obj.accept(self)

        for arg in node.args:
            if hasattr(arg, "accept"):
                arg.accept(self)

    def visit_return_stmt(self, node: ReturnStmt) -> Any:
        if node.value and hasattr(node.value, "accept"):
            node.value.accept(self)

    def visit_print_stmt(self, node: PrintStmt) -> Any:
        if node.value and hasattr(node.value, "accept"):
            node.value.accept(self)

    def visit_array_access(self, node: ArrayAccess) -> Any:
        if node.name not in self.declared_variables:
            self.add_error(f"Array '{node.name}' not declared")
        else:
            if node.name in self.dimension_tracker.array_dimensions:
                handler = MultidimensionalArrayHandler(self.dimension_tracker)
                if not handler.validate_multidimensional_access(node.name, node.index):
                    for error in handler.errors:
                        if "not declared" not in error:
                            self.add_error(error)

        if isinstance(node.index, list):
            for idx in node.index:
                if hasattr(idx, "accept"):
                    idx.accept(self)
        elif hasattr(node.index, "accept"):
            node.index.accept(self)

    def visit_array_slice(self, node: ArraySlice) -> Any:
        """Validate array slicing."""
        if isinstance(node.ranges, list):
            for r in node.ranges:
                if isinstance(r, tuple) and len(r) == 2:
                    start, end = r
                    if hasattr(start, "accept") and start is not Any:
                        start.accept(self)
                    if hasattr(end, "accept") and end is not Any:
                        end.accept(self)

    def visit_field_access(self, node: FieldAccess) -> Any:
        if node.obj not in self.declared_variables:
            self.add_error(f"Object variable '{node.obj}' is not declared")

    def visit_func_call_expr(self, node: FuncCallExpr) -> Any:
        for arg in node.args:
            if hasattr(arg, "accept"):
                arg.accept(self)

    def visit_bin_op(self, node: BinOp) -> Any:
        if hasattr(node.left, "accept"):
            node.left.accept(self)
        if node.right and hasattr(node.right, "accept"):
            node.right.accept(self)

    def visit_short_circuit_bin_op(self, node: ShortCircuitBinOp) -> Any:
        if hasattr(node.left, "accept"):
            node.left.accept(self)
        if hasattr(node.right, "accept"):
            node.right.accept(self)

    def visit_un_op(self, node: UnOp) -> Any:
        if hasattr(node.value, "accept"):
            node.value.accept(self)

    def visit_number(self, node: Number) -> Any:
        pass

    def visit_string(self, node: String) -> Any:
        pass

    def visit_var(self, node: Var) -> Any:
        if self._is_builtin_function_context(node.name):
            return

        if node.name not in self.declared_variables:
            if "." in node.name:
                obj_name = node.name.split(".")[0]
                if obj_name not in self.declared_variables:
                    self.add_error(f"Object variable '{obj_name}' is not declared")
            else:
                if not self._is_function_or_builtin(node.name):
                    self.add_error(f"Variable '{node.name}' is not declared")

    def _is_builtin_function_context(self, name: str) -> bool:
        """Check if this variable is in a built-in function context."""
        builtin_functions = {
            "length",
            "ceil",
            "floor",
            "concat",
            "substring",
            "strlen",
            "addNode",
            "addEdge",
            "neighbors",
        }
        return name in builtin_functions

    def _is_function_or_builtin(self, name: str) -> bool:
        """Check if this is a function name or built-in."""
        return False

    def visit_bool(self, node: Bool) -> Any:
        pass

    def visit_null(self, node: Null) -> Any:
        pass

    def visit_new_object(self, node: NewObject) -> Any:
        if node.class_name not in self.declared_classes:
            self.add_error(f"Class '{node.class_name}' is not defined")

    def visit_length_function(self, node: LengthFunction) -> Any:
        if hasattr(node.array, "accept"):
            node.array.accept(self)

    def visit_ceil_function(self, node: CeilFunction) -> Any:
        if hasattr(node.expr, "accept"):
            node.expr.accept(self)

    def visit_floor_function(self, node: FloorFunction) -> Any:
        if hasattr(node.expr, "accept"):
            node.expr.accept(self)

    def visit_strlen_function(self, node: StrlenFunction) -> Any:
        if hasattr(node.expr, "accept"):
            node.expr.accept(self)

    def visit_concat_function(self, node: ConcatFunction) -> Any:
        if hasattr(node.left, "accept"):
            node.left.accept(self)
        if hasattr(node.right, "accept"):
            node.right.accept(self)

    def visit_substring_function(self, node: SubstringFunction) -> Any:
        if hasattr(node.string, "accept"):
            node.string.accept(self)
        if hasattr(node.start, "accept"):
            node.start.accept(self)
        if hasattr(node.length, "accept"):
            node.length.accept(self)

    def visit_new_graph(self, node: NewGraph) -> Any:
        pass

    def visit_add_node_function(self, node: AddNodeFunction) -> Any:
        if hasattr(node.node, "accept"):
            node.node.accept(self)

    def visit_add_edge_function(self, node: AddEdgeFunction) -> Any:
        if hasattr(node.from_node, "accept"):
            node.from_node.accept(self)
        if hasattr(node.to_node, "accept"):
            node.to_node.accept(self)

    def visit_neighbors_function(self, node: NeighborsFunction) -> Any:
        if hasattr(node.node, "accept"):
            node.node.accept(self)

    def visit_array_var_decl(self, node: ArrayVarDecl) -> Any:
        if node.name in self.declared_variables:
            self.add_error(f"Array variable '{node.name}' is already declared")
        else:
            self.declared_variables.add(node.name)
            self.array_variables.add(node.name)
            self.dimension_tracker.register_array(node.name, node.dimensions)

        for dim in node.dimensions:
            if hasattr(dim, "accept"):
                dim.accept(self)

    def visit_object_var_decl(self, node: ObjectVarDecl) -> Any:
        if node.class_name not in self.declared_classes:
            self.add_error(
                f"Class '{node.class_name}' is not defined for variable '{node.name}'"
            )

        if node.name in self.declared_variables:
            self.add_error(f"Object variable '{node.name}' is already declared")
        else:
            self.declared_variables.add(node.name)
            self.object_variables.add(node.name)

    def visit_graph_var_decl(self, node: GraphVarDecl) -> Any:
        if node.name in self.declared_variables:
            self.add_error(f"Graph variable '{node.name}' is already declared")
        else:
            self.declared_variables.add(node.name)
            self.graph_variables.add(node.name)
