from app.core.language.ast.visitor import DefaultASTVisitor

class ASTPrinterVisitor(DefaultASTVisitor):
    """
    Visitor que recorre el AST y lo imprime de forma jerárquica.
    """

    def __init__(self):
        self._indent = 0

    def _print(self, text: str):
        print("  " * self._indent + text)

    def _safe_accept(self, item):
        """
        Intenta llamar a accept() si el objeto lo tiene; 
        si no, imprime su contenido directamente.
        """
        if hasattr(item, "accept"):
            item.accept(self)
        elif isinstance(item, tuple):
            self._print(f"Tuple: {item}")
        else:
            self._print(str(item))

    # --- Programa principal ---
    def visit_program(self, node):
        self._print("📘 Program")
        self._indent += 1
        for stmt in node.statements:
            self._safe_accept(stmt)
        self._indent -= 1

    # --- Comentarios ---
    def visit_comment(self, node):
        self._print(f"🗒️ Comment: {node.text}")

    # --- Declaraciones ---
    def visit_var_decl(self, node):
        self._print("📦 VarDecl")
        self._indent += 1
        for item in node.items:
            self._safe_accept(item)
        self._indent -= 1

    def visit_assignment(self, node):
        self._print("🧮 Assignment")
        self._indent += 1
        self._print("Target:")
        self._indent += 1
        self._safe_accept(node.target)
        self._indent -= 1
        self._print("Value:")
        self._indent += 1
        self._safe_accept(node.value)
        self._indent -= 1
        self._indent -= 1

    def visit_var_target(self, node):
        self._print(f"🎯 VarTarget: {node.name}")

    # --- Tipos de valores ---
    def visit_number(self, node):
        self._print(f"🔢 Number: {node.value}")

    def visit_string(self, node):
        self._print(f"💬 String: {node.value}")

    def visit_bool(self, node):
        self._print(f"🔘 Bool: {node.value}")

    def visit_null(self, node):
        self._print("∅ Null")

    # --- Estructuras de control ---
    def visit_for_loop(self, node):
        self._print(f"🔁 ForLoop var={node.var}")
        self._indent += 1
        self._print("Start:")
        self._indent += 1
        self._safe_accept(node.start)
        self._indent -= 1
        self._print("End:")
        self._indent += 1
        self._safe_accept(node.end)
        self._indent -= 1
        self._print("Body:")
        self._indent += 1
        for stmt in node.body:
            self._safe_accept(stmt)
        self._indent -= 1
        self._indent -= 1

    def visit_if_else(self, node):
        self._print("⚖️ IfElse")
        self._indent += 1
        self._print("Condition:")
        self._indent += 1
        self._safe_accept(node.cond)
        self._indent -= 1
        self._print("Then:")
        self._indent += 1
        for stmt in node.then_branch:
            self._safe_accept(stmt)
        self._indent -= 1
        if node.else_branch:
            self._print("Else:")
            self._indent += 1
            for stmt in node.else_branch:
                self._safe_accept(stmt)
            self._indent -= 1
        self._indent -= 1

    def visit_call_stmt(self, node):
        self._print(f"📞 CallStmt: {node.name}")
        self._indent += 1
        for arg in node.args:
            self._safe_accept(arg)
        self._indent -= 1
