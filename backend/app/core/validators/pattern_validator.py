""" """

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.language.ast.node import (ArrayAccess, Assignment, ASTNode,
                                        BinOp, CallStmt, ForLoop, FuncCallExpr,
                                        IfElse, Program, RepeatUntil,
                                        ReturnStmt, SubroutineDef, VarTarget,
                                        WhileLoop)


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
                    f"Función {func_name} hace {recursion.recursive_calls} llamadas recursivas"
                ]

                if recursion.base_cases > 0:
                    confidence += 0.2
                    evidence.append(
                        f"Tiene {recursion.base_cases} casos base identificados"
                    )

                if self._has_problem_division(func_name):
                    confidence += 0.1
                    evidence.append("Evidencia de división del problema")

                self.patterns.append(
                    PatternDetection(
                        pattern_type="Divide and Conquer",
                        confidence=min(confidence, 1.0),
                        location=f"Función {func_name}",
                        description="Patrón divide y vencerás detectado por múltiples llamadas recursivas",
                        evidence=evidence,
                    )
                )

    def _detect_dynamic_programming(self, program: Program) -> None:
        """Detecta patrones de programación dinámica."""
        for func_name, calls in self.function_calls.items():
            # Buscar uso de memoización o tablas
            if self._has_memoization_pattern(func_name):
                confidence = 0.8
                evidence = ["Uso de memoización o tabla de resultados detectado"]

                # Verificar solapamiento de subproblemas
                if func_name in self.recursion_info:
                    evidence.append(
                        "Función recursiva con posible solapamiento de subproblemas"
                    )
                    confidence += 0.1

                self.patterns.append(
                    PatternDetection(
                        pattern_type="Dynamic Programming",
                        confidence=min(confidence, 1.0),
                        location=f"Función {func_name}",
                        description="Patrón de programación dinámica detectado",
                        evidence=evidence,
                    )
                )

    def _detect_greedy_patterns(self, program: Program) -> None:
        """Detecta patrones de algoritmos greedy."""
        # Detectar selección greedy en loops
        for func_name, calls in self.function_calls.items():
            if self._has_greedy_selection(func_name):
                confidence = 0.6
                evidence = ["Selección de opción óptima local detectada"]

                if self._has_optimization_criteria(func_name):
                    confidence += 0.2
                    evidence.append("Criterios de optimización identificados")

                self.patterns.append(
                    PatternDetection(
                        pattern_type="Greedy Algorithm",
                        confidence=min(confidence, 1.0),
                        location=f"Función {func_name}",
                        description="Patrón de algoritmo greedy detectado",
                        evidence=evidence,
                    )
                )

    def _detect_backtracking(self, program: Program) -> None:
        """Detecta patrones de backtracking."""
        for func_name, recursion in self.recursion_info.items():
            if self._has_backtracking_pattern(func_name):
                confidence = 0.7
                evidence = ["Patrón de backtracking detectado"]

                if recursion.recursive_calls > 0:
                    evidence.append("Función recursiva que explora alternativas")
                    confidence += 0.2

                self.patterns.append(
                    PatternDetection(
                        pattern_type="Backtracking",
                        confidence=min(confidence, 1.0),
                        location=f"Función {func_name}",
                        description="Patrón de backtracking para exploración de soluciones",
                        evidence=evidence,
                    )
                )

    def _detect_function_patterns(self, func: SubroutineDef) -> None:
        """Detecta patrones específicos de función."""
        # Detectar funciones helper o auxiliares
        if self._is_helper_function(func):
            self.patterns.append(
                PatternDetection(
                    pattern_type="Helper Function",
                    confidence=0.8,
                    location=f"Función {func.name}",
                    description="Función auxiliar detectada",
                    evidence=["Función utilizada como helper en algoritmo principal"],
                )
            )

    def _detect_loop_patterns(self, loop_node: ASTNode) -> None:
        """Detecta patrones en loops."""
        if self.loop_nesting > 2:
            self.patterns.append(
                PatternDetection(
                    pattern_type="Nested Loops",
                    confidence=0.9,
                    location=f"Función {self.current_function or 'desconocida'}",
                    description=f"Loops anidados de nivel {self.loop_nesting}",
                    evidence=[
                        f"Anidamiento de loops de nivel {self.loop_nesting} puede indicar complejidad O(n^{self.loop_nesting})"
                    ],
                )
            )

    # Métodos auxiliares de detección

    def _contains_recursive_call(self, node: ASTNode, func_name: str) -> bool:
        """Verifica si un nodo contiene una llamada recursiva."""
        if isinstance(node, FuncCallExpr) and node.name == func_name:
            return True
        elif isinstance(node, CallStmt) and node.name == func_name:
            return True

        # Buscar en nodos hijos
        return self._search_in_children(
            node, lambda n: self._contains_recursive_call(n, func_name)
        )

    def _is_tail_recursive_call(self, node: ASTNode, func_name: str) -> bool:
        """Verifica si una llamada recursiva es tail recursion."""
        if isinstance(node, ReturnStmt) and node.value:
            return (
                isinstance(node.value, (FuncCallExpr, CallStmt))
                and getattr(node.value, "name", None) == func_name
            )
        return False

    def _is_base_case(self, node: ASTNode) -> bool:
        """Detecta casos base en recursión."""
        if isinstance(node, ReturnStmt):
            return True
        elif isinstance(node, IfElse):
            # Verificar si alguna rama es un return simple
            return any(isinstance(stmt, ReturnStmt) for stmt in node.then_branch)
        return False

    def _modifies_parameters(self, node: ASTNode, parameters: List[Any]) -> bool:
        """Verifica si se modifican los parámetros de la función."""
        if isinstance(node, Assignment):
            target = node.target
            if isinstance(target, VarTarget):
                param_names = [p.name for p in parameters] if parameters else []
                return target.name in param_names
        return False

    def _has_problem_division(self, func_name: str) -> bool:
        """Detecta evidencia de división del problema."""
        # Simplificado: buscar indicios de división en llamadas
        return (
            func_name in self.recursion_info
            and self.recursion_info[func_name].recursive_calls >= 2
        )

    def _has_memoization_pattern(self, func_name: str) -> bool:
        """Detecta patrones de memoización."""
        # Buscar arrays o estructuras que puedan ser tablas de memoización
        calls = self.function_calls.get(func_name, [])
        return any(
            "tabla" in call.lower() or "memo" in call.lower() or "cache" in call.lower()
            for call in calls
        )

    def _has_greedy_selection(self, func_name: str) -> bool:
        """Detecta selección greedy."""
        # Buscar patrones como "max", "min", "mejor", "óptimo"
        calls = self.function_calls.get(func_name, [])
        greedy_keywords = ["max", "min", "mejor", "optimo", "maximo", "minimo"]
        return any(
            any(keyword in call.lower() for keyword in greedy_keywords)
            for call in calls
        )

    def _has_optimization_criteria(self, func_name: str) -> bool:
        """Detecta criterios de optimización."""
        calls = self.function_calls.get(func_name, [])
        optimization_keywords = ["costo", "peso", "distancia", "beneficio", "valor"]
        return any(
            any(keyword in call.lower() for keyword in optimization_keywords)
            for call in calls
        )

    def _has_backtracking_pattern(self, func_name: str) -> bool:
        """Detecta patrón de backtracking."""
        # Buscar evidencia de "undo" o exploración de alternativas
        calls = self.function_calls.get(func_name, [])
        backtrack_keywords = ["undo", "revert", "backtrack", "deshacer", "explorar"]
        return any(
            any(keyword in call.lower() for keyword in backtrack_keywords)
            for call in calls
        )

    def _is_helper_function(self, func: SubroutineDef) -> bool:
        """Detecta si es una función auxiliar."""
        if not func.name:
            return False
        helper_indicators = ["helper", "aux", "util", "auxiliar"]
        return any(
            indicator in str(func.name).lower() for indicator in helper_indicators
        )

    def _search_in_children(self, node: ASTNode, predicate: Any) -> bool:
        """Busca recursivamente en nodos hijos."""
        for child in self._get_children(node):
            if predicate(child) or self._search_in_children(child, predicate):
                return True
        return False

    def _visit_children(self, node: ASTNode) -> None:
        """Visita todos los nodos hijos."""
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
