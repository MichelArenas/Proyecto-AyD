"""
Service layer for pseudocode validation and persistence.
"""

from dataclasses import asdict
from typing import Any, Dict, List

from app.core.language.language_parser import LanguageParser
from app.core.storage.mongodb import validation_repo
from app.core.validators.validation_suite import ValidationSuite


class ValidationService:
    """Service for pseudocode validation with optional persistence"""

    def __init__(self):
        self.parser = LanguageParser()
        self.validator = ValidationSuite()

    def validate_pseudocode(
        self, pseudocode: str, save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Validate pseudocode and optionally save results to database
        """
        try:
            ast = self.parser.parse(pseudocode)

            validation_result: Dict[str, Any] = self.validator.validate(ast)

            error_list: List[Dict[str, Any]] = []

            warnings = []
            for warning in validation_result.get("all_warnings", []):
                if hasattr(warning, "__dataclass_fields__"):
                    warnings.append(asdict(warning))
                elif isinstance(warning, dict):
                    warnings.append(warning)
                else:
                    warnings.append({"message": str(warning)})

            detected_patterns = []
            for pattern in validation_result.get("detected_patterns", []):
                if hasattr(pattern, "__dataclass_fields__"):
                    detected_patterns.append(asdict(pattern))
                elif isinstance(pattern, dict):
                    detected_patterns.append(pattern)
                else:
                    detected_patterns.append({"type": str(pattern)})

            pattern_summary = validation_result.get("pattern_summary", {})

            for error_type in ["syntax_errors", "null_errors", "semantic_errors"]:
                for error in validation_result.get(error_type, []):
                    if hasattr(error, "__dataclass_fields__"):
                        error_list.append(asdict(error))
                    elif isinstance(error, dict):
                        error_list.append(error)
                    else:
                        error_list.append({"message": str(error)})

            is_valid = len(error_list) == 0

            result = {
                "is_valid": is_valid,
                "error_count": len(error_list),
                "warning_count": len(warnings),
                "errors": error_list,
                "warnings": warnings,
                "detected_patterns": detected_patterns,
                "pattern_summary": pattern_summary,
                "validation_types": [
                    "syntax",
                    "semantic",
                    "null_safety",
                    "pattern",
                    "loop",
                    "recursion",
                ],
            }

            if save_to_db:
                try:
                    doc_id = validation_repo.save_validation(
                        pseudocode=pseudocode,
                        is_valid=is_valid,
                        errors=error_list,
                        warnings=warnings,
                        validation_types=result["validation_types"],
                        detected_patterns=detected_patterns,
                        pattern_summary=pattern_summary,
                    )
                    result["db_id"] = doc_id
                except Exception as e:
                    result["db_error"] = str(e)

            return result

        except Exception as e:
            return {
                "is_valid": False,
                "errors": [
                    {
                        "type": "ParseError",
                        "message": str(e),
                        "line": None,
                        "column": None,
                    }
                ],
                "warnings": [],
                "error_count": 1,
                "warning_count": 0,
                "validation_types": [],
            }
