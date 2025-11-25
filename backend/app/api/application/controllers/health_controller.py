"""
Controller for health check
"""

import logging

from app.api.application.dtos import HealthResponseDTO
from app.api.domain.exceptions import DomainException
from app.core import config
from app.core.storage.mongodb import MongoDBConnection

logger = logging.getLogger(__name__)


class HealthController:
    """Controller for health check"""

    async def check_health(self) -> HealthResponseDTO:
        """Perform health check"""
        try:
            db_conn = MongoDBConnection()
            db = db_conn.get_database()
            db.command("ping")

            return HealthResponseDTO(
                status="healthy",
                database="connected",
                llm_provider=config.llm.default_provider,
                ready=True,
            )
        except Exception as e:
            logger.error("Health check failed: %s", str(e))
            raise DomainException(f"Service unhealthy: {str(e)}") from e
