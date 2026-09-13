from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TeamMember(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    name: str = Field(
        min_length=1
    )

    role: str = ""

    linkedin_url: Optional[str] = None


class SearchEvidence(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    query: str = ""

    title: str = ""

    url: str = ""

    snippet: str = ""


class UsageMetrics(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    input_tokens: int = Field(
        default=0,
        ge=0
    )

    output_tokens: int = Field(
        default=0,
        ge=0
    )

    total_tokens: int = Field(
        default=0,
        ge=0
    )

    estimated_cost_usd: float = Field(
        default=0.0,
        ge=0.0
    )


class CompanyIntelligence(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    domain: str

    status: str

    company_overview: str

    target_audience: str

    contact_emails: List[str] = Field(
        default_factory=list
    )

    linkedin_urls: List[str] = Field(
        default_factory=list
    )

    team_members: List[TeamMember] = Field(
        default_factory=list
    )

    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0
    )

    source_urls: List[str] = Field(
        default_factory=list
    )

    search_evidence: List[SearchEvidence] = Field(
        default_factory=list
    )

    usage: UsageMetrics = Field(
        default_factory=UsageMetrics
    )

    error: Optional[str] = None