"""Service wrapper around the job repository."""

import logging
from typing import Any, Dict, Optional

from app.core.services.security_service import SecurityService
from app.core.storage.mongodb import job_repo

logger = logging.getLogger(__name__)


class JobService:
    """Provides CRUD helpers for analysis jobs."""

    def __init__(self):
        self.security_service = SecurityService()

    def save_job(self, document: Dict[str, Any]) -> str:
        job_id = job_repo.create_job(document)
        self._log_security(job_id, document, event="created")
        return job_id

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> str:
        if not job_repo.get_job(job_id):
            raise ValueError("Job not found")
        result = job_repo.update_job(job_id, updates)
        self._log_security(job_id, updates, event="updated")
        return result

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return job_repo.get_job(job_id)

    def _log_security(
        self,
        job_id: Optional[str],
        payload: Dict[str, Any],
        event: str,
    ) -> None:
        request_id = payload.get("request_id")
        translation = payload.get("translation") or {}
        sanitization = (
            translation.get("sanitization") if isinstance(translation, dict) else None
        )
        if sanitization:
            try:
                self.security_service.record_sanitization(
                    source="job_service",
                    sanitized=sanitization,
                    job_id=job_id,
                    request_id=request_id,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to audit sanitization for job %s: %s", job_id, exc
                )

        metrics = payload.get("metrics") or {}
        llm_metrics = metrics.get("llm") if isinstance(metrics, dict) else None
        calls = (
            llm_metrics.get("calls_breakdown")
            if isinstance(llm_metrics, dict)
            else None
        )
        if calls:
            formatted_calls = [
                {
                    "provider": call.get("provider"),
                    "model": call.get("model"),
                    "operation": call.get("operation"),
                    "tokens": call.get("tokens"),
                    "cost_usd": call.get("cost_usd"),
                    "latency_ms": call.get("latency_ms"),
                }
                for call in calls
            ]
            aggregate = {
                "total_calls": llm_metrics.get("total_calls"),
                "total_tokens": llm_metrics.get("total_tokens"),
                "total_cost_usd": llm_metrics.get("total_cost_usd"),
                "total_time_ms": llm_metrics.get("total_time_ms"),
            }
            try:
                self.security_service.record_llm_calls(
                    job_id=job_id,
                    calls=formatted_calls,
                    aggregate=aggregate,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to persist LLM metrics for job %s: %s", job_id, exc
                )

        status = payload.get("status", "unknown")
        try:
            self.security_service.record_policy_event(
                job_id=job_id,
                event_type=f"job.{event}.{status}",
                actor="job_service",
                details={"request_id": request_id},
            )
        except Exception as exc:
            logger.warning("Failed to log policy event for job %s: %s", job_id, exc)
