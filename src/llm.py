import os
import time

from dotenv import load_dotenv
from google import genai

from schemas import CompanyIntelligence


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY is missing. Please check your .env file."
    )

client = genai.Client(api_key=api_key)


def analyze_company(
    domain: str,
    clean_text: str,
    contact_emails: list[str],
    linkedin_urls: list[str],
) -> CompanyIntelligence:
    """
    Analyze website evidence using Gemini and return
    validated structured company intelligence.

    Automatically retries temporary API failures.
    """

    prompt = f"""
You are an AI company research agent.

Analyze ONLY the public website evidence provided below.

COMPANY DOMAIN:
{domain}

WEBSITE CONTENT:
{clean_text}

EMAILS FOUND DIRECTLY FROM WEBSITE:
{contact_emails}

LINKEDIN URLS FOUND DIRECTLY FROM WEBSITE:
{linkedin_urls}

Extract the following information:

1. Company Overview
   - Give a concise 2-sentence description.
   - Explain what the company does and its main product/service.

2. Target Audience / ICP
   - Identify the likely customers or users.
   - Use only the supplied website evidence.

3. Contact Emails
   - Include only publicly visible company/generic emails.
   - Never invent an email address.
   - Prefer the emails supplied in the evidence.

4. Key Leadership / Team
   - Extract names only when supported by the evidence.
   - Include their role/title when available.
   - Include a LinkedIn URL when available.
   - Never invent people, roles, or URLs.

5. Confidence Score
   - Return a number between 0.0 and 1.0.
   - Use a higher score when the evidence strongly supports the result.
   - Use a lower score when important information is missing.

IMPORTANT RULES:
- Do not hallucinate.
- Do not use outside knowledge.
- Do not invent missing information.
- If information is unavailable, use an empty string, empty list, or null.
- LinkedIn URLs must come from the supplied evidence.
"""

    max_retries = 3

    for attempt in range(max_retries):

        try:

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": CompanyIntelligence,
                },
            )

            return CompanyIntelligence.model_validate_json(
                response.text
            )

        except Exception as error:

            if attempt == max_retries - 1:
                print(
                    f"[ERROR] Gemini failed after "
                    f"{max_retries} attempts: {error}"
                )
                raise

            wait_time = 2 ** attempt

            print(
                f"[WARNING] Gemini request failed. "
                f"Retrying in {wait_time} second(s)..."
            )

            time.sleep(wait_time)

    raise RuntimeError("Unexpected Gemini retry state.")