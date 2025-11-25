"""Dataset generation utilities for ML classifier training."""

import csv
import hashlib
import json
import logging
import random
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from itertools import cycle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.constants import ALGORITHM_PATTERNS, PATTERN_LABELS
from app.core.language import LanguageParser
from app.core.llm import LLMClient
from app.core.services import LLMComparator, SecurityService

logger = logging.getLogger(__name__)


class DatasetGenerator:
    """Generates curated pseudocode datasets with validation and metadata."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        parser: Optional[LanguageParser] = None,
    ):
        self.llm_client = llm_client or LLMClient()
        self.language_parser = parser or LanguageParser()
        self.security_service = SecurityService()
        self.llm_comparator: Optional[LLMComparator] = None
        self.generated_examples: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}

    def count_patterns(self, patterns: Optional[List[str]] = None) -> int:
        """Return how many patterns will be used for generation."""
        if patterns is not None:
            return len(patterns)
        return len(ALGORITHM_PATTERNS)

    def generate_pseudocode_example(
        self, pattern: str, algorithm_name: str, complexity: str
    ) -> Optional[Dict[str, Any]]:
        """Generate a single pseudocode example using the configured LLM."""
        prompt = f"""Generate clean, well-structured pseudocode for the {algorithm_name} algorithm.
                    Pattern family: {pattern.replace('_', ' ')}
                    Target Time Complexity: {complexity}

                    Constraints:
                    1. Follow the documented grammar (begin/end blocks, CALL for user subroutines, etc.).
                    2. Declare loop counters/locals with "var" before use.
                    3. Keep between 15 and 40 lines, include minimal inline comments.
                    4. Return ONLY pseudocode (no markdown fences, no explanations)."""

        try:
            if not self.llm_client.translator:
                logger.warning(
                    "Provider %s not supported for generation", self.llm_client.provider
                )
                return None

            response = self.llm_client.translator.call_llm(prompt).strip()
            pseudocode = (
                response.replace("```pseudocode", "").replace("```", "").strip()
            )

            if not pseudocode:
                return None

            return {
                "algorithm_name": algorithm_name,
                "requested_pattern": pattern,
                "time_complexity": complexity,
                "pseudocode": pseudocode,
                "characteristics": ALGORITHM_PATTERNS[pattern]["characteristics"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "provider": self.llm_client.provider,
            }

        except Exception as exc:
            logger.error("Error generating example for %s: %s", algorithm_name, exc)
            return None

    def generate_dataset(
        self,
        target_size: int = 5000,
        patterns: Optional[List[str]] = None,
        allow_variations: bool = True,
        variations_per_example: int = 1,
        max_attempts: Optional[int] = None,
        enable_llm_verification: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Generate a validated dataset until the requested target size is reached."""
        run_id = f"dataset::{uuid.uuid4()}"
        self._audit_dataset_event(
            run_id,
            "dataset_generation.started",
            {
                "target_size": target_size,
                "patterns": patterns,
                "allow_variations": allow_variations,
                "variations_per_example": variations_per_example,
                "enable_llm_verification": enable_llm_verification,
            },
        )
        patterns = patterns or list(ALGORITHM_PATTERNS.keys())
        attempt_limit = max_attempts or target_size * 6
        dataset: List[Dict[str, Any]] = []
        stats = defaultdict(int)
        stats.update(
            {
                "target_size": target_size,
                "patterns": patterns,
                "attempt_limit": attempt_limit,
                "pattern_distribution": defaultdict(int),
                "start_time": datetime.utcnow().isoformat(),
            }
        )

        logger.info(
            "Starting dataset generation to reach %d validated examples (patterns=%s)",
            target_size,
            patterns,
        )

        pattern_cycle = cycle(patterns)
        attempts = 0

        while len(dataset) < target_size and attempts < attempt_limit:
            attempts += 1
            stats["attempts"] = attempts
            current_pattern = next(pattern_cycle)
            choice_map = ALGORITHM_PATTERNS[current_pattern]
            algorithm_name = random.choice(choice_map["examples"])
            complexity = random.choice(choice_map["time_complexity"])

            example = self.generate_pseudocode_example(
                current_pattern, algorithm_name, complexity
            )

            if not example:
                stats["llm_failures"] += 1
                continue

            enriched = self._validate_and_enrich_example(
                example, enable_llm_verification, stats
            )

            if not enriched:
                continue

            dataset.append(enriched)
            stats["accepted"] += 1
            stats["pattern_distribution"][enriched["pattern"]] += 1

            if allow_variations and len(dataset) < target_size:
                variations = self.add_noise_variations(
                    [enriched],
                    variations_per_example=variations_per_example,
                    enable_llm_verification=enable_llm_verification,
                    target_remaining=target_size - len(dataset),
                    stats=stats,
                )
                for variation in variations:
                    if len(dataset) >= target_size:
                        break
                    dataset.append(variation)
                    stats["accepted"] += 1
                    stats["variation_examples"] += 1
                    stats["pattern_distribution"][variation["pattern"]] += 1

        stats["completed_at"] = datetime.utcnow().isoformat()
        stats["achieved_size"] = len(dataset)
        stats["exhausted_attempts"] = attempts >= attempt_limit
        stats["pattern_distribution"] = dict(stats["pattern_distribution"])
        stats = dict(stats)

        self.generated_examples = dataset
        self.stats = stats

        logger.info(
            "Dataset generation finished with %d validated examples (attempts=%d)",
            len(dataset),
            attempts,
        )

        self._audit_dataset_event(
            run_id,
            "dataset_generation.completed",
            {
                "stats": stats,
                "achieved_size": len(dataset),
                "attempts": attempts,
                "exhausted_attempts": stats.get("exhausted_attempts"),
            },
        )

        return dataset, stats

    def add_noise_variations(
        self,
        dataset: List[Dict[str, Any]],
        variations_per_example: int = 1,
        enable_llm_verification: bool = False,
        target_remaining: Optional[int] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create lightly-perturbed copies that still pass validation."""
        if variations_per_example <= 0:
            return []

        generated: List[Dict[str, Any]] = []
        remaining = target_remaining or (len(dataset) * variations_per_example)

        for example in dataset:
            if remaining <= 0:
                break
            for variation_index in range(variations_per_example):
                if remaining <= 0:
                    break

                variation_prompt = f"""Rewrite the following pseudocode while preserving its logic and complexity class.
Focus on {"variable renaming" if variation_index % 2 == 0 else "minor control-flow reordering"}.
Keep the same grammar rules and constraints.

{example['pseudocode']}"""

                try:
                    if not self.llm_client.translator:
                        logger.warning("Cannot create variations without translator")
                        return generated

                    response = self.llm_client.translator.call_llm(
                        variation_prompt
                    ).strip()
                    varied_code = (
                        response.replace("```pseudocode", "").replace("```", "").strip()
                    )

                    if not varied_code:
                        continue

                    variation = example.copy()
                    variation.update(
                        {
                            "pseudocode": varied_code,
                            "is_variation": True,
                            "variation_source": example.get("algorithm_name"),
                            "generated_at": datetime.utcnow().isoformat(),
                        }
                    )

                    enriched = self._validate_and_enrich_example(
                        variation,
                        enable_llm_verification,
                        stats if stats is not None else self.stats,
                    )
                    if enriched:
                        generated.append(enriched)
                        remaining -= 1

                except Exception as exc:
                    logger.warning("Failed to create variation: %s", exc)

        return generated

    def extract_features(
        self, pseudocode: str, program_ast: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Extract textual and structural features from pseudocode."""
        features: Dict[str, Any] = {}
        lines = [line for line in pseudocode.split("\n") if line.strip()]
        features["line_count"] = len(lines)
        features["has_recursion"] = self._detect_recursion(pseudocode)
        features["loop_count"] = len(re.findall(r"\b(for|while|repeat)\b", pseudocode))
        features["conditional_count"] = len(re.findall(r"\bif\b", pseudocode))
        features["has_memoization"] = bool(
            re.search(r"\b(memo|cache|dp)\b", pseudocode, re.IGNORECASE)
        )
        features["has_array"] = bool(re.search(r"\[[^\]]+\]", pseudocode))
        features["has_graph"] = bool(
            re.search(r"\b(graph|node|edge|vertex)\b", pseudocode, re.IGNORECASE)
        )
        features["assignment_count"] = len(re.findall(r"<-", pseudocode))
        features["return_count"] = len(re.findall(r"\breturn\b", pseudocode))
        features["function_count"] = len(
            re.findall(r"\bcall\s+", pseudocode, re.IGNORECASE)
        )
        features["call_count"] = len(
            re.findall(r"\bcall\s+[A-Za-z_][A-Za-z0-9_]*", pseudocode, re.IGNORECASE)
        )
        features["self_call_count"] = len(
            re.findall(r"\bcall\s+(\w+)\s*\(\s*n", pseudocode, re.IGNORECASE)
        )
        features["nested_loop_depth"] = self._estimate_nested_loops(pseudocode)
        features["max_recursion_depth"] = features["self_call_count"]
        features["loop_type_for"] = len(re.findall(r"\bfor\b", pseudocode))
        features["loop_type_while"] = len(re.findall(r"\bwhile\b", pseudocode))
        features["loop_type_repeat"] = len(re.findall(r"\brepeat\b", pseudocode))
        features["recurrence_terms"] = bool(
            re.search(r"T\s*\(\s*n\s*(/|-)\s*", pseudocode)
        )
        features["pattern_hints"] = self._detect_pattern_hints(pseudocode)

        if program_ast:
            features.update(self._extract_ast_features(program_ast))

        return features

    def export_to_json(
        self,
        dataset: List[Dict[str, Any]],
        output_path: str = "dataset_algorithms.json",
    ) -> str:
        """Persist dataset in JSON format."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as handle:
            json.dump(dataset, handle, indent=2, ensure_ascii=False)

        logger.info("Dataset exported to %s (%d examples)", output_file, len(dataset))
        return str(output_file)

    def export_to_csv(
        self, dataset: List[Dict[str, Any]], output_path: str = "dataset_algorithms.csv"
    ) -> str:
        """
        Export dataset to CSV format.
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", newline="", encoding="utf-8") as handle:
            if not dataset:
                return str(output_file)

            flattened_rows = [self._flatten_example(example) for example in dataset]
            fieldnames = sorted(flattened_rows[0].keys())
            writer = csv.DictWriter(handle, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(flattened_rows)

        logger.info(
            "Dataset exported to %s (CSV format, %d examples)",
            output_file,
            len(dataset),
        )
        return str(output_file)

    def generate_and_export(
        self,
        target_size: int = 5000,
        allow_variations: bool = True,
        variations_per_example: int = 1,
        output_dir: str = "data/ml_datasets",
        enable_llm_verification: bool = False,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Full pipeline: build dataset then persist to disk."""
        dataset, stats = self.generate_dataset(
            target_size=target_size,
            allow_variations=allow_variations,
            variations_per_example=variations_per_example,
            enable_llm_verification=enable_llm_verification,
        )

        json_path = self.export_to_json(
            dataset, output_path=f"{output_dir}/algorithms_dataset.json"
        )
        csv_path = self.export_to_csv(
            dataset, output_path=f"{output_dir}/algorithms_dataset.csv"
        )

        return json_path, csv_path, stats

    def _audit_dataset_event(
        self, run_id: str, event_type: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        if not details:
            details = {}
        payload = {"run_id": run_id, **details}
        try:
            self.security_service.record_policy_event(
                job_id=run_id,
                event_type=event_type,
                actor="dataset_generator",
                details=payload,
            )
        except Exception as exc:
            logger.debug("Dataset audit logging failed for %s: %s", run_id, exc)

    def _validate_and_enrich_example(
        self,
        example: Dict[str, Any],
        enable_llm_verification: bool,
        stats: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Parse, label, and annotate an example. Returns None if invalid."""
        shared_stats = stats if stats is not None else self.stats
        if not shared_stats:
            shared_stats = defaultdict(int)
        pseudocode = example.get("pseudocode", "").strip()
        if not pseudocode:
            shared_stats["empty_examples"] += 1
            return None

        try:
            ast_program = self.language_parser.parse(pseudocode)
        except Exception as exc:
            logger.debug("Parser rejected example: %s", exc)
            shared_stats["parser_failures"] += 1
            return None

        features = self.extract_features(pseudocode, program_ast=ast_program)
        pattern = self._infer_pattern(pseudocode, example["requested_pattern"])
        llm_verification = None

        if enable_llm_verification:
            llm_verification = self._verify_with_llm(pseudocode, pattern)
            if llm_verification.get("status") == "divergent":
                shared_stats["llm_disagreements"] += 1

        enriched = {
            **example,
            "pattern": pattern,
            "features": features,
            "ast_fingerprint": hashlib.sha256(pseudocode.encode("utf-8")).hexdigest(),
            "validation": {
                "passed": True,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "llm_verification": llm_verification,
        }

        return enriched

    def _verify_with_llm(self, pseudocode: str, pattern: str) -> Dict[str, Any]:
        """Optional LLM-based cross-check of the inferred pattern."""
        if self.llm_comparator is None:
            self.llm_comparator = LLMComparator()

        try:
            analysis = self.llm_comparator.analyze_with_llm(pseudocode)
            if analysis.get("status") != "success":
                return {"status": "error", "details": analysis}

            llm_pattern = analysis["analysis"].get("pattern", "unknown")
            status = "match" if llm_pattern == pattern else "divergent"
            return {
                "status": status,
                "llm_pattern": llm_pattern,
                "provider": analysis.get("provider"),
            }
        except Exception as exc:
            logger.warning("LLM verification failed: %s", exc)
            return {"status": "error", "details": str(exc)}

    def _flatten_example(self, example: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested dictionaries for CSV export."""
        flattened = {
            k: v
            for k, v in example.items()
            if k not in {"features", "validation", "llm_verification"}
        }

        for prefix, section in (
            ("feature", example.get("features", {})),
            ("validation", example.get("validation", {})),
        ):
            for key, value in section.items():
                flattened[f"{prefix}_{key}"] = value

        llm_section = example.get("llm_verification") or {}
        for key, value in llm_section.items():
            flattened[f"llm_{key}"] = value

        return flattened

    def _estimate_nested_loops(self, pseudocode: str) -> int:
        depth = 0
        max_depth = 0
        for line in pseudocode.splitlines():
            if re.search(r"\b(for|while|repeat)\b", line):
                depth += 1
                max_depth = max(max_depth, depth)
            if line.strip().lower() == "end":
                depth = max(0, depth - 1)
        return max_depth

    def _detect_pattern_hints(self, pseudocode: str) -> List[str]:
        hints = []
        lowered = pseudocode.lower()
        if "memo" in lowered or "cache" in lowered:
            hints.append("dynamic_programming")
        if "pivot" in lowered or "partition" in lowered:
            hints.append("divide_and_conquer")
        if "queue" in lowered or "neighbors" in lowered:
            hints.append("graph_algorithms")
        if "while" in lowered and "i <- i * 2" in lowered:
            hints.append("logarithmic")
        if "return" in lowered and "call" in lowered:
            hints.append("recursive")
        return hints

    def _extract_ast_features(self, program_ast: Any) -> Dict[str, Any]:
        features = {
            "ast_total_nodes": 0,
            "ast_loop_nodes": 0,
            "ast_condition_nodes": 0,
        }

        def _walk(node):
            if not hasattr(node, "__dict__"):
                return
            features["ast_total_nodes"] += 1
            node_type = type(node).__name__.lower()
            if "loop" in node_type:
                features["ast_loop_nodes"] += 1
            if "if" in node_type or "condition" in node_type:
                features["ast_condition_nodes"] += 1

            for value in node.__dict__.values():
                if isinstance(value, list):
                    for item in value:
                        _walk(item)
                elif hasattr(value, "__dict__"):
                    _walk(value)

        for statement in getattr(program_ast, "statements", []):
            _walk(statement)

        return features

    def _infer_pattern(self, pseudocode: str, requested_pattern: str) -> str:
        lowered = pseudocode.lower()
        heuristics = [
            ("dynamic_programming", ["memo", "cache", "table", "dp"]),
            ("divide_and_conquer", ["pivot", "partition", "divide", "merge"]),
            ("greedy", ["greedy", "priority", "best"]),
            ("graph_algorithms", ["graph", "edge", "vertex", "neighbor", "queue"]),
            ("backtracking", ["backtrack", "n_queens", "sudoku", "constraint"]),
            ("brute_force", ["linear", "bubble", "selection", "scan"]),
            ("sorting", ["sort", "merge", "heap", "counting"]),
        ]

        for label, keywords in heuristics:
            if any(keyword in lowered for keyword in keywords):
                return label

        return (
            requested_pattern
            if requested_pattern in PATTERN_LABELS
            else PATTERN_LABELS[0]
        )

    def _detect_recursion(self, pseudocode: str) -> bool:
        lowered = pseudocode.lower()
        if re.search(r"\bcall\s+[a-z_][a-z0-9_]*", lowered):
            return True
        header = re.search(r"^\s*([a-z_][a-z0-9_]*)\s*\(", lowered, re.MULTILINE)
        if not header:
            return False
        func_name = header.group(1)
        occurrences = re.findall(rf"\b{re.escape(func_name)}\s*\(", lowered)
        return len(occurrences) > 1
