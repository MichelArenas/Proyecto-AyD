"""High-level analysis service built on top of the NL→AST pipeline."""

from typing import Any, Dict, List, Optional

from app.core.constants import COMPLEXITY_RANK_ORDER, STATUS_COMPLETED
from app.core.services.analysis_pipeline_service import AnalysisPipelineService
from app.core.storage.mongodb import analysis_repo


class AnalysisService:
    """Facade for orchestrating algorithm analysis tasks."""

    def __init__(self):
        self.pipeline = AnalysisPipelineService()

    def analyze_algorithm(
        self,
        pseudocode: str,
        validate_first: bool = True,
        save_to_db: bool = True,
        enable_llm_insights: bool = False,
    ) -> Dict[str, Any]:
        """Analyze already-prepared pseudocode via the shared pipeline."""

        options = {
            "auto_fix_syntax": enable_llm_insights,
            "resolve_graphics": enable_llm_insights,
        }

        result = self.pipeline.run_pipeline(
            raw_text=pseudocode,
            declared_input_type="pseudocode",
            request_id=None,
            options=options,
            validate_before_analysis=validate_first,
            skip_translation=True,
            enable_llm_insights=enable_llm_insights,
        )

        if save_to_db:
            self._persist_analysis(result)

        return result

    def run_full_pipeline(
        self,
        input_text: str,
        declared_input_type: str = "auto",
        request_id: Optional[str] = None,
        options: Optional[Dict[str, bool]] = None,
        validate_first: bool = True,
        enable_llm_insights: bool = False,
        save_to_db: bool = False,
    ) -> Dict[str, Any]:
        """Execute the complete NL→AST analysis pipeline for arbitrary input."""

        result = self.pipeline.run_pipeline(
            raw_text=input_text,
            declared_input_type=declared_input_type,
            request_id=request_id,
            options=options,
            validate_before_analysis=validate_first,
            skip_translation=False,
            enable_llm_insights=enable_llm_insights,
        )

        if save_to_db:
            self._persist_analysis(result)

        return result

    def compare_algorithms(
        self, pseudocode_list: List[str], save_to_db: bool = True
    ) -> Dict[str, Any]:
        """Compare multiple algorithm implementations and recommend the most efficient one."""
        analyses = []

        for i, pseudocode in enumerate(pseudocode_list):
            analysis = self.analyze_algorithm(
                pseudocode, validate_first=True, save_to_db=save_to_db
            )
            analysis["index"] = i
            analyses.append(analysis)

        valid_analyses = [a for a in analyses if a["status"] == STATUS_COMPLETED]

        if not valid_analyses:
            return {
                "status": "no_valid_analyses",
                "error": "None of the provided algorithms could be analyzed",
                "analyses": analyses,
            }

        return {
            "status": STATUS_COMPLETED,
            "total_analyzed": len(pseudocode_list),
            "successful_analyses": len(valid_analyses),
            "analyses": analyses,
            "recommendation": self._generate_recommendation(valid_analyses),
        }

    def _persist_analysis(self, result: Dict[str, Any]) -> None:
        """Persist successful analyses for history endpoints."""
        if result.get("status") != STATUS_COMPLETED:
            return

        analysis_payload = result.get("analysis") or {}
        try:
            doc_id = analysis_repo.save_analysis(
                algorithm_name=analysis_payload.get("algorithm_name") or "unknown",
                algorithm_type=analysis_payload.get("algorithm_type") or "unknown",
                pseudocode=result.get("pseudocode", ""),
                complexity_result=analysis_payload,
                validation_errors=(result.get("validation") or {}).get("errors", []),
            )
            result["db_id"] = doc_id
        except Exception as exc:
            result["db_error"] = str(exc)

    def _generate_recommendation(self, analyses: List[Dict]) -> Dict[str, Any]:
        """Generate recommendation based on complexity analysis."""
        best_index = 0
        best_rank = float("inf")
        best_complexity = None

        for analysis in analyses:
            try:
                worst_case = str(
                    analysis["analysis"]["time_complexity"]["worst_case"]["big_o"]
                )

                rank = COMPLEXITY_RANK_ORDER.get(worst_case, 999)

                if rank < best_rank:
                    best_rank = rank
                    best_index = analysis["index"]
                    best_complexity = worst_case
            except (KeyError, TypeError, AttributeError):
                continue

        if best_rank != float("inf") and best_complexity:
            return {
                "best_implementation": best_index,
                "reason": "Has the best worst-case time complexity",
                "complexity": best_complexity,
            }

        return {
            "best_implementation": None,
            "reason": "Could not determine best implementation",
            "complexity": None,
        }
