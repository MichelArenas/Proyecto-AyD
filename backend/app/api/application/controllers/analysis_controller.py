"""
Controller for the REST endpoints backed by the analysis pipeline.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.api.application.dtos import (AnalysisArtifactsDTO, AnalyzeRequestDTO,
                                      AnalyzeResponseDTO, CompareRequestDTO,
                                      CompareResponseDTO, ComparisonDeltaDTO,
                                      ComplexityBreakdownDTO,
                                      ComplexityCaseDTO, DiagnosticsDTO,
                                      GenerateDatasetRequestDTO,
                                      GenerateDatasetResponseDTO,
                                      JobResponseDTO, LLMInfoDTO,
                                      StudentResultDTO, ValidationIssueDTO,
                                      ValidationSummaryDTO)
from app.api.domain.exceptions import DomainException, ValidationError
from app.core.constants import (ERROR_QUOTA_EXCEEDED, ERROR_TRANSLATION_FAILED,
                                STATUS_COMPLETED, STATUS_VALIDATION_FAILED)
from app.core.ml.dataset_generator import DatasetGenerator
from app.core.services import AnalysisService, JobService


class AnalysisController:
    """Aggregates API operations requiring the analysis pipeline."""

    def __init__(
        self,
        analysis_service: AnalysisService,
        job_service: JobService,
        dataset_generator: DatasetGenerator,
    ):
        self.analysis_service = analysis_service
        self.job_service = job_service
        self.dataset_generator = dataset_generator

    async def analyze_algorithm(self, request: AnalyzeRequestDTO) -> AnalyzeResponseDTO:
        analysis_result = self.analysis_service.run_full_pipeline(
            input_text=request.input_text,
            declared_input_type=request.input_type,
            request_id=request.request_id,
            options=request.options.model_dump(),
            validate_first=True,
            enable_llm_insights=request.options.resolve_graphics,
            save_to_db=False,
        )

        translation_payload = analysis_result.get("translation") or {}

        status = analysis_result.get("status", "failed")
        if status == STATUS_VALIDATION_FAILED:
            raise ValidationError(
                "Pseudocode validation failed",
                errors=analysis_result.get("validation", {}).get("errors", []),
            )
        if status != STATUS_COMPLETED:
            message = analysis_result.get("error", "Analysis pipeline failed")
            error_type = analysis_result.get("error_type")
            if error_type in {ERROR_TRANSLATION_FAILED, ERROR_QUOTA_EXCEEDED}:
                code = 503
            elif status in {"parse_error", "analysis_error"}:
                code = 422
            else:
                code = 400
            raise DomainException(message, status_code=code)

        pseudocode = (
            analysis_result.get("pseudocode")
            or translation_payload.get("pseudocode")
            or request.input_text
        )

        validation_summary = self._build_validation_summary(
            analysis_result.get("validation")
        )
        complexity_breakdown = self._build_complexity_breakdown(
            analysis_result.get("analysis")
        )
        llm_info = self._build_llm_info(
            translation_payload,
            analysis_result.get("analysis"),
            analysis_result.get("metrics"),
        )
        diagnostics = self._build_diagnostics(analysis_result.get("analysis"))
        artifacts_payload = analysis_result.get("artifacts")
        artifacts = (
            AnalysisArtifactsDTO(**artifacts_payload) if artifacts_payload else None
        )

        job_id = self.job_service.save_job(
            {
                "status": status,
                "request_id": request.request_id,
                "input_type": translation_payload.get("input_type", request.input_type),
                "pseudocode": pseudocode,
                "translation": translation_payload,
                "validation": validation_summary.model_dump(),
                "analysis": (
                    complexity_breakdown.model_dump() if complexity_breakdown else None
                ),
                "llm_info": llm_info.model_dump() if llm_info else None,
                "diagnostics": diagnostics.model_dump(),
                "artifacts": artifacts_payload,
                "options": request.options.model_dump(),
                "metrics": analysis_result.get("metrics"),
            }
        )

        return AnalyzeResponseDTO(
            job_id=job_id,
            status=status,
            input_type=translation_payload.get("input_type", "unknown"),
            pseudocode=pseudocode,
            validation=validation_summary,
            analysis=complexity_breakdown,
            llm_info=llm_info,
            diagnostics=diagnostics,
            artifacts=artifacts,
        )

    async def compare_algorithm(self, request: CompareRequestDTO) -> CompareResponseDTO:
        student_result: StudentResultDTO = request.student_result

        if request.reference_job_id:
            job = self.job_service.get_job(request.reference_job_id)
            if not job:
                raise DomainException("Referenced job id not found", status_code=404)
            if job.get("status") != STATUS_COMPLETED:
                raise DomainException(
                    "Referenced job is not completed", status_code=409
                )
            system_breakdown = self._deserialize_complexity_breakdown(
                job.get("analysis")
            )
            system_job_id = request.reference_job_id
        else:
            analysis_result = self.analysis_service.analyze_algorithm(
                pseudocode=student_result.pseudocode,
                validate_first=True,
                save_to_db=False,
                enable_llm_insights=False,
            )

            status = analysis_result.get("status")
            if status != STATUS_COMPLETED:
                message = analysis_result.get("error", "Comparison analysis failed")
                raise DomainException(message, status_code=422)

            validation_summary = self._build_validation_summary(
                analysis_result.get("validation")
            )
            system_breakdown = self._build_complexity_breakdown(
                analysis_result.get("analysis")
            )
            llm_info = self._build_llm_info({}, analysis_result.get("analysis"))
            diagnostics = self._build_diagnostics(analysis_result.get("analysis"))
            system_job_id = self.job_service.save_job(
                {
                    "status": status,
                    "input_type": "pseudocode",
                    "pseudocode": student_result.pseudocode,
                    "validation": validation_summary.model_dump(),
                    "analysis": (
                        system_breakdown.model_dump() if system_breakdown else None
                    ),
                    "llm_info": llm_info.model_dump() if llm_info else None,
                    "diagnostics": diagnostics.model_dump(),
                    "artifacts": None,
                    "options": {
                        "resolve_graphics": False,
                        "auto_fix_syntax": False,
                    },
                }
            )

        if not system_breakdown:
            raise DomainException(
                "System analysis missing complexity breakdown", status_code=500
            )

        differences = self._compare_complexities(system_breakdown, student_result)
        matches = len(differences) == 0
        message = (
            "Student analysis matches system result"
            if matches
            else "Differences detected"
        )

        return CompareResponseDTO(
            matches=matches,
            differences=differences,
            system_job_id=system_job_id,
            message=message,
        )

    async def get_job(self, job_id: str) -> JobResponseDTO:
        job = self.job_service.get_job(job_id)
        if not job:
            raise DomainException("Job not found", status_code=404)

        breakdown = self._deserialize_complexity_breakdown(job.get("analysis"))
        validation = self._deserialize_validation(job.get("validation"))
        llm_info = self._deserialize_llm_info(job.get("llm_info"))
        diagnostics = self._deserialize_diagnostics(job.get("diagnostics"))
        artifacts = self._deserialize_artifacts(job.get("artifacts"))

        return JobResponseDTO(
            job_id=job_id,
            status=job.get("status", "completed"),
            input_type=job.get("input_type", "unknown"),
            pseudocode=job.get("pseudocode", ""),
            validation=validation,
            analysis=breakdown,
            llm_info=llm_info,
            diagnostics=diagnostics,
            artifacts=artifacts,
        )

    async def generate_dataset(
        self, request: GenerateDatasetRequestDTO
    ) -> GenerateDatasetResponseDTO:
        start = datetime.now(timezone.utc)
        dataset, stats = self.dataset_generator.generate_dataset(
            target_size=request.target_size,
            patterns=request.patterns,
            allow_variations=request.allow_variations,
            variations_per_example=request.variations_per_example,
            max_attempts=request.max_attempts,
            enable_llm_verification=request.enable_llm_verification,
        )

        json_path = self.dataset_generator.export_to_json(
            dataset, output_path="data/ml_datasets/algorithms_dataset.json"
        )
        csv_path = self.dataset_generator.export_to_csv(
            dataset, output_path="data/ml_datasets/algorithms_dataset.csv"
        )
        end = datetime.now(timezone.utc)

        return GenerateDatasetResponseDTO(
            total_examples=len(dataset),
            json_path=json_path,
            csv_path=csv_path,
            started_at=start.isoformat() + "Z",
            completed_at=end.isoformat() + "Z",
            metadata=stats,
        )

    def _build_validation_summary(
        self, payload: Optional[Dict[str, Any]]
    ) -> ValidationSummaryDTO:
        if not payload:
            return ValidationSummaryDTO(valid=True, errors=[], warnings=[])

        def map_issues(
            items: Optional[List[Dict[str, Any]]],
        ) -> List[ValidationIssueDTO]:
            mapped: List[ValidationIssueDTO] = []
            if not items:
                return mapped
            for item in items:
                mapped.append(
                    ValidationIssueDTO(
                        message=item.get("message") or item.get("detail") or str(item),
                        location=item.get("location") or item.get("node"),
                        code=item.get("code"),
                    )
                )
            return mapped

        valid_flag = (
            payload.get("is_valid")
            if "is_valid" in payload
            else payload.get("valid", True)
        )
        return ValidationSummaryDTO(
            valid=bool(valid_flag),
            errors=map_issues(payload.get("errors")),
            warnings=map_issues(payload.get("warnings")),
        )

    def _build_complexity_breakdown(
        self, analysis_payload: Optional[Dict[str, Any]]
    ) -> Optional[ComplexityBreakdownDTO]:
        if not analysis_payload:
            return None
        time_complexity = analysis_payload.get("time_complexity")
        if not time_complexity:
            return None

        def build_case(case_payload: Optional[Dict[str, Any]]) -> ComplexityCaseDTO:
            if not case_payload:
                return ComplexityCaseDTO(notation="O(1)", steps=[])
            notation = str(
                case_payload.get("big_o") or case_payload.get("notation") or "O(?)"
            )
            steps: List[str] = []
            evidence = case_payload.get("evidence")
            if isinstance(evidence, list):
                steps.extend(str(item) for item in evidence if item)
            explanation = case_payload.get("explanation")
            if explanation and not steps:
                steps.append(str(explanation))
            return ComplexityCaseDTO(notation=notation, steps=steps)

        return ComplexityBreakdownDTO(
            best=build_case(time_complexity.get("best_case")),
            avg=build_case(time_complexity.get("average_case")),
            worst=build_case(time_complexity.get("worst_case")),
        )

    def _build_llm_info(
        self,
        translation_payload: Dict[str, Any],
        analysis_payload: Optional[Dict[str, Any]],
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Optional[LLMInfoDTO]:
        provider = translation_payload.get("provider")
        llm_insights = (
            (analysis_payload or {}).get("llm_insights") if analysis_payload else None
        )
        llm_metrics = (metrics or {}).get("llm") if metrics else None
        if not provider and not llm_insights and not llm_metrics:
            return None

        tokens = translation_payload.get("token_usage") or (llm_insights or {}).get(
            "token_usage"
        )
        if not tokens and llm_metrics:
            tokens = llm_metrics.get("total_tokens")

        cost = (llm_insights or {}).get("cost_usd")
        if cost is None and llm_metrics:
            cost = llm_metrics.get("total_cost_usd")

        model = provider or (llm_insights or {}).get("provider")
        return LLMInfoDTO(model=model, tokens=tokens, cost_usd=cost)

    def _build_diagnostics(
        self, analysis_payload: Optional[Dict[str, Any]]
    ) -> DiagnosticsDTO:
        insights = (
            (analysis_payload or {}).get("llm_insights") if analysis_payload else None
        )
        if not insights:
            return DiagnosticsDTO(divergence=False, notes=[])
        notes: List[str] = []
        for key, value in insights.items():
            if isinstance(value, str):
                notes.append(f"{key}: {value}")
        return DiagnosticsDTO(divergence=False, notes=notes)

    def _deserialize_complexity_breakdown(
        self, payload: Optional[Dict[str, Any]]
    ) -> Optional[ComplexityBreakdownDTO]:
        if not payload:
            return None
        return ComplexityBreakdownDTO(**payload)

    def _deserialize_validation(
        self, payload: Optional[Dict[str, Any]]
    ) -> ValidationSummaryDTO:
        if not payload:
            return ValidationSummaryDTO(valid=True, errors=[], warnings=[])
        return ValidationSummaryDTO(**payload)

    def _deserialize_llm_info(
        self, payload: Optional[Dict[str, Any]]
    ) -> Optional[LLMInfoDTO]:
        if not payload:
            return None
        return LLMInfoDTO(**payload)

    def _deserialize_diagnostics(
        self, payload: Optional[Dict[str, Any]]
    ) -> DiagnosticsDTO:
        if not payload:
            return DiagnosticsDTO(divergence=False, notes=[])
        return DiagnosticsDTO(**payload)

    def _deserialize_artifacts(
        self, payload: Optional[Dict[str, Any]]
    ) -> Optional[AnalysisArtifactsDTO]:
        if not payload:
            return None
        return AnalysisArtifactsDTO(**payload)

    def _compare_complexities(
        self, system_breakdown: ComplexityBreakdownDTO, student_result: StudentResultDTO
    ) -> List[ComparisonDeltaDTO]:
        diffs: List[ComparisonDeltaDTO] = []
        student = student_result.claimed_complexity
        mapping = {
            "best": (student.best, system_breakdown.best.notation),
            "avg": (student.avg, system_breakdown.avg.notation),
            "worst": (student.worst, system_breakdown.worst.notation),
        }
        for case, (student_val, system_val) in mapping.items():
            if student_val.strip() != system_val.strip():
                diffs.append(
                    ComparisonDeltaDTO(
                        case=case, student=student_val, system=system_val
                    )
                )
        return diffs
