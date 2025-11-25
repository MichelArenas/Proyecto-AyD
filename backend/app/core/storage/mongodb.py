"""
MongoDB connection and repository implementations for complexity analysis,
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.core import config
from app.core.constants import (LOG_COLLECTION_LLM_CALLS,
                                LOG_COLLECTION_POLICY_EVENTS,
                                LOG_COLLECTION_SANITIZATION,
                                SANITIZATION_HASH_SALT)


class MongoDBConnection:
    """Singleton MongoDB connection handler"""

    _instance: Optional["MongoDBConnection"] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self) -> Database:
        """Establish MongoDB connection"""
        if self._client is None:
            self._client = MongoClient(config.database.url)
            self._db = self._client[config.database.name]
            self._ensure_indexes()
        return self._db

    def _ensure_indexes(self):
        """Ensure necessary indexes are created"""
        db = self._db

        db.analysis_results.create_index([("algorithm_name", ASCENDING)])
        db.analysis_results.create_index([("created_at", DESCENDING)])
        db.analysis_results.create_index([("algorithm_type", ASCENDING)])

        db.translations.create_index([("created_at", DESCENDING)])
        db.translations.create_index([("input_hash", ASCENDING)], unique=True)

        db.validations.create_index([("created_at", DESCENDING)])
        db.validations.create_index([("is_valid", ASCENDING)])

        db.jobs.create_index([("created_at", DESCENDING)])
        db.jobs.create_index([("status", ASCENDING)])

        db[LOG_COLLECTION_LLM_CALLS].create_index([("job_id", ASCENDING)])
        db[LOG_COLLECTION_LLM_CALLS].create_index([("created_at", DESCENDING)])
        db[LOG_COLLECTION_SANITIZATION].create_index([("job_id", ASCENDING)])
        db[LOG_COLLECTION_SANITIZATION].create_index([("request_hash", ASCENDING)])
        db[LOG_COLLECTION_POLICY_EVENTS].create_index([("job_id", ASCENDING)])
        db[LOG_COLLECTION_POLICY_EVENTS].create_index([("event_type", ASCENDING)])

    def get_database(self) -> Database:
        """Get database instance"""
        if self._db is None:
            return self.connect()
        return self._db

    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None


class BaseRepository:
    """Base repository with common database operations"""

    def __init__(self, collection_name: str):
        self.db_connection = MongoDBConnection()
        self.db = self.db_connection.get_database()
        self.collection: Collection = self.db[collection_name]

    def insert_one(self, document: Dict[str, Any]) -> str:
        """Insert a single document"""
        document["created_at"] = datetime.now()
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def find_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Find document by ID"""
        try:
            result = self.collection.find_one({"_id": ObjectId(doc_id)})
            if result:
                result["_id"] = str(result["_id"])
            return result
        except Exception:
            return None

    def find_all(
        self,
        filter_query: Optional[Dict] = None,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: int = DESCENDING,
    ) -> List[Dict[str, Any]]:
        """Find all documents matching filter"""
        query = filter_query or {}
        cursor = self.collection.find(query).sort(sort_by, sort_order).limit(limit)

        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    def count(self, filter_query: Optional[Dict] = None) -> int:
        """Count documents matching filter"""
        query = filter_query or {}
        return self.collection.count_documents(query)


class AnalysisRepository(BaseRepository):
    """Repository for complexity analysis results"""

    def __init__(self):
        super().__init__("analysis_results")

    def save_analysis(
        self,
        algorithm_name: str,
        algorithm_type: str,
        pseudocode: str,
        complexity_result: Dict[str, Any],
        validation_errors: List[Dict] = [],
    ) -> str:
        """Save a complexity analysis result"""
        document = {
            "algorithm_name": algorithm_name,
            "algorithm_type": algorithm_type,
            "pseudocode": pseudocode,
            "complexity": complexity_result,
            "validation_errors": validation_errors or [],
            "status": "completed",
        }
        return self.insert_one(document)

    def find_by_algorithm_name(
        self, name: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find analyses by algorithm name"""
        return self.find_all({"algorithm_name": name}, limit=limit)

    def find_by_type(
        self, algorithm_type: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find analyses by algorithm type (recursive/iterative)"""
        return self.find_all({"algorithm_type": algorithm_type}, limit=limit)

    def get_recent_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most recent analyses"""
        return self.find_all(limit=limit)


class TranslationRepository(BaseRepository):
    """Repository for natural language translations"""

    def __init__(self):
        super().__init__("translations")

    def save_translation(
        self,
        input_text: str,
        input_type: str,
        output_pseudocode: str,
        provider: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Save a translation result"""
        input_hash = hashlib.md5(input_text.encode()).hexdigest()

        document = {
            "input_hash": input_hash,
            "input_text": input_text,
            "input_type": input_type,
            "output_pseudocode": output_pseudocode,
            "provider": provider,
            "metadata": metadata or {},
            "status": "completed",
        }

        try:
            return self.insert_one(document)
        except Exception:
            existing = self.collection.find_one({"input_hash": input_hash})
            if existing:
                return self._update_translation(str(existing["_id"]), document)
            raise

    def find_by_input_hash(self, input_text: str) -> Optional[Dict[str, Any]]:
        """Find translation by input hash (for caching)"""

        input_hash = hashlib.md5(input_text.encode()).hexdigest()
        result = self.collection.find_one({"input_hash": input_hash})
        if result:
            result["_id"] = str(result["_id"])
        return result

    def _update_translation(self, doc_id: str, document: Dict[str, Any]) -> str:
        """
        Internal method to update an existing translation.
        Used when a duplicate hash is found.
        """
        document["updated_at"] = datetime.now()
        self.collection.update_one({"_id": ObjectId(doc_id)}, {"$set": document})
        return doc_id

    def get_recent_translations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most recent translations"""
        return self.find_all(limit=limit)


class ValidationRepository(BaseRepository):
    """Repository for validation results"""

    def __init__(self):
        super().__init__("validations")

    def save_validation(
        self,
        pseudocode: str,
        is_valid: bool,
        errors: List[Dict],
        warnings: List[Dict],
        validation_types: List[str],
        detected_patterns: Optional[List[str]] = None,
        pattern_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save a validation result"""
        document = {
            "pseudocode": pseudocode,
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "detected_patterns": detected_patterns or [],
            "pattern_summary": pattern_summary or {},
            "validation_types": validation_types,
            "error_count": len(errors),
            "warning_count": len(warnings),
        }
        return self.insert_one(document)

    def find_invalid_codes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Find all invalid pseudocode submissions"""
        return self.find_all({"is_valid": False}, limit=limit)

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        total = self.count()
        valid = self.count({"is_valid": True})
        invalid = self.count({"is_valid": False})

        return {
            "total_validations": total,
            "valid_count": valid,
            "invalid_count": invalid,
            "success_rate": (valid / total * 100) if total > 0 else 0,
        }


class JobRepository(BaseRepository):
    """Repository for persisted analysis jobs."""

    def __init__(self):
        super().__init__("jobs")

    def create_job(self, document: Dict[str, Any]) -> str:
        return self.insert_one(document)

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> str:
        updates["updated_at"] = datetime.now()
        self.collection.update_one({"_id": ObjectId(job_id)}, {"$set": updates})
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.find_by_id(job_id)


analysis_repo = AnalysisRepository()
translation_repo = TranslationRepository()
validation_repo = ValidationRepository()
job_repo = JobRepository()


class LLMCallRepository(BaseRepository):
    def __init__(self):
        super().__init__(LOG_COLLECTION_LLM_CALLS)


class SanitizationLogRepository(BaseRepository):
    def __init__(self):
        super().__init__(LOG_COLLECTION_SANITIZATION)

    def _hash_contents(self, text: str) -> str:
        digest = hashlib.sha256()
        digest.update(SANITIZATION_HASH_SALT.encode("utf-8"))
        digest.update(text.encode("utf-8"))
        return digest.hexdigest()

    def insert_report(self, document: Dict[str, Any]) -> str:
        document["request_hash"] = self._hash_contents(document.get("raw_preview", ""))
        return self.insert_one(document)


class PolicyEventRepository(BaseRepository):
    def __init__(self):
        super().__init__(LOG_COLLECTION_POLICY_EVENTS)


llm_call_repo = LLMCallRepository()
sanitization_log_repo = SanitizationLogRepository()
policy_event_repo = PolicyEventRepository()
