"""
Module for comparing structured system analysis with LLM-based complexity analysis.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

from app.core.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMComparator:
    """
    Compare structured system analysis with LLM-based complexity analysis.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    def analyze_with_llm(self, pseudocode: str) -> Dict[str, Any]:
        """
        Use LLM to analyze the complexity of the given pseudocode.
        """
        prompt = f"""You are an expert algorithm analyst. Always respond with valid JSON.
        Analyze the time and space complexity of the following algorithm.

        Pseudocode:
        {pseudocode}

        Provide a detailed analysis including:
        1. Best Case Time Complexity: Notation and explanation
        2. Average Case Time Complexity: Notation and explanation  
        3. Worst Case Time Complexity: Notation and explanation
        4. Space Complexity: Notation and explanation
        5. Algorithm Pattern: (e.g., divide-and-conquer, dynamic programming, greedy, etc.)
        6. Reasoning: Step-by-step explanation of how you determined the complexity

        Format your response as JSON with these exact keys:
        {{
            "best_case": "O(...)",
            "average_case": "O(...)",
            "worst_case": "O(...)",
            "space_complexity": "O(...)",
            "pattern": "pattern_name",
            "reasoning": "detailed explanation",
            "confidence": 0.0-1.0
        }}"""

        content = ""
        try:
            if not self.llm_client.translator:
                raise ValueError("LLM client is not initialized")

            response = self.llm_client.translator.call_llm(prompt)
            content = response.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(content)

            return {
                "status": "success",
                "analysis": analysis,
                "provider": self.llm_client.provider,
            }

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response: %s", e)
            return {
                "status": "parse_error",
                "error": str(e),
                "raw_response": content if "content" in locals() else None,
            }
        except Exception as e:
            logger.error("LLM analysis failed: %s", e)
            return {
                "status": "error",
                "error": str(e),
            }

    def compare_analyses(
        self, system_analysis: Dict[str, Any], llm_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare system analysis with LLM analysis and identify concordances and divergences.
        """
        comparison = {
            "concordance": {},
            "divergences": [],
            "system_analysis": system_analysis,
            "llm_analysis": llm_analysis,
            "overall_agreement": 0.0,
        }

        system_worst = self._normalize_complexity(
            system_analysis.get("time_complexity", {})
            .get("worst_case", {})
            .get("big_o", "unknown")
        )
        llm_worst = self._normalize_complexity(
            llm_analysis.get("analysis", {}).get("worst_case", "unknown")
        )

        system_space = self._normalize_complexity(
            system_analysis.get("space_complexity", "unknown")
        )
        llm_space = self._normalize_complexity(
            llm_analysis.get("analysis", {}).get("space_complexity", "unknown")
        )

        if system_worst == llm_worst:
            comparison["concordance"]["worst_case_time"] = {
                "agree": True,
                "value": system_worst,
            }
        else:
            comparison["concordance"]["worst_case_time"] = {
                "agree": False,
                "system": system_worst,
                "llm": llm_worst,
            }
            comparison["divergences"].append(
                {
                    "category": "worst_case_time",
                    "system_value": system_worst,
                    "llm_value": llm_worst,
                    "severity": self._calculate_divergence_severity(
                        system_worst, llm_worst
                    ),
                }
            )

        if system_space == llm_space:
            comparison["concordance"]["space_complexity"] = {
                "agree": True,
                "value": system_space,
            }
        else:
            comparison["concordance"]["space_complexity"] = {
                "agree": False,
                "system": system_space,
                "llm": llm_space,
            }
            comparison["divergences"].append(
                {
                    "category": "space_complexity",
                    "system_value": system_space,
                    "llm_value": llm_space,
                    "severity": self._calculate_divergence_severity(
                        system_space, llm_space
                    ),
                }
            )

        agreements = sum(
            1 for v in comparison["concordance"].values() if v.get("agree", False)
        )
        total_checks = len(comparison["concordance"])
        comparison["overall_agreement"] = (
            agreements / total_checks if total_checks > 0 else 0.0
        )

        if comparison["divergences"]:
            comparison["divergence_analysis"] = self._analyze_divergences(
                comparison["divergences"],
                system_analysis,
                llm_analysis,
            )

        return comparison

    def _normalize_complexity(self, complexity_str: str) -> str:
        """
        Normalize complexity notation for comparison.
        """
        if not complexity_str or complexity_str == "unknown":
            return "unknown"

        normalized = re.sub(r"^[OoΩΘ]\(?\s*", "", str(complexity_str))
        normalized = normalized.strip().lower()
        if normalized.endswith(")") and not normalized.endswith("))"):
            normalized = normalized[:-1]

        normalized = re.sub(r"log\s*\(?\s*n\s*\)?", "log(n)", normalized)
        normalized = re.sub(r"lg\s*n", "log(n)", normalized)

        normalized = re.sub(r"\s+", " ", normalized)
        if "log(n" in normalized and not normalized.endswith("))"):
            normalized = f"{normalized})"

        return normalized

    def _calculate_divergence_severity(self, complexity1: str, complexity2: str) -> str:
        """
        Calculate the severity of divergence between two complexity notations.
        """
        if complexity1 == "unknown" or complexity2 == "unknown":
            return "unknown"

        order = ["1", "log(n)", "n", "n log(n)", "n^2", "n^3", "2^n", "n!"]

        try:
            idx1 = next((i for i, o in enumerate(order) if complexity1 == o), -1)
            if idx1 == -1:
                idx1 = next((i for i, o in enumerate(order) if o in complexity1), -1)
            idx2 = next((i for i, o in enumerate(order) if complexity2 == o), -1)
            if idx2 == -1:
                idx2 = next((i for i, o in enumerate(order) if o in complexity2), -1)

            if idx1 == -1 or idx2 == -1:
                return "medium"

            diff = abs(idx1 - idx2)

            if diff == 0:
                return "low"
            if diff <= 1:
                return "medium"
            return "high"
        except Exception:
            return "medium"

    def _analyze_divergences(
        self, divergences: list, system_analysis: Dict, llm_analysis: Dict
    ) -> Dict[str, Any]:
        """
        Analyze the divergences and provide possible causes and recommendations.
        """
        analysis = {
            "possible_causes": [],
            "recommendations": [],
        }

        for div in divergences:
            if div["severity"] == "high":
                analysis["possible_causes"].append(
                    {
                        "category": div["category"],
                        "description": f"Major difference: {div['system_value']} vs {div['llm_value']}",
                        "likely_reason": "Different interpretation of loop bounds or recursion depth",
                    }
                )
                analysis["recommendations"].append(
                    {
                        "action": "manual_review",
                        "details": f"Review {div['category']} calculation manually",
                    }
                )

        system_pattern = system_analysis.get("analysis", {}).get("algorithmic_pattern")
        if system_pattern:
            analysis["possible_causes"].append(
                {
                    "category": "pattern_detection",
                    "description": f"System detected pattern: {system_pattern}",
                    "likely_reason": "Structured pattern matching vs free-form reasoning",
                }
            )

        return analysis

    def generate_comparison_report(
        self,
        pseudocode: str,
        system_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a comparison report between system analysis and LLM analysis.
        """
        logger.info("Generating LLM comparison report...")

        llm_result = self.analyze_with_llm(pseudocode)

        if llm_result["status"] != "success":
            return {
                "status": "error",
                "error": "LLM analysis failed",
                "details": llm_result,
            }

        comparison = self.compare_analyses(system_analysis, llm_result)

        report = {
            "status": "success",
            "comparison": comparison,
            "summary": {
                "overall_agreement": f"{comparison['overall_agreement'] * 100:.1f}%",
                "divergence_count": len(comparison["divergences"]),
                "high_severity_divergences": sum(
                    1 for d in comparison["divergences"] if d["severity"] == "high"
                ),
                "recommendation": self._generate_recommendation(comparison),
            },
        }

        logger.info(
            "Comparison complete: %s agreement",
            report["summary"]["overall_agreement"],
        )

        return report

    def _generate_recommendation(self, comparison: Dict[str, Any]) -> str:
        """
        Generate recommendation based on comparison results.
        """
        agreement = comparison["overall_agreement"]
        high_severity = sum(
            1 for d in comparison["divergences"] if d["severity"] == "high"
        )

        if agreement >= 0.9:
            return "High concordance. System analysis is reliable."
        if agreement >= 0.7:
            return "Good concordance. Minor differences detected, review if critical."
        if high_severity > 0:
            return "Significant divergences detected. Manual review recommended."
        return "Low concordance. Thoroughly review both analyses."
