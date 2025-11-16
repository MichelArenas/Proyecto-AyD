from app.core.language.language_parser import LanguageParser
from app.core.validators.validation_suite import ValidationSuite


def main():
    pseudo_code = """
    ► Demo completo para probar la gramática
► Definición de clases (deben ir antes del algoritmo principal)
class Person { name age }
class Casa { Area color propietario }

► Subrutina con parámetro arreglo unidimensional
sumArray(arr[])
begin
    var i, s
    i <- 1
    s <- 0
    for i <- 1 to length(arr) do
    begin
        s <- s + arr[i]
    end
    return s
end

"""
    parser = LanguageParser()
    result = parser.parse(pseudo_code)
    print(result)
    validator = ValidationSuite()
    result = validator.validate_program(result)
    print(result)


if __name__ == "__main__":
    main()
