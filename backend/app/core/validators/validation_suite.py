"""
Validation suite for programs in the custom language.
"""

from typing import Any, Dict, List, Union

from app.core.exceptions import ValidationError
from app.core.language.ast import Program
from app.core.validators import (NullSafetyValidator, PatternValidator,
                                 SemanticValidator, SyntaxValidator)


class ValidationSuite:
    """
    Integrates multiple validators for the language.
    """

    def __init__(self):
        self.syntax_validator = SyntaxValidator()
        self.null_safety_validator = NullSafetyValidator()
        self.semantic_validator = SemanticValidator()
        self.pattern_validator = PatternValidator()

    def validate(self, program: Program) -> Dict[str, Union[List[Any], Dict[str, Any]]]:

        results: Dict[str, Any] = {
            "syntax_errors": [],
            "null_errors": [],
            "all_warnings": [],
            "detected_patterns": [],
            "pattern_summary": {},
        }

        try:
            syntax_errors, syntax_warnings = self.syntax_validator.validate(program)

            null_errors, null_warnings = (
                self.null_safety_validator.validate_null_safety(program)
            )

            semantic_errors, semantic_warnings = self.semantic_validator.validate(
                program
            )

            detected_patterns = self.pattern_validator.validate_patterns(program)

            all_warnings = syntax_warnings + null_warnings + semantic_warnings

            results = {
                "syntax_errors": syntax_errors,
                "null_errors": null_errors,
                "semantic_errors": semantic_errors,
                "all_warnings": all_warnings,
                "detected_patterns": [
                    {
                        "type": pattern.pattern_type,
                        "confidence": pattern.confidence,
                        "location": pattern.location,
                        "description": pattern.description,
                        "evidence": pattern.evidence,
                    }
                    for pattern in detected_patterns
                ],
                "pattern_summary": self.pattern_validator.get_pattern_summary(),
            }

        except ValidationError as e:
            results["syntax_errors"].append(
                {
                    "type": "InternalError",
                    "message": f"An internal error occurred during validation: {str(e)}",
                }
            )

        return results
