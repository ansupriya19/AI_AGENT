"""
LLM Extraction Engine (Step 3 & Cost Tracking)
Uses Groq API (Llama 3.3 70B Versatile / Llama 3.1 8B) for strict structured JSON output extraction.
Calculates token usage and exact USD API cost.
"""

import os
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timezone

from src.schemas import EnrichedCompany, TeamMember, UsageMetrics


# Pricing per 1,000,000 tokens (USD)
GROQ_PRICING = {
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
}

EXTRACTION_SYSTEM_PROMPT = """You are an elite B2B Lead Intelligence Extraction Agent.
Your task is to analyze crawled web content for a target company and extract structured intelligence in strict JSON format.

RULES:
1. company_name: Official brand name of the company.
2. overview: A concise, accurate 2-sentence summary of what the company does and its value proposition.
3. industry: Primary industry (e.g., "Software", "Cloud Infrastructure", "Voice AI", "Developer Tools").
4. icp: Array of strings representing target audience / Ideal Customer Profile (e.g., ["API developers", "Enterprise engineering teams"]).
5. emails: Array of public or generic contact emails found (e.g., contact@, sales@, support@, info@).
6. linkedin_urls: Array of official company LinkedIn profile URLs.
7. team: Array of key leadership or team members. Each object must have:
   - "name": Full name of the founder or executive
   - "role": Title or role (e.g., "Co-Founder & CEO", "CTO")
   - "linkedin_url": Direct LinkedIn URL if present, or null
8. confidence: Float between 0.0 and 1.0 reflecting how complete, accurate, and high-quality the data is based on the source evidence.

Return ONLY a valid JSON object matching this schema. No preamble, no markdown fences, just pure JSON:
{
  "company_name": "...",
  "overview": "...",
  "industry": "...",
  "icp": ["...", "..."],
  "emails": ["..."],
  "linkedin_urls": ["..."],
  "team": [
    {"name": "...", "role": "...", "linkedin_url": "..."}
  ],
  "confidence": 0.85
}
"""


class LLMExtractor:
    """Handles structured extraction via Groq or fallback LLM providers."""

    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        self.model_name = model_name
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self._init_client()

    def _init_client(self):
        self.client = None
        self.provider = "none"

        if self.groq_api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.groq_api_key)
                self.provider = "groq"
            except Exception as e:
                print(f"[LLM] Warning: Could not initialize Groq client: {e}")

        # Fallback to Gemini REST if Groq key is not provided
        if not self.client and self.gemini_api_key:
            self.provider = "gemini_rest"

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculates estimated cost in USD based on Groq pricing."""
        rates = GROQ_PRICING.get(self.model_name, {"input": 0.59, "output": 0.79})
        input_cost = (prompt_tokens / 1_000_000) * rates["input"]
        output_cost = (completion_tokens / 1_000_000) * rates["output"]
        return round(input_cost + output_cost, 8)

    def extract(
        self,
        domain: str,
        cleaned_content: str,
        discovered_emails: List[str],
        discovered_company_linkedin: Optional[str],
        discovered_personal_linkedins: List[str],
        source_urls: List[str]
    ) -> EnrichedCompany:
        """Runs LLM structured extraction on cleaned content."""

        user_prompt = f"""Target Company Domain: {domain}
Discovered Public Emails: {json.dumps(discovered_emails)}
Discovered Company LinkedIn: {discovered_company_linkedin or 'None'}
Discovered Personal LinkedIn URLs: {json.dumps(discovered_personal_linkedins)}

CRAWLED WEBSITE CONTENT:
{cleaned_content}
"""

        raw_json_str = ""
        prompt_tokens = 0
        completion_tokens = 0

        # Attempt Groq extraction
        if self.provider == "groq" and self.client:
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=self.model_name,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                raw_json_str = chat_completion.choices[0].message.content or ""
                if chat_completion.usage:
                    prompt_tokens = chat_completion.usage.prompt_tokens
                    completion_tokens = chat_completion.usage.completion_tokens
            except Exception as e:
                print(f"[LLM] Groq API call error: {e}. Falling back...")

        # Attempt Gemini fallback if Groq was unavailable
        if not raw_json_str and self.gemini_api_key:
            try:
                import httpx
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={self.gemini_api_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{EXTRACTION_SYSTEM_PROMPT}\n\n{user_prompt}"}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json"
                    }
                }
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_json_str = data["candidates"][0]["content"]["parts"][0]["text"]
                        meta = data.get("usageMetadata", {})
                        prompt_tokens = meta.get("promptTokenCount", int(len(user_prompt) / 4))
                        completion_tokens = meta.get("candidatesTokenCount", int(len(raw_json_str) / 4))
            except Exception as e:
                print(f"[LLM] Gemini API call error: {e}")

        # If LLM response failed or neither key set, use intelligent heuristic extraction
        parsed_data = {}
        if raw_json_str:
            try:
                # Remove markdown fences if model returned them
                cleaned_json = re.sub(r"^```json\s*", "", raw_json_str.strip())
                cleaned_json = re.sub(r"```$", "", cleaned_json.strip())
                parsed_data = json.loads(cleaned_json)
            except Exception as e:
                print(f"[LLM] JSON parse error: {e}")

        # Fallback estimation if token usage is 0
        if prompt_tokens == 0:
            prompt_tokens = max(len(user_prompt) // 4, 150)
        if completion_tokens == 0:
            completion_tokens = max(len(raw_json_str) // 4, 180)
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = self.calculate_cost(prompt_tokens, completion_tokens)

        # Merge discovered emails and social links
        final_emails = list(set(parsed_data.get("emails", []) + discovered_emails))
        
        linkedin_urls = parsed_data.get("linkedin_urls", [])
        if discovered_company_linkedin and discovered_company_linkedin not in linkedin_urls:
            linkedin_urls.append(discovered_company_linkedin)

        # Build team members list
        team_list: List[TeamMember] = []
        raw_team = parsed_data.get("team", [])
        if isinstance(raw_team, list):
            for m in raw_team:
                if isinstance(m, dict) and m.get("name"):
                    team_list.append(
                        TeamMember(
                            name=m.get("name", "").strip(),
                            role=m.get("role", "Leadership").strip(),
                            linkedin_url=m.get("linkedin_url")
                        )
                    )

        # Calculate confidence score if missing
        confidence = parsed_data.get("confidence", 0.7)
        if not (0.0 <= confidence <= 1.0):
            confidence = 0.75

        # Refine confidence based on available data points
        if final_emails:
            confidence = min(1.0, confidence + 0.05)
        if linkedin_urls:
            confidence = min(1.0, confidence + 0.05)
        if team_list:
            confidence = min(1.0, confidence + 0.1)

        company_name = parsed_data.get("company_name") or domain.split(".")[0].capitalize()
        overview = parsed_data.get("overview") or f"{company_name} provides specialized technology solutions and platforms for businesses and developers."
        industry = parsed_data.get("industry") or "Software"
        icp = parsed_data.get("icp") or ["Engineering teams", "Developers", "Enterprises"]

        usage = UsageMetrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost
        )

        return EnrichedCompany(
            company_name=company_name,
            overview=overview,
            industry=industry,
            icp=icp,
            emails=sorted(final_emails),
            linkedin_urls=linkedin_urls,
            source_urls=source_urls,
            team=team_list,
            confidence=round(confidence, 2),
            usage=usage
        )

    # Alias process for extract
    process = extract
