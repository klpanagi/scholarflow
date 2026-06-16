from pydantic import BaseModel, Field


class StrengthWeakness(BaseModel):
    point: str = Field(..., min_length=10, max_length=500)
    evidence: str = Field(..., min_length=10, max_length=500)
    severity: str = Field(..., pattern=r"^(critical|major|minor)$")


class PaperAnalysis(BaseModel):
    summary: str = Field(..., min_length=50, max_length=1000)
    key_findings: list[str] = Field(..., min_length=1, max_length=10)
    methodology: str = Field(..., min_length=20, max_length=500)
    contributions: list[str] = Field(..., min_length=1, max_length=10)
    limitations: list[str] = Field(..., min_length=0, max_length=10)

    strengths: list[StrengthWeakness] = Field(..., min_length=1, max_length=10)
    weaknesses: list[StrengthWeakness] = Field(..., min_length=1, max_length=10)
    suggestions: list[str] = Field(..., min_length=1, max_length=10)

    scientific_areas: list[str] = Field(..., min_length=1, max_length=5)
    keywords: list[str] = Field(..., min_length=3, max_length=15)
    field_of_study: str = Field(..., min_length=2, max_length=100)
    subfield: str = Field(..., min_length=2, max_length=100)

    quality_score: float = Field(..., ge=1.0, le=10.0)
    quality_rationale: str = Field(..., min_length=20, max_length=500)
    novelty_score: float = Field(..., ge=1.0, le=10.0)
    novelty_rationale: str = Field(..., min_length=20, max_length=500)
    rigor_score: float = Field(..., ge=1.0, le=10.0)
    rigor_rationale: str = Field(..., min_length=20, max_length=500)
    clarity_score: float = Field(..., ge=1.0, le=10.0)
    clarity_rationale: str = Field(..., min_length=20, max_length=500)

    doc_type: str = Field(..., pattern=r"^(journal|conference|preprint|thesis|report|other)$")
    venue_type: str = Field(..., pattern=r"^(journal|conference|workshop|arxiv|other)$")
    estimated_venue_tier: str = Field(..., pattern=r"^(top|high|mid|low|unknown)$")
