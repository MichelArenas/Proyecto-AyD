"""
Service to run the full analysis pipeline: translation, parsing,
validation, complexity analysis, and artifact management.
"""

import logging
from typing import Any, Dict, Optional

from app.core.analysis import ComplexityCalculator
from app.core.analysis.techniques import (LoopBoundsAnalyzer,
                                          PatternHeuristics,
                                          SymbolicComplexitySolver)
from app.core.constants import (ERROR_TRANSLATION_FAILED, LLM_MODELS,
                                STATUS_COMPLETED, STATUS_FAILED,
                                STATUS_VALIDATION_FAILED)
from app.core.language import LanguageParser
from app.core.llm import LLMClient
from app.core.services.translation_service import TranslationService
from app.core.services.validation_service import ValidationService
from app.core.utils import ArtifactManager, CostTracker, InputSanitizer

logger = logging.getLogger(__name__)


class AnalysisPipelineService:
    """Service to run the full analysis pipeline."""

    def __init__(
        self,
        translation_service: Optional[TranslationService] = None,
        validation_service: Optional[ValidationService] = None,
        calculator: Optional[ComplexityCalculator] = None,
    ):
        self.translation_service = translation_service or TranslationService()
        self.validation_service = validation_service or ValidationService()
        self.parser = LanguageParser()
        self.calculator = calculator or ComplexityCalculator()
        self.loop_bounds = LoopBoundsAnalyzer()
        self.symbolic_solver = SymbolicComplexitySolver()
        self.cost_tracker = CostTracker()
        self.artifacts = ArtifactManager()
        self.patterns = PatternHeuristics()
        self.input_sanitizer = InputSanitizer()
        self.llm_client = LLMClient()

    def run_pipeline(
        self,
        raw_text: str,
        declared_input_type: str = "auto",
        request_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        validate_before_analysis: bool = True,
        skip_translation: bool = False,
        enable_llm_insights: bool = False,
    ) -> Dict[str, Any]:
        """Execute the NL → AST → complexity pipeline."""

        effective_options = self._normalize_options(options)
        self.cost_tracker.start_analysis()

        try:
            translation_payload = (
                self._build_direct_translation(raw_text)
                if skip_translation
                else self.translation_service.process_input(
                    input_text=raw_text,
                    validate=False,
                    save_to_db=False,
                    use_cache=True,
                    declared_input_type=declared_input_type,
                )
            )
        except ValueError as exc:
            self.cost_tracker.finalize_analysis()
            return {
                "status": STATUS_FAILED,
                "error": str(exc),
                "error_type": ERROR_TRANSLATION_FAILED,
            }

        if translation_payload.get("error"):
            self.cost_tracker.finalize_analysis()
            return {
                "status": "translation_failed",
                "error": translation_payload.get("error"),
                "error_type": translation_payload.get("error_type"),
                "translation": translation_payload,
                "pseudocode": translation_payload.get("pseudocode", raw_text),
            }

        pseudocode = translation_payload.get("pseudocode", "").strip()
        if not pseudocode:
            self.cost_tracker.finalize_analysis()
            return {
                "status": STATUS_FAILED,
                "error": "Translation produced empty pseudocode",
                "translation": translation_payload,
            }

        parse_result = self._parse_with_optional_fix(
            pseudocode,
            translation_payload,
            auto_fix=effective_options["auto_fix_syntax"],
            skip_translation=skip_translation,
        )
        if parse_result.get("status") != STATUS_COMPLETED:
            self.cost_tracker.finalize_analysis()
            return {
                **parse_result,
                "translation": translation_payload,
            }

        ast = parse_result["ast"]
        pseudocode = parse_result["pseudocode"]
        ast_meta = self.artifacts.persist_ast(ast, pseudocode)
        ast_stats = self._compute_ast_metrics(ast)
        self.cost_tracker.set_ast_metrics(
            ast_stats["node_count"], ast_stats["max_depth"]
        )

        validation_payload = None
        if validate_before_analysis:
            self.cost_tracker.start_operation("validation")
            validation_payload = self.validation_service.validate_pseudocode(
                pseudocode, save_to_db=False
            )
            self.cost_tracker.end_operation("validation")
            if not validation_payload.get("is_valid", False):
                metrics = self._finalize_metrics()
                return {
                    "status": STATUS_VALIDATION_FAILED,
                    "error": "Pseudocode validation failed",
                    "validation": validation_payload,
                    "translation": translation_payload,
                    "pseudocode": pseudocode,
                    "artifacts": {
                        "ast_digest": ast_meta["digest"],
                        "ast_path": ast_meta["path"],
                    },
                    "metrics": metrics,
                }

        self.cost_tracker.start_operation("complexity_calculation")
        try:
            loop_analysis = self.loop_bounds.analyze(ast)
            complexity_result = self.calculator.analyze(ast)
        except Exception as exc:
            self.cost_tracker.end_operation("complexity_calculation")
            metrics = self._finalize_metrics()
            return {
                "status": STATUS_FAILED,
                "error": str(exc),
                "error_type": "analysis_error",
                "translation": translation_payload,
                "pseudocode": pseudocode,
                "metrics": metrics,
            }
        self.cost_tracker.end_operation("complexity_calculation")

        analysis_payload = self._format_complexity(complexity_result)
        analysis_payload["loop_analysis"] = loop_analysis
        analysis_payload["symbolic_solver"] = self.symbolic_solver.solve_loops(
            loop_analysis.get("loops", [])
        )

        pattern_hint = self.patterns.detect_pattern(
            complexity_result.algorithm_name or "main",
            ast,
            complexity_result.algorithm_type,
        )
        if pattern_hint:
            analysis_payload["pattern_heuristic"] = pattern_hint
            optimization = self.patterns.suggest_optimization(pattern_hint["pattern"])
            if optimization:
                analysis_payload["optimization_hint"] = optimization

        if enable_llm_insights and self.llm_client:
            insights = self._generate_llm_insights(pseudocode, complexity_result)
            if insights:
                analysis_payload["llm_insights"] = insights

        self._track_translation_cost(raw_text, translation_payload)

        recursion_tree_path = self._maybe_render_recursion_tree(
            pseudocode, effective_options["resolve_graphics"]
        )

        metrics = self._finalize_metrics()

        result = {
            "status": STATUS_COMPLETED,
            "input_type": translation_payload.get("input_type", "pseudocode"),
            "pseudocode": pseudocode,
            "translation": translation_payload,
            "validation": validation_payload,
            "analysis": analysis_payload,
            "artifacts": {
                "ast_digest": ast_meta["digest"],
                "ast_path": ast_meta["path"],
                "recursion_tree_svg": recursion_tree_path,
            },
            "metrics": metrics,
            "options": effective_options,
            "request_id": request_id,
        }

        return result

    def _build_direct_translation(self, raw_text: str) -> Dict[str, Any]:
        report = self.input_sanitizer.sanitize(raw_text)
        return {
            "input_type": "pseudocode",
            "confidence": 1.0,
            "pseudocode": report.text,
            "translated": False,
            "provider": None,
            "cached": False,
            "sanitization": report.to_dict(),
        }

    def _parse_with_optional_fix(
        self,
        pseudocode: str,
        translation_payload: Dict[str, Any],
        auto_fix: bool,
        skip_translation: bool,
    ) -> Dict[str, Any]:
        try:
            self.cost_tracker.start_operation("parsing")
            ast = self.parser.parse(pseudocode)
            self.cost_tracker.end_operation("parsing")
            return {"status": STATUS_COMPLETED, "ast": ast, "pseudocode": pseudocode}
        except Exception as exc:
            self.cost_tracker.end_operation("parsing")
            if not auto_fix:
                return {"status": "parse_error", "error": str(exc)}
            if skip_translation:
                return {"status": "parse_error", "error": str(exc)}
            try:
                fix_payload = self.translation_service.auto_fix_pseudocode(
                    pseudocode, str(exc)
                )
                translation_payload["auto_fix"] = fix_payload
                fixed = fix_payload["pseudocode"]
                self.cost_tracker.start_operation("parsing")
                ast = self.parser.parse(fixed)
                self.cost_tracker.end_operation("parsing")
                self._track_fix_cost(
                    old_code=pseudocode,
                    new_code=fixed,
                    provider=fix_payload.get("provider"),
                )
                return {"status": STATUS_COMPLETED, "ast": ast, "pseudocode": fixed}
            except Exception as fix_exc:
                logger.warning("Auto-fix failed: %s", fix_exc)
                return {"status": "parse_error", "error": str(exc)}

    def _format_complexity(self, result) -> Dict[str, Any]:
        def build_case(case):
            return {
                "big_o": str(case.big_o),
                "omega": str(case.omega),
                "theta": str(case.theta) if case.theta else None,
                "explanation": case.explanation,
                "evidence": case.evidence,
                "recurrence": case.recurrence_relation,
            }

        payload = {
            "algorithm_name": result.algorithm_name,
            "algorithm_type": result.algorithm_type,
            "time_complexity": {
                "best_case": build_case(result.best_case),
                "average_case": build_case(result.average_case),
                "worst_case": build_case(result.worst_case),
            },
            "space_complexity": str(result.space_complexity),
            "explanation": result.detailed_explanation,
            "step_by_step_analysis": result.step_by_step_analysis,
            "loop_structure": result.loop_structure,
            "dominant_operations": result.dominant_operations,
        }

        if result.algorithmic_pattern:
            payload["pattern"] = result.algorithmic_pattern
        return payload

    def _normalize_options(self, options: Optional[Dict[str, Any]]) -> Dict[str, bool]:
        options = options or {}
        return {
            "auto_fix_syntax": bool(options.get("auto_fix_syntax", False)),
            "resolve_graphics": bool(options.get("resolve_graphics", False)),
        }

    def _compute_ast_metrics(self, ast) -> Dict[str, int]:
        stats = {"node_count": 0, "max_depth": 0}

        def _visit(node, depth):
            stats["node_count"] += 1
            stats["max_depth"] = max(stats["max_depth"], depth)
            for attr in getattr(node, "__dict__", {}).values():
                if isinstance(attr, list):
                    for child in attr:
                        if hasattr(child, "__dict__"):
                            _visit(child, depth + 1)
                elif hasattr(attr, "__dict__"):
                    _visit(attr, depth + 1)

        _visit(ast, 1)
        return stats

    def _generate_llm_insights(
        self, pseudocode: str, complexity_result
    ) -> Optional[Dict[str, Any]]:
        try:
            worst = str(complexity_result.worst_case.big_o)
            explanation = self.llm_client.explain_complexity(
                pseudocode=pseudocode, complexity_result=worst
            )
            verification = self.llm_client.verify_complexity(
                pseudocode=pseudocode, calculated_complexity=worst
            )
            self.cost_tracker.track_llm_call(
                provider=self.llm_client.provider or "unknown",
                model=LLM_MODELS.get(self.llm_client.provider, ""),
                operation="llm_insights",
                input_tokens=self._estimate_tokens(pseudocode),
                output_tokens=self._estimate_tokens(str(explanation)),
                latency_ms=0.0,
            )
            return {
                "explanation": explanation,
                "verification": verification,
            }
        except Exception as exc:
            logger.warning("LLM insights unavailable: %s", exc)
            return None

    def _maybe_render_recursion_tree(
        self, pseudocode: str, resolve_graphics: bool
    ) -> Optional[str]:
        if not resolve_graphics:
            return None
        tree = getattr(self.calculator.recursive_analyzer, "recursion_tree", None)
        if not tree:
            return None
        self.cost_tracker.start_operation("diagram_generation")
        try:
            visualization = tree.visualize(format_graph="graphviz")
            return self.artifacts.persist_recursion_tree(visualization, pseudocode)
        except Exception as exc:
            logger.warning("Failed to persist recursion tree: %s", exc)
            return None
        finally:
            self.cost_tracker.end_operation("diagram_generation")

    def _finalize_metrics(self) -> Dict[str, Any]:
        try:
            metrics = self.cost_tracker.finalize_analysis()
            return self.cost_tracker.get_metrics_summary(metrics)
        except Exception as exc:
            logger.warning("Unable to finalize metrics: %s", exc)
            return {}

    def _track_translation_cost(
        self, raw_text: str, translation_payload: Dict[str, Any]
    ) -> None:
        if not translation_payload.get("translated"):
            return
        provider = translation_payload.get("provider") or "unknown"
        model = LLM_MODELS.get(provider, "")
        input_tokens = self._estimate_tokens(raw_text)
        output_tokens = self._estimate_tokens(translation_payload.get("pseudocode", ""))
        self.cost_tracker.track_llm_call(
            provider=provider,
            model=model,
            operation="translation",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=0.0,
        )
        latest_call = (
            self.cost_tracker.current_analysis.llm_calls[-1]
            if self.cost_tracker.current_analysis
            and self.cost_tracker.current_analysis.llm_calls
            else None
        )
        translation_payload["token_usage"] = (
            latest_call.total_tokens if latest_call else input_tokens + output_tokens
        )
        if latest_call:
            translation_payload["cost_usd"] = round(latest_call.cost_usd, 6)

    def _track_fix_cost(
        self, old_code: str, new_code: str, provider: Optional[str]
    ) -> None:
        if not provider:
            return
        model = LLM_MODELS.get(provider, "")
        self.cost_tracker.track_llm_call(
            provider=provider,
            model=model,
            operation="auto_fix",
            input_tokens=self._estimate_tokens(old_code),
            output_tokens=self._estimate_tokens(new_code),
            latency_ms=0.0,
        )

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 1
        return max(1, int(len(text.split()) * 3))
