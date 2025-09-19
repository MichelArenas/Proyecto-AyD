"""
Exceptions for a custom programming language interpreter.
"""


class LanguageError(Exception):
    """Excepction base for language-related errors"""


class ParsingError(LanguageError):
    """Error ocurred during parsing"""


class ValidationError(LanguageError):
    """Error ocurred during validation"""
