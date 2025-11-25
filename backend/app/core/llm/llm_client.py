"""
Refactored LLM Client Module - High-level coordinator for LLM interactions.
Delegates input type detection and pseudocode translation to specialized classes.
"""

import json
from typing import Dict, Optional

import anthropic
import google.generativeai as genai
import openai

from app.core import config
from app.core.constants import LLM_MODELS
from app.core.llm.input_detector import InputTypeDetector
from app.core.llm.translator import PseudocodeTranslator


class LLMClient:
    """
    High-level LLM client that coordinates input detection and translation.
    Delegates specialized tasks to InputTypeDetector and PseudocodeTranslator.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or config.llm.default_provider
        self.api_key = config.llm.get_api_key(self.provider)
        self.client = self._initialize_client()

        self.detector = InputTypeDetector()
        self.translator = (
            PseudocodeTranslator(self.provider, self.client, self.api_key)
            if self.client
            else None
        )

    def _initialize_client(self):
        """Initializes the LLM client based on the provider."""
        if not self.api_key:
            return None

        try:
            print("Initializing LLM client for provider:", self.provider)
            if self.provider == "openai":
                return openai.OpenAI(api_key=self.api_key)

            if self.provider == "anthropic":
                return anthropic.Anthropic(api_key=self.api_key)

            if self.provider == "google":
                genai.configure(api_key=self.api_key)
                return genai.GenerativeModel(LLM_MODELS["google"])

            if self.provider == "github":
                return openai.OpenAI(
                    base_url="https://models.inference.ai.azure.com",
                    api_key=self.api_key,
                )

        except Exception:
            raise RuntimeError(
                f"Failed to initialize LLM client for provider: {self.provider}"
            ) from None

        return None

    def detect_input_type(self, text: str):
        """Delegates detection to InputTypeDetector."""
        return self.detector.detect_input_type(text)

    def process_input(self, input_text: str) -> Dict[str, Optional[object]]:
        """Processes input by detecting type and translating if necessary."""
        input_type, confidence = self.detect_input_type(input_text)

        result = {
            "input_type": input_type,
            "confidence": confidence,
            "translated": False,
            "pseudocode": input_text,
            "provider": self.provider,
        }

        if input_type == "natural_language":
            if not self.translator:
                raise RuntimeError("LLM translator not initialized")
            translated = self.translator.translate(input_text)
            result["pseudocode"] = translated
            result["translated"] = True

        return result

    def translate_to_pseudocode(self, natural_language: str) -> str:
        """Delegates translation to PseudocodeTranslator."""
        if not self.translator:
            raise RuntimeError("LLM translator not initialized")
        return self.translator.translate(natural_language)

    def fix_pseudocode(self, pseudocode: str, errors: str) -> str:
        """Delegates syntax fixing to PseudocodeTranslator."""
        if not self.translator:
            raise RuntimeError("LLM translator not initialized")
        return self.translator.fix_pseudocode(pseudocode, errors)

    def explain_complexity(self, pseudocode: str, complexity_result: str) -> str:
        """
        Uses LLM to generate explanation of complexity analysis.
        """
        if not self.client:
            return "LLM not available for explanation generation."

        prompt = f"""Given this algorithm:
                    {pseudocode}

                    And this complexity analysis:
                    {complexity_result}

                    Provide a clear, educational explanation of:
                    1. Why this complexity was determined
                    2. Which parts of the algorithm contribute most to the complexity
                    3. Key insights about the algorithm's efficiency

                    Keep it concise (3-4 paragraphs):
                """

        try:
            return (
                self.translator.call_llm(prompt)
                if self.translator
                else "LLM not available"
            )
        except Exception as e:
            return f"Error generating explanation: {e}"

    def verify_complexity(self, pseudocode: str, calculated_complexity: str) -> dict:
        """
        Uses LLM to verify the calculated time complexity.
        """
        if not self.client:
            return {
                "agrees": True,
                "reasoning": "LLM not available",
                "alternative": None,
            }

        prompt = f"""Analyze this algorithm's time complexity:
                    {pseudocode}

                    Our analysis calculated: {calculated_complexity}
                    
                    Does this seem correct? Respond in JSON format:
                    {{
                        "agrees": true/false,
                        "reasoning": "brief explanation",
                        "alternative": "alternative complexity if you disagree, or null"
                    }}
                """

        try:
            response = self.translator.call_llm(prompt) if self.translator else "{}"

            start = response.find("{")
            end = response.rfind("}") + 1
            if 0 <= start < end:
                return json.loads(response[start:end])

            return {
                "agrees": True,
                "reasoning": "Could not parse response",
                "alternative": None,
            }
        except Exception as e:
            return {"agrees": True, "reasoning": f"Error: {e}", "alternative": None}
