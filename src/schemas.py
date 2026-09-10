from typing import List, Optional

from pydantic import BaseModel, Field


class TeamMember(BaseModel):
    name: str
    role: Optional[str] = None
    linkedin_url: Optional[str] = None


class CompanyIntelligence(BaseModel):
    domain: str
    company_overview: str
    target_audience: str
    contact_emails: List[str]
    team_members: List[TeamMember]
    confidence_score: float = Field(ge=0.0, le=1.0)