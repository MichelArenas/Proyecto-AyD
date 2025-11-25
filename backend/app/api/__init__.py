"""
Main application entry point for the Algorithm Complexity Analyzer API.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.application.controllers import (AnalysisController,
                                             HealthController)
from app.api.application.dtos import (AnalyzeRequestDTO, AnalyzeResponseDTO,
                                      CompareRequestDTO, CompareResponseDTO,
                                      GenerateDatasetRequestDTO,
                                      GenerateDatasetResponseDTO,
                                      JobResponseDTO)
from app.api.domain.exceptions import DomainException
from app.core import config
from app.core.ml import DatasetGenerator
from app.core.services import AnalysisService, JobService
from app.core.storage.mongodb import MongoDBConnection

logging.basicConfig(
    level=logging.INFO if config.server.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage application lifecycle"""
    db_conn = None

    logger.info("Starting Algorithm Complexity Analyzer API")
    logger.info("Database: %s", config.database.name)
    logger.info("LLM Provider: %s", config.llm.default_provider)

    try:
        db_conn = MongoDBConnection()
        db_conn.connect()
        logger.info("MongoDB connected")
    except Exception as e:
        logger.error("MongoDB connection failed: %s", e)

    yield

    logger.info("Shutting down API")
    try:
        if db_conn:
            db_conn.close()
        logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error("Error closing MongoDB connection: %s", e)


app = FastAPI(
    title="Algorithm Complexity Analyzer",
    description="Analyze algorithm complexity with clean architecture",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with better messages"""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"], "type": error["type"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Request validation failed. Please check the fields below.",
            "details": errors,
        },
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(_: Request, exc: DomainException):
    """Handle domain exceptions"""
    return JSONResponse(
        status_code=getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST),
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "details": getattr(exc, "errors", None),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(_: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error("Unexpected error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "details": str(exc) if config.server.debug else None,
        },
    )


analysis_service = AnalysisService()
job_service = JobService()
dataset_generator = DatasetGenerator()

analysis_controller = AnalysisController(
    analysis_service=analysis_service,
    job_service=job_service,
    dataset_generator=dataset_generator,
)
health_controller = HealthController()


@app.get("/", tags=["Root"])
async def root():
    """API root"""
    return {
        "name": "Algorithm Complexity Analyzer API",
        "version": "2.0.0",
        "architecture": "Clean Architecture",
        "docs": "/docs",
        "endpoints": {
            "analyze": "POST /analyze",
            "compare": "POST /compare",
            "generate_dataset": "POST /generate_dataset",
            "jobs": "GET /jobs/{job_id}",
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        return await health_controller.check_health()
    except DomainException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@app.post("/analyze", tags=["Analysis"], response_model=AnalyzeResponseDTO)
async def analyze_algorithm(request: AnalyzeRequestDTO):
    return await analysis_controller.analyze_algorithm(request)


@app.post("/compare", tags=["Analysis"], response_model=CompareResponseDTO)
async def compare_algorithms(request: CompareRequestDTO):
    return await analysis_controller.compare_algorithm(request)


@app.post(
    "/generate_dataset",
    tags=["ML"],
    response_model=GenerateDatasetResponseDTO,
)
async def generate_dataset(request: GenerateDatasetRequestDTO):
    return await analysis_controller.generate_dataset(request)


@app.get("/jobs/{job_id}", tags=["Jobs"], response_model=JobResponseDTO)
async def get_job(job_id: str):
    return await analysis_controller.get_job(job_id)


__all__ = ["app"]
