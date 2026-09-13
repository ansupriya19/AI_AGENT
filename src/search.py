import re
from typing import List, Dict, Any
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def normalize_linkedin_url(url: str) -> str:
    """
    Normalize LinkedIn profile/company URLs.
    """

    if not url:
        return ""

    url = url.strip()

    url = url.split("?")[0]
    url = url.split("#")[0]

    url = url.rstrip("/")

    if url.startswith("//"):
        url = "https:" + url

    if not url.startswith("http"):
        url = "https://" + url

    match = re.search(
        r"https?://(?:www\.)?linkedin\.com/(in|company)/([^/]+)",
        url,
        re.IGNORECASE,
    )

    if not match:
        return ""

    category = match.group(1).lower()
    slug = match.group(2)

    return f"https://www.linkedin.com/{category}/{slug}"


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def _search_google(page, query: str) -> List[Dict[str, str]]:
    results = []

    url = (
        "https://www.google.com/search?q="
        + quote(query)
    )

    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=20000,
        )

        page.wait_for_timeout(1500)

        soup = BeautifulSoup(
            page.content(),
            "html.parser",
        )

        for result in soup.select("div.MjjYud"):

            link = result.select_one("a[href]")

            if not link:
                continue

            href = link.get("href", "")

            if "linkedin.com/" not in href.lower():
                continue

            linkedin_url = normalize_linkedin_url(href)

            if not linkedin_url:
                continue

            title_node = result.select_one("h3")

            title = (
                title_node.get_text(" ", strip=True)
                if title_node
                else ""
            )

            snippet = ""

            for selector in [
                ".VwiC3b",
                ".yXK7lf",
                ".IsZvec",
            ]:
                node = result.select_one(selector)

                if node:
                    snippet = node.get_text(
                        " ",
                        strip=True,
                    )
                    break

            results.append(
                {
                    "query": query,
                    "title": _clean_text(title),
                    "snippet": _clean_text(snippet),
                    "linkedin_url": linkedin_url,
                    "source": "google",
                }
            )

    except Exception:
        pass

    return results


def _search_duckduckgo(
    page,
    query: str,
) -> List[Dict[str, str]]:

    results = []

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=20000,
        )

        page.wait_for_timeout(1500)

        soup = BeautifulSoup(
            page.content(),
            "html.parser",
        )

        for result in soup.select(
            ".result, .web-result"
        ):

            link = result.select_one(
                ".result__a[href], a[href]"
            )

            if not link:
                continue

            href = link.get("href", "")

            if "linkedin.com/" not in href.lower():
                continue

            linkedin_url = normalize_linkedin_url(href)

            if not linkedin_url:
                continue

            title = link.get_text(
                " ",
                strip=True,
            )

            snippet_node = result.select_one(
                ".result__snippet"
            )

            snippet = (
                snippet_node.get_text(
                    " ",
                    strip=True,
                )
                if snippet_node
                else ""
            )

            results.append(
                {
                    "query": query,
                    "title": _clean_text(title),
                    "snippet": _clean_text(snippet),
                    "linkedin_url": linkedin_url,
                    "source": "duckduckgo",
                }
            )

    except Exception:
        pass

    return results


def _build_queries(
    domain: str,
    people: List[dict],
) -> List[str]:

    clean_domain = (
        domain
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
    )

    company_name = (
        clean_domain
        .split(".")[0]
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )

    queries = [
        f'"{company_name}" LinkedIn company',
        f'"{clean_domain}" LinkedIn',
    ]

    # Search for people already detected on the website
    for person in people or []:

        name = str(
            person.get("name") or ""
        ).strip()

        if not name:
            continue

        queries.append(
            f'"{name}" "{company_name}" LinkedIn'
        )

    # Remove duplicates
    final_queries = []
    seen = set()

    for query in queries:

        key = query.lower().strip()

        if key in seen:
            continue

        seen.add(key)
        final_queries.append(query)

    # Prevent excessive external searches
    return final_queries[:12]


def external_search(
    domain: str,
    people: List[dict] | None = None,
) -> List[Dict[str, Any]]:
    """
    External LinkedIn search fallback.

    This is intentionally optional. Website crawling remains
    the primary source of evidence.
    """

    people = people or []

    queries = _build_queries(
        domain,
        people,
    )

    if not queries:
        return []

    all_results = []

    try:
        with sync_playwright() as playwright:

            browser = playwright.chromium.launch(
                headless=True
            )

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/131.0.0.0 "
                    "Safari/537.36"
                )
            )

            page = context.new_page()

            for query in queries:

                # Google first
                google_results = _search_google(
                    page,
                    query,
                )

                all_results.extend(
                    google_results
                )

                # DuckDuckGo fallback
                if not google_results:
                    ddg_results = _search_duckduckgo(
                        page,
                        query,
                    )

                    all_results.extend(
                        ddg_results
                    )

            browser.close()

    except Exception:
        return []

    # Deduplicate results
    final_results = []
    seen = set()

    for result in all_results:

        linkedin_url = normalize_linkedin_url(
            result.get("linkedin_url", "")
        )

        if not linkedin_url:
            continue

        key = (
            linkedin_url.lower(),
            str(
                result.get("query") or ""
            ).lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        result["linkedin_url"] = linkedin_url

        final_results.append(result)

    return final_results