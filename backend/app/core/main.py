from app.core.language.language_parser import LanguageParser
from app.core.language.ast.ast_printer import ASTPrinterVisitor
from app.core.language.ast.ast_analyzer import ASTAnalyzerVisitor
from app.core.validators.validation_suite import ValidationSuite

def main():
    code = """
    var b, s, t
   a <- 0
   n <- 10
for i <- 1 to n do
begin
    for j <- 1 to n do
    begin
        a <- a + 1
    end
end
if a > 10 then
begin
    call f()
end

    """

    parser = LanguageParser()
    ast = parser.parse(code)

    print(ValidationSuite().validate_program(ast))

    # ✅ 1. Imprimir AST
    print("✅ AST generado:\n")
    printer = ASTPrinterVisitor()
    ast.accept(printer)

    # ✅ 2. Analizar estructura y complejidad
    print("\n🔍 Análisis de complejidad:\n")
    analyzer = ASTAnalyzerVisitor()
    ast.accept(analyzer)
    print(analyzer.get_report())


if __name__ == "__main__":
    main()
