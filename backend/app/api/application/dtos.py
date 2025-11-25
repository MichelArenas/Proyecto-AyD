"""
Data Transfer Objects for the public REST API.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AnalysisOptionsDTO(BaseModel):
    """Options applicable to the main analysis request."""

    resolve_graphics: bool = Field(
        default=False,
        description="Generate visual artifacts such as recursion trees or AST diagrams.",
    )
    auto_fix_syntax: bool = Field(
        default=False,
        description="Enable automatic syntax fixing via LLM when parsing fails.",
    )


class AnalyzeRequestDTO(BaseModel):
    """Request payload for POST /analyze."""

    input_text: str = Field(
        ...,
        min_length=5,
        description="Natural language description or pseudocode snippet to analyze.",
    )
    input_type: Literal["auto", "nl", "pseudocode"] = Field(
        default="auto",
        description="Explicitly declare the input type or let the system detect it.",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Optional client-provided identifier for traceability.",
        max_length=128,
    )
    options: AnalysisOptionsDTO = Field(
        default_factory=AnalysisOptionsDTO,
        description="Feature toggles for this analysis job.",
    )

    @field_validator("input_text")
    @classmethod
    def _normalize_input(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("input_text cannot be empty")
        return text


class ComplexityCaseDTO(BaseModel):
    """Time complexity notation plus derivation steps."""

    notation: str = Field(..., description="Complexity expressed in O/Ω/Θ format.")
    steps: List[str] = Field(
        default_factory=list,
        description="Ordered reasoning steps or equations used to reach the notation.",
    )


class ComplexityBreakdownDTO(BaseModel):
    """Container for best/average/worst case time complexity."""

    best: ComplexityCaseDTO
    avg: ComplexityCaseDTO
    worst: ComplexityCaseDTO


class ValidationIssueDTO(BaseModel):
    """Represents a validation warning or error."""

    message: str
    location: Optional[str] = None
    code: Optional[str] = None


class ValidationSummaryDTO(BaseModel):
    """Validation status for the parsed pseudocode."""

    valid: bool
    errors: List[ValidationIssueDTO] = Field(default_factory=list)
    warnings: List[ValidationIssueDTO] = Field(default_factory=list)


class LLMInfoDTO(BaseModel):
    """Metadata about LLM interactions used during the pipeline."""

    model: Optional[str] = None
    tokens: Optional[int] = None
    cost_usd: Optional[float] = Field(
        default=None, description="Approximate USD cost for LLM calls in this job."
    )


class DiagnosticsDTO(BaseModel):
    """Diagnostics section highlighting divergences or notes."""

    divergence: bool = False
    notes: List[str] = Field(default_factory=list)


class AnalysisArtifactsDTO(BaseModel):
    """Paths or identifiers for generated artifacts."""

    ast_digest: Optional[str] = None
    ast_path: Optional[str] = None
    recursion_tree_svg: Optional[str] = None
    logs_path: Optional[str] = None


class AnalyzeResponseDTO(BaseModel):
    """Standard response body for POST /analyze and GET /jobs/{job_id}."""

    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    input_type: str
    pseudocode: str
    validation: ValidationSummaryDTO
    analysis: Optional[ComplexityBreakdownDTO] = None
    llm_info: Optional[LLMInfoDTO] = None
    diagnostics: DiagnosticsDTO = Field(default_factory=DiagnosticsDTO)
    artifacts: Optional[AnalysisArtifactsDTO] = None


class ComplexityTripletDTO(BaseModel):
    """Simplified complexity specification used by students."""

    best: str
    avg: str
    worst: str


class StudentResultDTO(BaseModel):
    """Student-provided analysis for comparison."""

    pseudocode: str = Field(..., min_length=5)
    claimed_complexity: ComplexityTripletDTO
    notes: Optional[str] = None

    @field_validator("pseudocode")
    @classmethod
    def _normalize_pseudocode(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("pseudocode cannot be empty")
        return text


class CompareRequestDTO(BaseModel):
    """Request payload for POST /compare."""

    student_result: StudentResultDTO
    reference_job_id: Optional[str] = Field(
        default=None,
        description="Optional analysis job id to compare against instead of recalculating.",
    )


class ComparisonDeltaDTO(BaseModel):
    """Difference between student and system complexity notations."""

    case: Literal["best", "avg", "worst"]
    student: str
    system: str


class CompareResponseDTO(BaseModel):
    """Response body for comparison requests."""

    matches: bool
    differences: List[ComparisonDeltaDTO]
    system_job_id: str
    message: str


class GenerateDatasetRequestDTO(BaseModel):
    """Request body for POST /generate_dataset."""

    target_size: int = Field(
        default=5000,
        ge=100,
        description="Desired number of synthetic examples after filtering.",
    )
    allow_variations: bool = Field(
        default=True, description="Enable automatic template variations via LLM."
    )
    patterns: Optional[List[str]] = Field(
        default=None,
        description="Optional subset of algorithmic patterns to generate.",
    )
    enable_llm_verification: bool = Field(
        default=False,
        description="Cross-check inferred labels with an auxiliary LLM analysis.",
    )
    variations_per_example: int = Field(
        default=1,
        ge=0,
        le=3,
        description="How many validated variations to request per accepted base example.",
    )
    max_attempts: Optional[int] = Field(
        default=None,
        ge=100,
        description="Optional cap on raw generation attempts to avoid runaway costs.",
    )


class GenerateDatasetResponseDTO(BaseModel):
    """Response for dataset generation endpoint."""

    total_examples: int
    json_path: str
    csv_path: str
    started_at: str
    completed_at: str
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed generation stats, rejection counts, and pattern breakdown.",
    )


class JobResponseDTO(AnalyzeResponseDTO):
    """Alias for clarity when returning job lookups."""


class HealthResponseDTO(BaseModel):
    """Health check response DTO."""

    status: str
    database: str
    llm_provider: Optional[str] = None
    ready: bool = True
