

from app.core.language.ast.visitor import DefaultASTVisitor


class ASTAnalyzerVisitor(DefaultASTVisitor):
    """
    Visitor que analiza el AST para detectar estructuras algorítmicas
    y estimar su complejidad temporal de manera preliminar.
    """

    def __init__(self):
        self.results = []
        self.current_level = 0
        self.has_recursion = False

    # Utilidad de impresión estructurada
    def _add_result(self, text):
        self.results.append("  " * self.current_level + text)

    # ---------------------------------------------
    # Programa principal
    # ---------------------------------------------
    def visit_program(self, node):
        self._add_result("📘 Programa detectado")
        self.current_level += 1

        for stmt in node.statements:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

        self.current_level -= 1
        self._add_result("✅ Fin del análisis del programa")

        # Resumen final
        self._add_result("\n📊 Resumen del análisis:")
        if self.has_recursion:
            self._add_result("- Tipo de algoritmo: Recursivo")
        else:
            self._add_result("- Tipo de algoritmo: Iterativo")

    # ---------------------------------------------
    # Declaraciones
    # ---------------------------------------------
    def visit_var_decl(self, node):
        self._add_result("📦 Declaración de variables (costo constante O(1))")

    def visit_assignment(self, node):
        self._add_result("🧮 Asignación detectada → O(1)")

    # ---------------------------------------------
    # Estructuras de control
    # ---------------------------------------------
    def visit_for_loop(self, node):
        self._add_result("🔁 Bucle FOR detectado → comportamiento iterativo O(n)")
        self.current_level += 1

        for stmt in node.body:
            if hasattr(stmt, "accept"):
                stmt.accept(self)

        self.current_level -= 1

    def visit_if_else(self, node):
        self._add_result("⚖️ Estructura IF-ELSE detectada")
        self.current_level += 1

        self._add_result("Condición evaluada → costo O(1)")

        self._add_result("Rama THEN:")
        self.current_level += 1
        for stmt in node.then_branch:
            if hasattr(stmt, "accept"):
                stmt.accept(self)
        self.current_level -= 1

        if node.else_branch:
            self._add_result("Rama ELSE:")
            self.current_level += 1
            for stmt in node.else_branch:
                if hasattr(stmt, "accept"):
                    stmt.accept(self)
            self.current_level -= 1

        self.current_level -= 1

    # ---------------------------------------------
    # Llamadas y recursión
    # ---------------------------------------------
    def visit_call_stmt(self, node):
        name = getattr(node, "name", "")
        self._add_result(f"📞 Llamada a función: {name}")

        # Heurística simple: detectar recursión
        if name.lower() in ["f", "recurse", "self", "main"]:
            self.has_recursion = True
            self._add_result("🔁 Recursión detectada → relación de recurrencia potencial")

    # ---------------------------------------------
    # Valores
    # ---------------------------------------------
    def visit_number(self, node):
        self._add_result(f"🔢 Número literal: {node.value}")

    def visit_string(self, node):
        self._add_result(f"💬 Cadena literal: {node.value}")

    def visit_bool(self, node):
        self._add_result(f"🔘 Valor booleano: {node.value}")

    def visit_null(self, node):
        self._add_result("∅ Valor nulo")

    # ---------------------------------------------
    # Resultado final
    # ---------------------------------------------
    def get_report(self):
        """
        Devuelve el análisis completo como un texto formateado.
        """
        return "\n".join(self.results)
