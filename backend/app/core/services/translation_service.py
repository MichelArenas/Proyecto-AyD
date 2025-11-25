"""Service for intelligent input processing and translation with caching."""

from typing import Any, Dict, Optional

from app.core.constants import (ERROR_QUOTA_EXCEEDED, ERROR_TRANSLATION_FAILED,
                                ERROR_UNEXPECTED, NATURAL_LANGUAGE)
from app.core.llm import LLMClient
from app.core.services.validation_service import ValidationService
from app.core.storage.mongodb import translation_repo
from app.core.utils import InputSanitizer


class TranslationService:
    """Service for intelligent input processing and translation"""

    def __init__(self, provider: Optional[str] = None):
        self.llm_client = LLMClient(provider=provider)
        self.validation_service = ValidationService()
        self.input_sanitizer = InputSanitizer()

    def process_input(
        self,
        input_text: str,
        validate: bool = True,
        save_to_db: bool = True,
        use_cache: bool = True,
        declared_input_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process input text (natural language or pseudocode) and translate if needed
        """
        sanitization = self.input_sanitizer.sanitize(input_text)
        normalized_text = sanitization.text

        if save_to_db and use_cache:
            cached = translation_repo.find_by_input_hash(normalized_text)
            if cached:
                result = {
                    "input_type": cached.get("input_type"),
                    "confidence": 1.0,
                    "pseudocode": cached.get("output_pseudocode"),
                    "translated": cached.get("input_type") == NATURAL_LANGUAGE,
                    "provider": cached.get("provider"),
                    "cached": True,
                    "db_id": cached.get("_id"),
                    "sanitization": sanitization.to_dict(),
                }

                if validate:
                    validation_result = self.validation_service.validate_pseudocode(
                        result["pseudocode"], save_to_db=False
                    )
                    result["validation"] = validation_result

                return result
        forced_type = self._normalize_declared_type(declared_input_type)

        if forced_type == "pseudocode":
            processed_pseudocode = normalized_text
            result = {
                "input_type": "pseudocode",
                "confidence": 1.0,
                "pseudocode": input_text,
                "translated": False,
                "provider": self.llm_client.provider,
                "cached": False,
                "sanitization": sanitization.to_dict(),
            }
            if validate:
                validation_result = self.validation_service.validate_pseudocode(
                    processed_pseudocode, save_to_db=save_to_db
                )
                result["validation"] = validation_result
            if save_to_db:
                self._persist_translation(
                    normalized_text,
                    result["input_type"],
                    processed_pseudocode,
                    result["provider"],
                    result.get("validation"),
                )
            return result

        try:
            if forced_type == NATURAL_LANGUAGE:
                translated = self.llm_client.translate_to_pseudocode(normalized_text)
                llm_result = {
                    "input_type": NATURAL_LANGUAGE,
                    "confidence": 0.95,
                    "pseudocode": translated,
                    "translated": True,
                    "provider": self.llm_client.provider,
                }
            else:
                llm_result = self.llm_client.process_input(normalized_text)

            processed_pseudocode = llm_result["pseudocode"]
            result = {
                "input_type": llm_result["input_type"],
                "confidence": llm_result["confidence"],
                "pseudocode": llm_result["pseudocode"],
                "translated": llm_result["translated"],
                "provider": llm_result["provider"],
                "cached": False,
                "sanitization": sanitization.to_dict(),
            }

            if validate:
                validation_result = self.validation_service.validate_pseudocode(
                    processed_pseudocode, save_to_db=save_to_db
                )
                result["validation"] = validation_result

            if (
                result["input_type"] == "pseudocode"
                and result.get("translated") is False
            ):
                result["pseudocode"] = input_text

            if save_to_db:
                try:
                    doc_id = self._persist_translation(
                        normalized_text,
                        result["input_type"],
                        processed_pseudocode,
                        result["provider"],
                        result.get("validation"),
                        confidence=result["confidence"],
                        translated=result["translated"],
                    )
                    result["db_id"] = doc_id
                except Exception as e:
                    result["db_error"] = str(e)

            return result

        except RuntimeError as e:
            error_msg = str(e)
            error_lower = error_msg.lower()

            if "not initialized" in error_lower:
                error_type = ERROR_TRANSLATION_FAILED
                user_msg = (
                    f"Translation failed: LLM client for {self.llm_client.provider}"
                    "is not properly initialized."
                )
            elif "quota" in error_lower or "429" in error_msg:

                error_type = ERROR_QUOTA_EXCEEDED
                user_msg = (
                    f"LLM API quota exceeded for {self.llm_client.provider}. "
                    "Please try again later."
                )
            else:
                error_type = ERROR_TRANSLATION_FAILED
                user_msg = error_msg

            return {
                "input_type": NATURAL_LANGUAGE,
                "confidence": 0.8,
                "pseudocode": input_text,
                "translated": False,
                "provider": self.llm_client.provider,
                "cached": False,
                "error": user_msg,
                "error_type": error_type,
            }
        except Exception as e:
            try:
                input_type, confidence = self.llm_client.detect_input_type(
                    normalized_text
                )
            except Exception:
                input_type = "unknown"
                confidence = 0.0

            return {
                "input_type": input_type,
                "confidence": confidence,
                "pseudocode": normalized_text,
                "translated": False,
                "provider": (
                    self.llm_client.provider if self.llm_client.provider else "unknown"
                ),
                "cached": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": ERROR_UNEXPECTED,
                "sanitization": sanitization.to_dict(),
            }

    def auto_fix_pseudocode(self, pseudocode: str, errors: str) -> Dict[str, Any]:
        """Use the configured LLM client to attempt syntax remediation."""
        fixed = self.llm_client.fix_pseudocode(pseudocode, errors)
        return {
            "pseudocode": fixed,
            "provider": self.llm_client.provider,
        }

    def _normalize_declared_type(self, declared: Optional[str]) -> Optional[str]:
        if not declared:
            return None
        normalized = declared.lower()
        if normalized in {"pseudocode", "pseudo"}:
            return "pseudocode"
        if normalized in {"nl", "natural", NATURAL_LANGUAGE}:
            return NATURAL_LANGUAGE
        if normalized == "auto":
            return None
        return None

    def _persist_translation(
        self,
        input_text: str,
        input_type: str,
        output_pseudocode: str,
        provider: Optional[str],
        validation: Optional[Dict[str, Any]],
        confidence: float = 1.0,
        translated: bool = False,
    ) -> str:
        metadata = {
            "confidence": confidence,
            "translated": translated,
            "validation": validation or {},
        }
        return translation_repo.save_translation(
            input_text=input_text,
            input_type=input_type,
            output_pseudocode=output_pseudocode,
            provider=provider or "unknown",
            metadata=metadata,
        )
