"""
Pydantic Schemas for Autonomous Lead Enrichment Agent
Matches exact JSON output structure:
{
  "generated_at": "...",
  "companies": [
    {
      "company_name": "...",
      "overview": "...",
      "industry": "...",
      "icp": [...],
      "emails": [...],
      "linkedin_urls": [...],
      "source_urls": [...],
      "team": [
        {
          "name": "...",
          "role": "...",
          "linkedin_url": "..."
        }
      ],
      "confidence": 0.9,
      "usage": {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0
      }
    }
  ]
}
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TeamMember(BaseModel):
    name: str = Field(..., description="Full name of key team member or executive")
    role: str = Field(..., description="Title/role (e.g., CEO & Co-Founder, CTO, VP Engineering)")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL if found")


class UsageMetrics(BaseModel):
    prompt_tokens: int = Field(default=0, description="Input tokens used")
    completion_tokens: int = Field(default=0, description="Output tokens generated")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated API cost in USD")


class EnrichedCompany(BaseModel):
    company_name: str = Field(..., description="Official name of the company")
    overview: str = Field(..., description="Concise 2-sentence summary of what the company does")
    industry: str = Field(default="Software", description="Industry classification")
    icp: List[str] = Field(default_factory=list, description="Target Audience / Ideal Customer Profile list")
    emails: List[str] = Field(default_factory=list, description="Generic or public contact emails")
    linkedin_urls: List[str] = Field(default_factory=list, description="Company LinkedIn profile URLs")
    source_urls: List[str] = Field(default_factory=list, description="List of source URLs crawled")
    team: List[TeamMember] = Field(default_factory=list, description="Key leadership & team members with roles and LinkedIn URLs")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    usage: UsageMetrics = Field(default_factory=UsageMetrics, description="Token usage and cost tracking")


class BatchOutput(BaseModel):
    generated_at: str = Field(..., description="ISO 8601 generation timestamp")
    companies: List[EnrichedCompany] = Field(default_factory=list, description="List of enriched company records")
