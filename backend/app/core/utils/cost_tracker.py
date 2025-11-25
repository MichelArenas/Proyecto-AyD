"""
Cost and Performance Tracker for Analysis Operations
This module provides classes and functions to track costs and performance metrics
associated with analysis operations, including LLM API calls, AST metrics, and timing breakdowns.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.constants import TOKEN_COSTS

logger = logging.getLogger(__name__)


@dataclass
class LLMCallMetrics:
    """Metrics for a single LLM API call."""

    provider: str
    model: str
    operation: str

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    latency_ms: float = 0.0
    cost_usd: float = 0.0

    timestamp: float = field(default_factory=time.time)


@dataclass
class AnalysisMetrics:
    """Comprehensive metrics for an entire analysis operation."""

    validation_time_us: float = 0.0
    parsing_time_us: float = 0.0
    ast_analysis_time_us: float = 0.0
    complexity_calculation_time_us: float = 0.0
    diagram_generation_time_us: float = 0.0
    total_time_us: float = 0.0

    llm_calls: List[LLMCallMetrics] = field(default_factory=list)
    total_llm_tokens: int = 0
    total_llm_cost_usd: float = 0.0
    total_llm_time_ms: float = 0.0

    ast_node_count: int = 0
    ast_depth: int = 0

    peak_memory_mb: float = 0.0


class CostTracker:
    """
    Tracks costs and performance metrics for analysis operations.
    """

    def __init__(self):
        self.current_analysis: Optional[AnalysisMetrics] = None
        self.operation_start_times: Dict[str, float] = {}

    def start_analysis(self):
        """Initialize a new analysis tracking session."""
        self.current_analysis = AnalysisMetrics()
        self.operation_start_times.clear()

    def start_operation(self, operation_name: str):
        """Start timing an operation."""
        self.operation_start_times[operation_name] = time.perf_counter()

    def end_operation(self, operation_name: str) -> float:
        """
        End timing an operation and record elapsed time.
        """
        if operation_name not in self.operation_start_times:
            logger.warning("Operation '%s' was not started", operation_name)
            return 0.0

        start_time = self.operation_start_times.pop(operation_name)
        elapsed_seconds = time.perf_counter() - start_time
        elapsed_microseconds = elapsed_seconds * 1_000_000

        if self.current_analysis:
            if operation_name == "validation":
                self.current_analysis.validation_time_us = elapsed_microseconds
            elif operation_name == "parsing":
                self.current_analysis.parsing_time_us = elapsed_microseconds
            elif operation_name == "ast_analysis":
                self.current_analysis.ast_analysis_time_us = elapsed_microseconds
            elif operation_name == "complexity_calculation":
                self.current_analysis.complexity_calculation_time_us = (
                    elapsed_microseconds
                )
            elif operation_name == "diagram_generation":
                self.current_analysis.diagram_generation_time_us = elapsed_microseconds

        return elapsed_microseconds

    def track_llm_call(
        self,
        provider: str,
        model: str,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
    ):
        """
        Track an LLM API call and its associated metrics.
        """
        if not self.current_analysis:
            logger.warning("No active analysis to track LLM call")
            return

        total_tokens = input_tokens + output_tokens
        cost_usd = self._calculate_llm_cost(
            provider, model, input_tokens, output_tokens
        )

        metrics = LLMCallMetrics(
            provider=provider,
            model=model,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
        )

        self.current_analysis.llm_calls.append(metrics)
        self.current_analysis.total_llm_tokens += total_tokens
        self.current_analysis.total_llm_cost_usd += cost_usd
        self.current_analysis.total_llm_time_ms += latency_ms

    def _calculate_llm_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """
        Calculate the cost of an LLM API call based on provider and model.
        """
        if provider not in TOKEN_COSTS:
            logger.warning("Unknown provider: %s", provider)
            return 0.0

        provider_costs = TOKEN_COSTS[provider]

        model_costs = None
        for known_model, costs in provider_costs.items():
            if known_model in model or model in known_model:
                model_costs = costs
                break

        if not model_costs:
            logger.warning("Unknown model: %s for provider %s", model, provider)
            return 0.0

        input_cost = (input_tokens / 1000) * model_costs["input"]
        output_cost = (output_tokens / 1000) * model_costs["output"]

        return input_cost + output_cost

    def set_ast_metrics(self, node_count: int, depth: int):
        """Set AST-related metrics."""
        if self.current_analysis:
            self.current_analysis.ast_node_count = node_count
            self.current_analysis.ast_depth = depth

    def finalize_analysis(self) -> AnalysisMetrics:
        """
        Finalize the analysis and return collected metrics.
        """
        if not self.current_analysis:
            raise ValueError("No active analysis to finalize")

        self.current_analysis.total_time_us = (
            self.current_analysis.validation_time_us
            + self.current_analysis.parsing_time_us
            + self.current_analysis.ast_analysis_time_us
            + self.current_analysis.complexity_calculation_time_us
            + self.current_analysis.diagram_generation_time_us
        )

        metrics = self.current_analysis
        self.current_analysis = None

        return metrics

    def get_metrics_summary(self, metrics: AnalysisMetrics) -> Dict[str, Any]:
        """
        Generate a summary of the collected metrics.
        """
        return {
            "timing": {
                "total_us": metrics.total_time_us,
                "total_ms": metrics.total_time_us / 1000,
                "total_seconds": metrics.total_time_us / 1_000_000,
                "breakdown": {
                    "validation_us": metrics.validation_time_us,
                    "parsing_us": metrics.parsing_time_us,
                    "ast_analysis_us": metrics.ast_analysis_time_us,
                    "complexity_calculation_us": metrics.complexity_calculation_time_us,
                    "diagram_generation_us": metrics.diagram_generation_time_us,
                },
                "breakdown_percentage": {
                    "validation": self._percentage(
                        metrics.validation_time_us, metrics.total_time_us
                    ),
                    "parsing": self._percentage(
                        metrics.parsing_time_us, metrics.total_time_us
                    ),
                    "ast_analysis": self._percentage(
                        metrics.ast_analysis_time_us, metrics.total_time_us
                    ),
                    "complexity_calculation": self._percentage(
                        metrics.complexity_calculation_time_us, metrics.total_time_us
                    ),
                    "diagram_generation": self._percentage(
                        metrics.diagram_generation_time_us, metrics.total_time_us
                    ),
                },
            },
            "llm": {
                "total_calls": len(metrics.llm_calls),
                "total_tokens": metrics.total_llm_tokens,
                "total_cost_usd": round(metrics.total_llm_cost_usd, 6),
                "total_time_ms": metrics.total_llm_time_ms,
                "calls_breakdown": [
                    {
                        "operation": call.operation,
                        "provider": call.provider,
                        "model": call.model,
                        "tokens": call.total_tokens,
                        "cost_usd": round(call.cost_usd, 6),
                        "latency_ms": call.latency_ms,
                    }
                    for call in metrics.llm_calls
                ],
            },
            "ast": {
                "node_count": metrics.ast_node_count,
                "depth": metrics.ast_depth,
            },
            "cost_summary": {
                "total_usd": round(metrics.total_llm_cost_usd, 6),
                "cost_per_token_usd": (
                    round(metrics.total_llm_cost_usd / metrics.total_llm_tokens, 8)
                    if metrics.total_llm_tokens > 0
                    else 0.0
                ),
            },
        }

    def _percentage(self, part: float, total: float) -> float:
        """Calculate percentage."""
        if total == 0:
            return 0.0
        return round((part / total) * 100, 2)
