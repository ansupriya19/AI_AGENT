import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)

MAX_INPUT_CHARS = int(
    os.getenv("LLM_MAX_INPUT_CHARS", "7500")
)

MAX_PEOPLE = int(
    os.getenv("LLM_MAX_PEOPLE", "20")
)

MAX_EMAILS = int(
    os.getenv("LLM_MAX_EMAILS", "25")
)

MAX_LINKEDIN = int(
    os.getenv("LLM_MAX_LINKEDIN", "30")
)

MAX_SOURCES = int(
    os.getenv("LLM_MAX_SOURCES", "15")
)

MAX_SEARCH = int(
    os.getenv("LLM_MAX_SEARCH", "15")
)


def _get_client() -> Groq:

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from .env"
        )

    return Groq(api_key=api_key)


def _safe_list(value):
    return value if isinstance(value, list) else []


def _compact_people(
    people: List[dict]
) -> List[dict]:

    result = []

    for person in people[:MAX_PEOPLE]:

        if not isinstance(person, dict):
            continue

        result.append(
            {
                "name": str(
                    person.get("name") or ""
                ).strip(),

                "role": str(
                    person.get("role") or ""
                ).strip(),

                "linkedin_url": str(
                    person.get("linkedin_url") or ""
                ).strip(),

                "source_url": str(
                    person.get("source_url") or ""
                ).strip(),
            }
        )

    return result


def _compact_search(
    results: List[dict]
) -> List[dict]:

    output = []

    for item in results[:MAX_SEARCH]:

        if not isinstance(item, dict):
            continue

        output.append(
            {
                "query": str(
                    item.get("query") or ""
                ).strip(),

                "title": str(
                    item.get("title") or ""
                ).strip(),

                "snippet": str(
                    item.get("snippet") or ""
                ).strip(),

                "linkedin_url": str(
                    item.get("linkedin_url") or ""
                ).strip(),

                "source": str(
                    item.get("source") or ""
                ).strip(),
            }
        )

    return output


def _build_schema():

    return {
        "type": "object",
        "properties": {

            "company_name": {
                "type": "string"
            },

            "overview": {
                "type": "string"
            },

            "industry": {
                "type": "string"
            },

            "icp": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },

            "team": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        "name": {
                            "type": "string"
                        },

                        "role": {
                            "type": "string"
                        },

                        "linkedin_url": {
                            "type": [
                                "string",
                                "null"
                            ]
                        }
                    },

                    "required": [
                        "name",
                        "role",
                        "linkedin_url"
                    ],

                    "additionalProperties": False
                }
            },

            "emails": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },

            "linkedin_urls": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },

            "source_urls": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },

            "confidence": {
                "type": "number"
            }
        },

        "required": [
            "company_name",
            "overview",
            "industry",
            "icp",
            "team",
            "emails",
            "linkedin_urls",
            "source_urls",
            "confidence"
        ],

        "additionalProperties": False
    }


def _calculate_cost(
    prompt_tokens: int,
    completion_tokens: int
) -> float:

    input_price = float(
        os.getenv(
            "GROQ_INPUT_PRICE_PER_1M",
            "0.075"
        )
    )

    output_price = float(
        os.getenv(
            "GROQ_OUTPUT_PRICE_PER_1M",
            "0.30"
        )
    )

    input_cost = (
        prompt_tokens / 1_000_000
    ) * input_price

    output_cost = (
        completion_tokens / 1_000_000
    ) * output_price

    return round(
        input_cost + output_cost,
        9
    )


def analyze_company(
    domain: str,
    website_text: str,
    emails: List[str],
    linkedin_urls: List[str],
    people_evidence: List[dict],
    source_urls: List[str],
    search_evidence: List[dict]
) -> Dict[str, Any]:

    website_text = (
        website_text or ""
    )[:MAX_INPUT_CHARS]

    emails = _safe_list(emails)
    linkedin_urls = _safe_list(linkedin_urls)
    people_evidence = _safe_list(
        people_evidence
    )
    source_urls = _safe_list(source_urls)
    search_evidence = _safe_list(
        search_evidence
    )

    compact_people = _compact_people(
        people_evidence
    )

    compact_search = _compact_search(
        search_evidence
    )

    evidence = {
        "domain": domain,

        "website_text": website_text,

        "people_evidence": compact_people,

        "linkedin_urls": linkedin_urls[
            :MAX_LINKEDIN
        ],

        "emails": emails[
            :MAX_EMAILS
        ],

        "source_urls": source_urls[
            :MAX_SOURCES
        ],

        "external_search": compact_search
    }

    system_prompt = """
You are a professional company intelligence extraction agent.

Your task is to extract factual company intelligence from website
and search evidence.

For TEAM MEMBERS:

- Identify real people associated with the company.
- Match personal LinkedIn URLs to names.
- Determine professional roles when supported by evidence.
- A personal LinkedIn URL such as /in/john-smith is evidence about
  a person, but the slug alone is not sufficient to invent facts.
- Search the supplied website evidence for the corresponding person.
- Search for leadership, founders, executives, management and team
  information.
- Never confuse the company LinkedIn URL with a person's URL.
- Never invent a role.
- Never invent a person's identity.
- Use empty role only when the supplied evidence genuinely does not
  support a role.

IMPORTANT:

A team member object should look like:

{
  "name": "Full Name",
  "role": "Actual Role",
  "linkedin_url": "https://www.linkedin.com/in/example"
}

For COMPANY:

Extract:
- company name
- overview
- industry
- ideal customer profile
- public emails
- LinkedIn URLs
- source URLs
- confidence

Use only information supported by evidence.
"""

    user_prompt = (
        "Analyze this company.\n\n"
        + json.dumps(
            evidence,
            ensure_ascii=False,
            separators=(",", ":")
        )
    )

    print(
        "\n========== GROQ REQUEST =========="
    )

    print(
        f"Model: {MODEL}"
    )

    print(
        f"Input characters: "
        f"{len(system_prompt + user_prompt)}"
    )

    print(
        f"People evidence: "
        f"{len(compact_people)}"
    )

    print(
        f"LinkedIn URLs: "
        f"{len(linkedin_urls)}"
    )

    print(
        "=================================="
    )

    client = _get_client()

    response = client.chat.completions.create(
        model=MODEL,

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],

        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "company_intelligence",
                "strict": True,
                "schema": _build_schema()
            }
        },

        reasoning_effort="low",

        max_completion_tokens=700,

        temperature=0.1
    )

    content = (
        response.choices[0]
        .message.content
        or "{}"
    )

    parsed = json.loads(content)

    usage = response.usage

    prompt_tokens = int(
        getattr(
            usage,
            "prompt_tokens",
            0
        ) or 0
    )

    completion_tokens = int(
        getattr(
            usage,
            "completion_tokens",
            0
        ) or 0
    )

    total_tokens = int(
        getattr(
            usage,
            "total_tokens",
            prompt_tokens + completion_tokens
        )
        or
        (
            prompt_tokens
            + completion_tokens
        )
    )

    estimated_cost = _calculate_cost(
        prompt_tokens,
        completion_tokens
    )

    parsed["usage"] = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost
    }

    parsed.setdefault(
        "company_name",
        domain
    )

    parsed.setdefault(
        "overview",
        ""
    )

    parsed.setdefault(
        "industry",
        ""
    )

    parsed.setdefault(
        "icp",
        []
    )

    parsed.setdefault(
        "team",
        []
    )

    parsed.setdefault(
        "emails",
        []
    )

    parsed.setdefault(
        "linkedin_urls",
        []
    )

    parsed.setdefault(
        "source_urls",
        []
    )

    parsed.setdefault(
        "confidence",
        0.0
    )

    print(
        "\n========== GROQ SUCCESS =========="
    )

    print(
        f"Prompt tokens: "
        f"{prompt_tokens}"
    )

    print(
        f"Completion tokens: "
        f"{completion_tokens}"
    )

    print(
        f"Total tokens: "
        f"{total_tokens}"
    )

    print(
        f"Estimated cost: "
        f"${estimated_cost:.9f}"
    )

    print(
        "=================================="
    )

    return parsed