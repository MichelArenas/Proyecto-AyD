"""
Module for translating natural language to pseudocode using LLMs with retry logic.
"""

import logging

from app.core.constants import (ERROR_EMPTY_RESULT, ERROR_LLM_NOT_INITIALIZED,
                                ERROR_TRANSLATION_FAILED,
                                GEMINI_FINISH_REASON_OTHER,
                                GEMINI_FINISH_REASON_RECITATION,
                                GEMINI_FINISH_REASON_SAFETY,
                                GOOGLE_SAFETY_SETTINGS, LLM_MAX_INPUT_LENGTH,
                                LLM_MAX_TOKENS, LLM_MODELS,
                                LLM_TEMPERATURE_DETERMINISTIC,
                                MIN_PSEUDOCODE_LENGTH, SYSTEM_INSTRUCTIONS,
                                SYSTEM_INSTRUCTIONS_FIXER,
                                SYSTEM_INSTRUCTIONS_SIMPLIFIED,
                                TRANSLATION_STRATEGIES)

logger = logging.getLogger(__name__)


class PseudocodeTranslator:
    """
    Translates natural language to pseudocode using LLMs with retry logic.
    Implements multiple strategies to handle errors and ensure successful translation.
    """

    def __init__(self, provider: str, client, api_key: str):
        self.provider = provider
        self.client = client
        self.api_key = api_key

    def translate(self, natural_language: str) -> str:
        """
        Translates natural language to pseudocode using multiple strategies.
        Retries with different strategies on failure.
        """
        logger.info("Translating input of length %d", len(natural_language))
        if not self.client:
            raise RuntimeError(ERROR_LLM_NOT_INITIALIZED)

        strategies = [
            (TRANSLATION_STRATEGIES[0], self._translate_standard),
            (TRANSLATION_STRATEGIES[1], self._translate_simplified),
        ]

        last_error = None
        for strategy_name, strategy_func in strategies:
            try:
                result = strategy_func(natural_language)
                if result and len(result.strip()) > MIN_PSEUDOCODE_LENGTH:
                    return result
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if (
                    "quota" in error_str
                    or "429" in error_str
                    or "resourceexhausted" in str(type(e)).lower()
                ):
                    raise RuntimeError(
                        f"LLM quota exceeded. Translation failed using strategy: {strategy_name}"
                    ) from e

                if "safety filter" in error_str or "blocked" in error_str:
                    continue

                if strategy_name == TRANSLATION_STRATEGIES[0]:
                    continue
                raise

        if last_error:
            raise RuntimeError(
                f"{ERROR_TRANSLATION_FAILED}: {last_error}"
            ) from last_error
        raise RuntimeError(ERROR_EMPTY_RESULT)

    def _translate_standard(self, natural_language: str) -> str:
        """Standard translation prompt."""
        prompt = SYSTEM_INSTRUCTIONS % natural_language
        response = self.call_llm(prompt)
        return self._extract_pseudocode(response)

    def _translate_simplified(self, natural_language: str) -> str:
        """Simplified translation prompt for complex inputs."""
        text = (
            natural_language[:LLM_MAX_INPUT_LENGTH]
            if len(natural_language) > LLM_MAX_INPUT_LENGTH
            else natural_language
        )
        prompt = SYSTEM_INSTRUCTIONS_SIMPLIFIED % text

        response = self.call_llm(prompt)
        return self._extract_pseudocode(response)

    def fix_pseudocode(self, pseudocode: str, errors: str) -> str:
        """Attempt to repair invalid pseudocode using the fixer prompt."""
        if not self.client:
            raise RuntimeError(ERROR_LLM_NOT_INITIALIZED)

        prompt = SYSTEM_INSTRUCTIONS_FIXER.format(
            pseudocode=pseudocode.strip(), errors=errors.strip() or "unknown"
        )
        response = self.call_llm(prompt)
        return self._extract_pseudocode(response)

    def call_llm(self, prompt: str) -> str:
        """Calls the appropriate LLM based on the provider."""

        if self.provider in ["openai", "github"]:
            return self._call_openai_compatible(prompt)

        if self.provider == "anthropic":
            return self._call_anthropic(prompt)

        if self.provider == "google":
            return self._call_google(prompt)

        raise ValueError(f"Unsupported provider: {self.provider}")

    def _call_openai_compatible(self, prompt: str) -> str:
        """Calls OpenAI or GitHub Copilot."""
        model = LLM_MODELS.get(self.provider, LLM_MODELS["openai"])
        logger.info(prompt)
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=LLM_TEMPERATURE_DETERMINISTIC,
            max_tokens=LLM_MAX_TOKENS,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, prompt: str) -> str:
        """Calls Anthropic Claude."""
        response = self.client.messages.create(
            model=LLM_MODELS["anthropic"],
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE_DETERMINISTIC,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _call_google(self, prompt: str) -> str:
        """Calls Google Gemini."""
        full_prompt = SYSTEM_INSTRUCTIONS + "\n\n" + prompt

        try:
            response = self.client.generate_content(
                full_prompt,
                generation_config={
                    "temperature": LLM_TEMPERATURE_DETERMINISTIC,
                    "max_output_tokens": LLM_MAX_TOKENS,
                },
                safety_settings=GOOGLE_SAFETY_SETTINGS,
            )
        except Exception:
            response = self.client.generate_content(
                full_prompt,
                generation_config={
                    "temperature": LLM_TEMPERATURE_DETERMINISTIC,
                    "max_output_tokens": LLM_MAX_TOKENS,
                },
            )

        if not response.candidates:
            raise RuntimeError("Response was blocked by safety filters")

        candidate = response.candidates[0]

        if candidate.finish_reason == GEMINI_FINISH_REASON_SAFETY:
            raise RuntimeError(
                "Response blocked by safety filters. Try rephrasing your input."
            )
        if candidate.finish_reason == GEMINI_FINISH_REASON_RECITATION:
            raise RuntimeError(
                "Response blocked due to recitation. Try rephrasing your input."
            )
        if candidate.finish_reason == GEMINI_FINISH_REASON_OTHER:
            raise RuntimeError(
                "Response blocked for other reasons. Try simplifying your input."
            )
        if not response.text:
            raise RuntimeError(
                f"No text in response. Finish reason: {candidate.finish_reason}"
            )

        return response.text

    def _extract_pseudocode(self, response: str) -> str:
        """Extracts pseudocode from LLM response, removing code block markers."""
        lines = response.strip().split("\n")

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        return "\n".join(lines).strip()
