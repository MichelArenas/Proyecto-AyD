"""Security, audit, and cost logging helpers."""

import logging
from typing import Any, Dict, List, Optional

from app.core.storage.mongodb import (llm_call_repo, policy_event_repo,
                                      sanitization_log_repo)

logger = logging.getLogger(__name__)


class SecurityService:
    """Persists sanitization metadata, policy events, and LLM call logs."""

    def record_sanitization(
        self,
        source: str,
        sanitized: Optional[Dict[str, Any]],
        job_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[str]:
        if not sanitized:
            return None

        payload = {
            "job_id": job_id,
            "request_id": request_id,
            "source": source,
            "raw_preview": sanitized.get("text", "")[:512],
            "operations": sanitized.get("operations", []),
            "truncated": sanitized.get("truncated"),
            "removed_non_ascii": sanitized.get("removed_non_ascii"),
            "sanitized_length": len(sanitized.get("text", "")),
        }

        try:
            return sanitization_log_repo.insert_report(payload)
        except Exception as exc:
            logger.warning("Failed to persist sanitization log: %s", exc)
            return None

    def record_llm_calls(
        self,
        job_id: Optional[str],
        calls: Optional[List[Dict[str, Any]]],
        aggregate: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not job_id or not calls:
            return

        try:
            for call in calls:
                document = {
                    "entry_type": "call",
                    "job_id": job_id,
                    "provider": call.get("provider"),
                    "model": call.get("model"),
                    "operation": call.get("operation"),
                    "tokens": call.get("tokens"),
                    "cost_usd": call.get("cost_usd"),
                    "latency_ms": call.get("latency_ms"),
                }
                llm_call_repo.insert_one(document)

            if aggregate:
                llm_call_repo.insert_one(
                    {
                        "entry_type": "aggregate",
                        "job_id": job_id,
                        "summary": aggregate,
                    }
                )
        except Exception as exc:
            logger.warning("Failed to persist LLM cost metrics: %s", exc)

    def record_policy_event(
        self,
        job_id: Optional[str],
        event_type: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        payload = {
            "job_id": job_id,
            "event_type": event_type,
            "actor": actor,
            "details": details or {},
        }

        try:
            return policy_event_repo.insert_one(payload)
        except Exception as exc:
            logger.warning("Failed to persist policy event: %s", exc)
            return None
