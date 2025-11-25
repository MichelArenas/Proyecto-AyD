"""
Module for detecting if input text is natural language or pseudocode.
"""

import re
from typing import List, Tuple

from langdetect import LangDetectException, detect

from app.core.constants import (CODE_RATIO_THRESHOLD,
                                EXPLANATORY_RATIO_DOMINANT,
                                EXPLANATORY_RATIO_EXTREMELY_HIGH,
                                EXPLANATORY_RATIO_HIGH, EXPLANATORY_RATIO_LOW,
                                EXPLANATORY_RATIO_MEDIUM, NL_STRONG_SCORE_HIGH,
                                NL_STRONG_SCORE_LOW, NL_STRONG_SCORE_MEDIUM,
                                NL_STRONG_SCORE_VERY_HIGH,
                                PSEUDO_STRONG_SCORE_THRESHOLD,
                                PSEUDOCODE_TOTAL_THRESHOLD, SHORT_INPUT_LENGTH,
                                WEIGHT_CRITICAL, WEIGHT_EXPLANATORY_HIGH,
                                WEIGHT_EXPLANATORY_VERY_HIGH,
                                WEIGHT_HUMAN_LANGUAGE, WEIGHT_MEDIUM,
                                WEIGHT_STRONG)


class InputTypeDetector:
    """
    Detects if input text is natural language or pseudocode.
    """

    def __init__(self):
        self.pseudocode_critical_patterns = [
            (r"\bbegin\b", WEIGHT_CRITICAL, "begin keyword"),
            (r"\bend\b", WEIGHT_CRITICAL, "end keyword"),
            (r"<-", WEIGHT_STRONG + 0.5, "assignment operator"),
        ]

        self.pseudocode_strong_patterns = [
            (r"\bfor\b\s+\w+\s*<-.*\bto\b.*\bdo\b", WEIGHT_STRONG, "for-to-do loop"),
            (r"\bwhile\b\s*\(.*\)\s*\bdo\b", WEIGHT_STRONG, "while-do loop"),
            (r"\brepeat\b", WEIGHT_MEDIUM, "repeat keyword"),
            (r"\bif\b.*\bthen\b", WEIGHT_MEDIUM, "if-then structure"),
            (r"\bvar\b\s+\w+", 1.0, "var declaration"),
        ]

        self.pseudocode_medium_patterns = [
            (r"\breturn\b\s+\w+", 0.8, "return statement"),
            (r"\w+\[[\w\+\-\*]+\]", 0.6, "array indexing"),
            (r"\bclass\b\s+\w+\s*\{", 0.8, "class definition"),
            (r"\bcall\b\s+\w+", 0.7, "call statement"),
            (r"\bnew\b\s+\w+", 0.6, "object instantiation"),
        ]

        self.natural_language_strong_patterns = [
            (
                r"^(create|implement|write|design|develop|build|make)\s+(a|an|the)\s+",
                2.5,
                "imperative instruction",
            ),
            (r"\b(should|must|will|would|could|can)\b", 1.8, "modal verb"),
            (
                r"\b(algorithm|function|program)\s+(that|which|to)\b",
                WEIGHT_STRONG,
                "algorithm description",
            ),
            (r"^\d+\.\s+[A-Z]", WEIGHT_MEDIUM, "numbered list"),
            (
                r"\b(accept|receive|take|get)\s+(a|an|the)\s+\w+\s+(as\s+)?(parameter|input|argument)",
                1.8,
                "parameter description",
            ),
            (
                r"\b(return|output|produce|generate)\s+(a|an|the)\s+\w+",
                WEIGHT_MEDIUM,
                "output description",
            ),
            (
                r"\binclude\b.*\b(helper|auxiliary|utility)\s+(function|method)",
                WEIGHT_MEDIUM,
                "helper description",
            ),
            (
                r"\bby\s+(iterating|looping|traversing|checking|comparing)",
                WEIGHT_MEDIUM,
                "process description",
            ),
        ]

        self.natural_language_medium_patterns = [
            (
                r"\b(first|second|third|next|then|finally|lastly)\b",
                0.8,
                "sequence indicator",
            ),
            (r"\b(each|every|all|any|some)\s+\w+", 0.7, "quantifier"),
            (r"\b(using|with|through|via)\s+(a|an|the)", 0.6, "method description"),
            (r":\s*$", 0.5, "colon at line end"),
        ]

        self.code_anti_nl_patterns = [
            (
                r"^\s*(var|let|const|int|float|string)\s+\w+",
                WEIGHT_MEDIUM,
                "variable declaration syntax",
            ),
            (r"^\s*\w+\s*<-", WEIGHT_MEDIUM, "assignment at line start"),
            (r"^\s*for\s+", 1.2, "for loop at line start"),
            (r"^\s*while\s+", 1.2, "while loop at line start"),
            (r"^\s*if\s+", 1.0, "if statement at line start"),
        ]

    def detect_input_type(self, text: str) -> Tuple[str, float]:
        """
        Detects if the input text is natural language or pseudocode.
        """
        text_lower = text.lower()
        text_lines = [line.strip() for line in text.split("\n") if line.strip()]
        total_lines = len(text_lines)

        human_language_detected, detected_lang = self._detect_human_language(text)
        explanatory_ratio, code_ratio = self._analyze_line_types(text_lines)

        critical_score, critical_matches = self._calculate_critical_score(text_lower)
        pseudo_strong_score = self._calculate_strong_pseudocode_score(text_lower)
        pseudo_medium_score = self._calculate_medium_pseudocode_score(text_lower)
        nl_strong_score = self._calculate_strong_nl_score(text_lower)
        nl_medium_score = self._calculate_medium_nl_score(text_lower)
        anti_nl_score = self._calculate_anti_nl_score(text_lines)

        pseudocode_total = (
            critical_score + pseudo_strong_score + pseudo_medium_score + anti_nl_score
        )
        natural_language_total = nl_strong_score + nl_medium_score

        if human_language_detected:
            natural_language_total += WEIGHT_HUMAN_LANGUAGE

        natural_language_total += self._adjust_for_explanatory_ratio(explanatory_ratio)

        return self._apply_decision_rules(
            text,
            text_lower,
            text_lines,
            explanatory_ratio,
            code_ratio,
            critical_score,
            critical_matches,
            pseudo_strong_score,
            nl_strong_score,
            pseudocode_total,
            natural_language_total,
            human_language_detected,
        )

    def _detect_human_language(self, text: str) -> Tuple[bool, str]:
        """Detects if text is in a human language."""
        try:
            clean_text = re.sub(r"[<>\-\[\](){};]", " ", text)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

            if len(clean_text) > 20:
                detected_lang = detect(clean_text)
                human_languages = [
                    "en",
                    "es",
                    "fr",
                    "de",
                    "it",
                    "pt",
                    "ru",
                    "zh-cn",
                    "ja",
                    "ar",
                ]
                return detected_lang in human_languages, detected_lang
        except (LangDetectException, Exception):
            pass
        return False, ""

    def _analyze_line_types(self, text_lines: List[str]) -> Tuple[float, float]:
        """Analyzes line types to determine ratios."""
        if not text_lines:
            return 0.0, 0.0

        explanatory_lines = 0
        code_structure_lines = 0

        for line in text_lines:
            line_lower = line.lower()

            if self._is_explanatory_line(line, line_lower):
                explanatory_lines += 1

            if self._is_code_structure_line(line_lower):
                code_structure_lines += 1

        total = len(text_lines)
        return explanatory_lines / total, code_structure_lines / total

    def _is_explanatory_line(self, line: str, line_lower: str) -> bool:
        """Checks if a line is explanatory."""
        checks = [
            line_lower.startswith(
                ("create", "implement", "write", "design", "build", "make", "develop")
            ),
            re.search(
                r"^(the|this|that|an|a)\s+\w+\s+(should|must|will|can|could)",
                line_lower,
            ),
            re.search(r"^\d+\.\s+", line),
            re.search(r"^-\s+", line),
            "should" in line_lower or "must" in line_lower or "will" in line_lower,
            line_lower.startswith(("to ", "for example", "such as", "like ", "using ")),
            re.search(
                r"\b(accept|receive|return|output|take|get)\s+(a|an|the)\s+\w+",
                line_lower,
            ),
        ]
        return any(checks)

    def _is_code_structure_line(self, line_lower: str) -> bool:
        """Checks if a line has code structure."""
        checks = [
            line_lower.strip() in ["begin", "end"],
            re.match(r"^\w+\s*<-", line_lower),
            re.match(r"^(for|while|if|repeat)\s+", line_lower),
            re.match(r"^(var|return)\s+", line_lower),
        ]
        return any(checks)

    def _calculate_critical_score(self, text_lower: str) -> Tuple[float, List[str]]:
        """Calculates the score for critical pseudocode patterns."""
        score = 0.0
        matches = []
        for pattern, weight, desc in self.pseudocode_critical_patterns:
            if re.search(pattern, text_lower, re.MULTILINE):
                score += weight
                matches.append(desc)
        return score, matches

    def _calculate_strong_pseudocode_score(self, text_lower: str) -> float:
        """Calculates score for strong pseudocode patterns."""
        score = 0.0
        for pattern, weight, _ in self.pseudocode_strong_patterns:
            if re.search(pattern, text_lower, re.MULTILINE):
                score += weight
        return score

    def _calculate_medium_pseudocode_score(self, text_lower: str) -> float:
        """Calculates score for medium pseudocode patterns."""
        score = 0.0
        for pattern, weight, _ in self.pseudocode_medium_patterns:
            if re.search(pattern, text_lower, re.MULTILINE):
                score += weight
        return score

    def _calculate_strong_nl_score(self, text_lower: str) -> float:
        """Calculates score for strong natural language patterns."""
        score = 0.0
        for pattern, weight, _ in self.natural_language_strong_patterns:
            if re.search(pattern, text_lower, re.MULTILINE | re.IGNORECASE):
                score += weight
        return score

    def _calculate_medium_nl_score(self, text_lower: str) -> float:
        """Calculates score for medium natural language patterns."""
        score = 0.0
        for pattern, weight, _ in self.natural_language_medium_patterns:
            if re.search(pattern, text_lower, re.MULTILINE):
                score += weight
        return score

    def _calculate_anti_nl_score(self, text_lines: List[str]) -> float:
        """Calculates score for anti-natural-language patterns (indicates code)."""
        score = 0.0
        for pattern, weight, _ in self.code_anti_nl_patterns:
            for line in text_lines[:10]:
                if re.search(pattern, line.lower()):
                    score += weight
                    break
        return score

    def _adjust_for_explanatory_ratio(self, explanatory_ratio: float) -> float:
        """Adjusts score based on explanatory line ratio."""
        adjustment = 0.0
        if explanatory_ratio > EXPLANATORY_RATIO_HIGH:
            adjustment += WEIGHT_EXPLANATORY_HIGH
        if explanatory_ratio > EXPLANATORY_RATIO_DOMINANT:
            adjustment += WEIGHT_EXPLANATORY_VERY_HIGH
        return adjustment

    def _apply_decision_rules(
        self,
        text: str,
        text_lower: str,
        text_lines: List[str],
        explanatory_ratio: float,
        code_ratio: float,
        critical_score: float,
        critical_matches: List[str],
        pseudo_strong_score: float,
        nl_strong_score: float,
        pseudocode_total: float,
        natural_language_total: float,
        human_language_detected: bool,
    ) -> Tuple[str, float]:
        """Applies decision rules to determine input type."""

        has_begin = "begin keyword" in critical_matches
        has_end = "end keyword" in critical_matches
        has_assignment = "assignment operator" in critical_matches

        begin_count = len(re.findall(r"\bbegin\b", text_lower))
        end_count = len(re.findall(r"\bend\b", text_lower))
        assignment_count = len(re.findall(r"<-", text))

        has_dominant_structure = (
            begin_count >= 2 and end_count >= 2 and assignment_count >= 2
        )

        if (
            explanatory_ratio > EXPLANATORY_RATIO_EXTREMELY_HIGH
            and nl_strong_score >= NL_STRONG_SCORE_MEDIUM
        ):
            confidence = min(0.8 + (explanatory_ratio * 0.15), 0.98)
            return ("natural_language", confidence)

        if human_language_detected and nl_strong_score >= NL_STRONG_SCORE_HIGH:
            confidence = min(0.85 + (nl_strong_score / 20.0), 0.98)
            return ("natural_language", confidence)

        if (
            explanatory_ratio > EXPLANATORY_RATIO_MEDIUM
            and nl_strong_score >= NL_STRONG_SCORE_LOW
        ):
            confidence = min(0.75 + (explanatory_ratio * 0.2), 0.95)
            return ("natural_language", confidence)

        if has_dominant_structure and code_ratio > CODE_RATIO_THRESHOLD:
            confidence = min(0.7 + (critical_score / 15.0), 0.95)
            return ("pseudocode", confidence)

        if has_begin and has_end and has_assignment:
            if explanatory_ratio > EXPLANATORY_RATIO_MEDIUM:
                confidence = min(0.75 + (nl_strong_score / 15.0), 0.95)
                return ("natural_language", confidence)
            confidence = min(0.65 + (critical_score / 15.0), 0.95)
            return ("pseudocode", confidence)

        if (
            pseudo_strong_score >= PSEUDO_STRONG_SCORE_THRESHOLD
            and nl_strong_score < NL_STRONG_SCORE_MEDIUM
        ):
            if explanatory_ratio < EXPLANATORY_RATIO_LOW:
                confidence = min(0.6 + (pseudo_strong_score / 10.0), 0.92)
                return ("pseudocode", confidence)

        if nl_strong_score >= NL_STRONG_SCORE_VERY_HIGH:
            confidence = min(0.75 + (nl_strong_score / 15.0), 0.98)
            return ("natural_language", confidence)

        if human_language_detected and (
            nl_strong_score >= NL_STRONG_SCORE_LOW
            or explanatory_ratio > EXPLANATORY_RATIO_LOW
        ):
            confidence = min(0.8 + (nl_strong_score / 20.0), 0.95)
            return ("natural_language", confidence)

        if len(text) < SHORT_INPUT_LENGTH and re.search(
            r"\b(sort|create|implement|write|find|search|build|make|calculate|compute|process|handle|manage|check|validate)\b",
            text_lower,
        ):
            if pseudocode_total < PSEUDOCODE_TOTAL_THRESHOLD:
                return ("natural_language", 0.70)

        context_adjusted_nl = natural_language_total + (explanatory_ratio * 4.0)

        if pseudocode_total > context_adjusted_nl:
            ratio = pseudocode_total / (context_adjusted_nl + 1.0)
            confidence = min(0.5 + (ratio * 0.1), 0.88)
            return ("pseudocode", confidence)

        ratio = context_adjusted_nl / (pseudocode_total + 1.0)
        confidence = min(0.65 + (ratio * 0.12), 0.95)
        return ("natural_language", confidence)
