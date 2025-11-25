"""Utility helpers to sanitize raw user inputs before translation/parsing."""

import re
from dataclasses import dataclass
from typing import Dict, List

from app.core.constants import LLM_MAX_INPUT_LENGTH


@dataclass
class SanitizationReport:
    """Represents the outcome of the sanitization phase."""

    text: str
    truncated: bool
    removed_non_ascii: bool
    operations: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "text": self.text,
            "truncated": self.truncated,
            "removed_non_ascii": self.removed_non_ascii,
            "operations": self.operations,
        }


class InputSanitizer:
    """Normalizes whitespace, replaces unsupported glyphs and enforces limits."""

    _REPLACEMENTS = {
        "🡨": "<-",
        "←": "<-",
        "→": "<-",
        "⇒": "<-",
        "►": "#",
        "•": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    }

    def __init__(self, max_length: int = LLM_MAX_INPUT_LENGTH):
        self.max_length = max_length

    def sanitize(self, raw_text: str) -> SanitizationReport:
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.strip()
        operations: List[str] = []

        for needle, replacement in self._REPLACEMENTS.items():
            if needle in text:
                text = text.replace(needle, replacement)
                operations.append(f"replace:{needle}->{replacement}")

        removed_non_ascii = False
        if not self._is_ascii(text):
            removed_non_ascii = True
            text = text.encode("ascii", "ignore").decode("ascii")
            operations.append("strip_non_ascii")

        if len(text) > self.max_length:
            text = text[: self.max_length]
            operations.append("truncate")
            truncated = True
        else:
            truncated = False

        text = self._collapse_whitespace(text)

        return SanitizationReport(
            text=text,
            truncated=truncated,
            removed_non_ascii=removed_non_ascii,
            operations=operations,
        )

    def _is_ascii(self, value: str) -> bool:
        try:
            value.encode("ascii")
            return True
        except UnicodeEncodeError:
            return False

    def _collapse_whitespace(self, value: str) -> str:
        collapsed = re.sub(r"[\t ]+", " ", value)
        collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
        return collapsed.strip()
