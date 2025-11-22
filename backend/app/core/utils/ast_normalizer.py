"""
AST normalizer for the language parser.
Provides normalization utilities for AST nodes and tokens.
"""

from typing import Any

from lark import Token, Tree, logger

from app.core.exceptions.exception import ParsingError
from app.core.interfaces.ast_normalizer import IASTNormalizer
from app.core.language.ast.node import Bool, Null, Number, String, Var


class ASTNormalizer(IASTNormalizer):
    """
    Normalizes AST nodes and tokens for the language parser.
    """

    def __init__(self, transformer: Any):
        """
        Initialize the ASTNormalizer with a transformer.
        """
        self._transformer = transformer

    def normalize(self, node: Any) -> Any:
        """
        Normalize an AST node or token recursively.
        """
        return self._normalize_recursive(node)

    def _normalize_recursive(self, x: Any) -> Any:
        """
        Recursively normalize tokens, trees, objects, lists, and tuples.
        """
        if isinstance(x, Token):
            return self._normalize_token(x)

        if isinstance(x, Tree):
            return self._normalize_tree(x)

        if hasattr(x, "__dict__"):
            return self._normalize_object(x)

        if isinstance(x, list):
            return [self._normalize_recursive(e) for e in x]

        if isinstance(x, tuple):
            return tuple(self._normalize_recursive(e) for e in x)

        return x

    def _normalize_token(self, token: Token) -> Any:
        """
        Normalize a token using the transformer or by type.
        """
        handler = getattr(self._transformer, token.type, None)
        if callable(handler):
            try:
                return handler(token)
            except ParsingError:
                pass

        match token.type:
            case "NUMBER":
                s = token.value
                return Number(value=float(s) if "." in s else int(s))
            case "STRING":
                return String(value=token.value[1:-1])
            case "VAR":
                return Var(name=token.value)
            case "TRUE":
                return Bool(True)
            case "FALSE":
                return Bool(False)
            case "NULL":
                return Null()
            case _:
                return token.value if hasattr(token, "value") else str(token)

    def _normalize_tree(self, tree: Tree) -> Any:
        """
        Normalize a tree node using the transformer and its children.
        """
        method_name = tree.data
        method = getattr(self._transformer, method_name, None)
        normalized_children = [
            self._normalize_recursive(child) for child in tree.children
        ]

        if callable(method):
            try:
                result = method(*normalized_children)
                return self._normalize_recursive(result)
            except ParsingError as e:
                logger.debug(f"ParsingError in Tree {method_name}: {e}")
                return tree
        else:
            return (
                normalized_children[0]
                if len(normalized_children) == 1
                else normalized_children
            )

    def _normalize_object(self, obj: Any) -> Any:
        """
        Normalize all attributes of an object recursively.
        """
        for k, v in list(vars(obj).items()):
            setattr(obj, k, self._normalize_recursive(v))
        return obj
