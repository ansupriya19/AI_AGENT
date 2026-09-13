import re
from typing import Any, Dict
from urllib.parse import urlparse

from src.crawler import crawl_website
from src.extractor import process_pages
from src.search import external_search
from src.llm import analyze_company


def _name_from_linkedin(url: str) -> str:

    if not url:
        return ""

    try:
        path = urlparse(url).path.strip("/")

        parts = path.split("/")

        if (
            len(parts) >= 2
            and parts[0].lower() == "in"
        ):
            slug = re.sub(
                r"[^A-Za-z0-9_-]",
                "",
                parts[1]
            )

            words = re.split(
                r"[-_]+",
                slug
            )

            words = [
                w for w in words
                if w
            ]

            if len(words) >= 2:
                return " ".join(
                    w.capitalize()
                    for w in words
                )

    except Exception:
        pass

    return ""


def _clean_email(email: str) -> str:

    email = str(email or "").strip().lower()

    for garbage in [
        "u003e",
        "u003c",
        "&gt;",
        "&lt;",
        "&#62;",
        "&#60;",
    ]:
        email = email.replace(
            garbage,
            ""
        )

    return email.strip()


def _merge_emails(
    llm_emails,
    deterministic_emails
):

    result = []
    seen = set()

    for email in (
        list(deterministic_emails or [])
        + list(llm_emails or [])
    ):

        email = _clean_email(email)

        if not email:
            continue

        if "@" not in email:
            continue

        if email in seen:
            continue

        seen.add(email)
        result.append(email)

    return result


def _merge_strings(
    first,
    second
):

    result = []
    seen = set()

    for value in (
        list(first or [])
        + list(second or [])
    ):

        value = str(
            value or ""
        ).strip()

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


def _merge_team(
    llm_team,
    deterministic_team
):

    merged = []

    # Deterministic evidence comes first.
    # It must never be discarded.
    for person in (
        deterministic_team or []
    ):

        if not isinstance(person, dict):
            continue

        linkedin = str(
            person.get(
                "linkedin_url"
            )
            or ""
        ).strip()

        name = str(
            person.get("name")
            or ""
        ).strip()

        role = str(
            person.get("role")
            or ""
        ).strip()

        if not name and linkedin:
            name = _name_from_linkedin(
                linkedin
            )

        if (
            not name
            and not role
            and not linkedin
        ):
            continue

        merged.append(
            {
                "name": name,
                "role": role,
                "linkedin_url": (
                    linkedin or None
                )
            }
        )

    # Now enrich from LLM
    for person in (
        llm_team or []
    ):

        if not isinstance(person, dict):
            continue

        name = str(
            person.get("name")
            or ""
        ).strip()

        role = str(
            person.get("role")
            or ""
        ).strip()

        linkedin = str(
            person.get(
                "linkedin_url"
            )
            or ""
        ).strip()

        if not name and linkedin:
            name = _name_from_linkedin(
                linkedin
            )

        match = None

        for existing in merged:

            existing_linkedin = str(
                existing.get(
                    "linkedin_url"
                )
                or ""
            ).strip().lower()

            existing_name = str(
                existing.get("name")
                or ""
            ).strip().lower()

            if (
                linkedin
                and existing_linkedin
                and linkedin.lower()
                == existing_linkedin
            ):
                match = existing
                break

            if (
                name
                and existing_name
                and name.lower()
                == existing_name
            ):
                match = existing
                break

        if match:

            if not match["name"] and name:
                match["name"] = name

            if not match["role"] and role:
                match["role"] = role

            if (
                not match["linkedin_url"]
                and linkedin
            ):
                match["linkedin_url"] = linkedin

        else:

            merged.append(
                {
                    "name": name,
                    "role": role,
                    "linkedin_url": (
                        linkedin or None
                    )
                }
            )

    return merged


def run_company_pipeline(
    domain: str,
    max_pages: int = 50
) -> Dict[str, Any]:

    domain = domain.strip()

    print(
        "\n" + "=" * 70
    )

    print(
        f"PROCESSING: {domain}"
    )

    print(
        "=" * 70
    )

    # =========================================================
    # 1. CRAWL
    # =========================================================

    print(
        "\n[1/5] Crawling website..."
    )

    pages = crawl_website(
        domain,
        max_pages=max_pages
    )

    print(
        f"Pages crawled: {len(pages)}"
    )

    # =========================================================
    # 2. DETERMINISTIC EXTRACTION
    # =========================================================

    print(
        "\n[2/5] Extracting ALL page evidence..."
    )

    try:

        (
            website_text,
            emails,
            linkedin_urls,
            people_evidence,
            source_urls
        ) = process_pages(
            pages
        )

    except Exception as exc:

        print(
            f"[ERROR] Extraction failed: {exc}"
        )

        website_text = ""
        emails = []
        linkedin_urls = []
        people_evidence = []
        source_urls = []

    print(
        f"Emails extracted: {len(emails)}"
    )

    print(
        f"LinkedIn URLs extracted: "
        f"{len(linkedin_urls)}"
    )

    print(
        f"People extracted: "
        f"{len(people_evidence)}"
    )

    print(
        f"Source pages: "
        f"{len(source_urls)}"
    )

    # =========================================================
    # 3. SEARCH FALLBACK
    # =========================================================

    print(
        "\n[3/5] Running external search..."
    )

    try:

        search_evidence = external_search(
            domain=domain,
            people=people_evidence
        )

    except Exception as exc:

        print(
            f"[WARNING] Search failed: {exc}"
        )

        search_evidence = []

    print(
        f"External results: "
        f"{len(search_evidence)}"
    )

    # =========================================================
    # 4. LLM
    # =========================================================

    print(
        "\n[4/5] Running Groq analysis..."
    )

    try:

        analysis = analyze_company(
            domain=domain,
            website_text=website_text,
            emails=emails,
            linkedin_urls=linkedin_urls,
            people_evidence=people_evidence,
            source_urls=source_urls,
            search_evidence=search_evidence
        )

    except Exception as exc:

        print(
            f"[ERROR] Groq analysis failed: "
            f"{exc}"
        )

        analysis = {}

    if not isinstance(
        analysis,
        dict
    ):
        analysis = {}

    # =========================================================
    # 5. MERGE WITHOUT LOSING EVIDENCE
    # =========================================================

    print(
        "\n[5/5] Merging deterministic + AI results..."
    )

    analysis["company_name"] = (
        analysis.get(
            "company_name"
        )
        or domain
    )

    analysis["team"] = _merge_team(
        analysis.get(
            "team",
            []
        ),
        people_evidence
    )

    analysis["emails"] = _merge_emails(
        analysis.get(
            "emails",
            []
        ),
        emails
    )

    analysis["linkedin_urls"] = _merge_strings(
        linkedin_urls,
        analysis.get(
            "linkedin_urls",
            []
        )
    )

    analysis["source_urls"] = _merge_strings(
        source_urls,
        analysis.get(
            "source_urls",
            []
        )
    )

    analysis.setdefault(
        "overview",
        ""
    )

    analysis.setdefault(
        "industry",
        ""
    )

    analysis.setdefault(
        "icp",
        []
    )

    analysis.setdefault(
        "confidence",
        0.0
    )

    analysis.setdefault(
        "usage",
        {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0
        }
    )

    print(
        "\n========== FINAL =========="
    )

    print(
        f"Team members: "
        f"{len(analysis['team'])}"
    )

    print(
        f"Emails: "
        f"{len(analysis['emails'])}"
    )

    print(
        f"LinkedIn URLs: "
        f"{len(analysis['linkedin_urls'])}"
    )

    print(
        f"Source URLs: "
        f"{len(analysis['source_urls'])}"
    )

    usage = analysis["usage"]

    print(
        f"Total tokens: "
        f"{usage.get('total_tokens', 0)}"
    )

    print(
        f"Estimated cost: "
        f"${usage.get('estimated_cost_usd', 0):.9f}"
    )

    print(
        "=========================="
    )

    return analysis