import re
from typing import Dict, Set
from urllib.parse import urldefrag, urljoin, urlparse

from playwright.sync_api import sync_playwright


HIGH_VALUE_KEYWORDS = {
    "about": 120,
    "about-us": 120,
    "company": 115,
    "team": 125,
    "leadership": 125,
    "management": 120,
    "founder": 125,
    "founders": 125,
    "people": 120,
    "executive": 120,

    "press": 115,
    "press-media": 120,
    "media": 110,
    "newsroom": 110,

    "contact": 125,
    "contact-us": 130,
    "contact-sales": 130,
    "sales": 120,

    "careers": 90,
    "pricing": 90,
    "security": 80,
    "customers": 80,
    "customer-stories": 80,
    "case-studies": 78,
    "solutions": 75,
    "product": 70,
    "platform": 70,
}


LOW_VALUE_PATTERNS = {
    "/workspace/": -100,
    "/workspaces/": -100,
    "/collection/": -100,
    "/collections/": -100,
    "/request/": -110,
    "/requests/": -110,
    "/folder/": -90,
    "/folders/": -90,
    "/environment/": -90,
    "/mock-server/": -90,
    "/user/": -90,
    "/users/": -90,
    "/incontact/": -100,
    "/api-network/": -80,
}


IGNORED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".ico", ".css", ".js", ".mjs", ".map",
    ".zip", ".rar", ".7z",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".xml", ".json",
}


def normalize_domain(domain: str) -> str:
    domain = domain.strip()

    if not domain:
        raise ValueError("Domain cannot be empty.")

    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain

    parsed = urlparse(domain)

    hostname = (
        parsed.netloc or parsed.path
    ).lower().split(":")[0]

    if hostname.startswith("www."):
        hostname = hostname[4:]

    return hostname


def build_base_url(domain: str) -> str:
    return f"https://{normalize_domain(domain)}"


def normalize_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None

    href = href.strip()

    if href.startswith((
        "#", "mailto:", "tel:", "javascript:", "data:"
    )):
        return None

    try:
        absolute = urljoin(base_url, href)
        absolute, _ = urldefrag(absolute)

        parsed = urlparse(absolute)

        if parsed.scheme not in {"http", "https"}:
            return None

        if not parsed.netloc:
            return None

        hostname = parsed.netloc.lower().split(":")[0]

        if hostname.startswith("www."):
            hostname = hostname[4:]

        path = parsed.path or "/"

        if path != "/":
            path = path.rstrip("/")

        result = f"https://{hostname}{path}"

        if parsed.query:
            result += "?" + parsed.query

        return result

    except Exception:
        return None


def is_same_domain(
    base_url: str,
    target_url: str
) -> bool:

    base = normalize_domain(base_url)
    target = normalize_domain(target_url)

    return (
        target == base
        or target.endswith("." + base)
    )


def is_html_candidate(url: str) -> bool:

    path = urlparse(url).path.lower()

    return not path.endswith(
        tuple(IGNORED_EXTENSIONS)
    )


def score_url(
    url: str,
    anchor_text: str = ""
) -> int:

    parsed = urlparse(url)

    path = parsed.path.lower()
    anchor = (anchor_text or "").lower()

    score = 10

    for keyword, weight in HIGH_VALUE_KEYWORDS.items():
        if keyword in path:
            score = max(score, weight)

        if keyword in anchor:
            score = max(score, weight - 5)

    for pattern, penalty in LOW_VALUE_PATTERNS.items():
        if pattern in path:
            score += penalty

    # Penalize very deep URLs because they are often
    # content artifacts rather than corporate pages.
    depth = len([
        part for part in path.split("/")
        if part
    ])

    if depth > 4:
        score -= (depth - 4) * 5

    # Queries often represent product variants/tracking pages.
    if parsed.query:
        score -= 3

    return max(score, 1)


def discover_links(
    page,
    current_url: str
) -> Dict[str, int]:

    discovered = {}

    try:
        anchors = page.locator("a[href]").all()

        for anchor in anchors:
            try:
                href = anchor.get_attribute("href")

                url = normalize_url(
                    current_url,
                    href
                )

                if not url:
                    continue

                if not is_same_domain(
                    current_url,
                    url
                ):
                    continue

                if not is_html_candidate(url):
                    continue

                try:
                    anchor_text = anchor.inner_text(
                        timeout=1000
                    )
                except Exception:
                    anchor_text = ""

                priority = score_url(
                    url,
                    anchor_text
                )

                discovered[url] = max(
                    discovered.get(url, 0),
                    priority
                )

            except Exception:
                continue

    except Exception:
        pass

    return discovered


def extract_sitemap_urls(
    xml_text: str
) -> Set[str]:

    return {
        item.strip()
        for item in re.findall(
            r"<loc>\s*(.*?)\s*</loc>",
            xml_text,
            re.IGNORECASE
        )
    }


def crawl_sitemap_recursive(
    context,
    sitemap_url: str,
    base_url: str,
    visited_sitemaps: Set[str],
    html_urls: Set[str],
):

    sitemap_url = normalize_url(
        base_url,
        sitemap_url
    )

    if not sitemap_url:
        return

    if sitemap_url in visited_sitemaps:
        return

    visited_sitemaps.add(sitemap_url)

    try:
        response = context.request.get(
            sitemap_url,
            timeout=20000
        )

        if not response.ok:
            return

        text = response.text()

        for raw_url in extract_sitemap_urls(text):

            url = normalize_url(
                sitemap_url,
                raw_url
            )

            if not url:
                continue

            if not is_same_domain(
                base_url,
                url
            ):
                continue

            path = urlparse(url).path.lower()

            if path.endswith(".xml"):

                crawl_sitemap_recursive(
                    context,
                    url,
                    base_url,
                    visited_sitemaps,
                    html_urls
                )

            elif is_html_candidate(url):

                html_urls.add(url)

    except Exception:
        return


def discover_sitemap_pages(
    context,
    base_url: str
) -> Set[str]:

    html_urls = set()
    visited_sitemaps = set()

    candidates = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/sitemap/sitemap.xml",
    ]

    for candidate in candidates:
        crawl_sitemap_recursive(
            context,
            urljoin(base_url, candidate),
            base_url,
            visited_sitemaps,
            html_urls
        )

    # robots.txt can reveal additional sitemap files.
    try:
        robots_url = urljoin(
            base_url,
            "/robots.txt"
        )

        response = context.request.get(
            robots_url,
            timeout=10000
        )

        if response.ok:
            robots = response.text()

            sitemap_lines = re.findall(
                r"(?im)^\s*Sitemap:\s*(\S+)",
                robots
            )

            for sitemap in sitemap_lines:
                crawl_sitemap_recursive(
                    context,
                    sitemap,
                    base_url,
                    visited_sitemaps,
                    html_urls
                )

    except Exception:
        pass

    return html_urls


def fetch_page(
    context,
    url: str,
    timeout: int = 20000
):

    page = context.new_page()

    try:
        response = page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout
        )

        if response and response.status >= 400:
            return None, None

        try:
            page.wait_for_timeout(1200)
        except Exception:
            pass

        return page.url, page.content()

    except Exception as exc:
        print(
            f"[WARNING] Crawl failed: "
            f"{url} -> {exc}"
        )

        return None, None

    finally:
        try:
            page.close()
        except Exception:
            pass


def crawl_website(
    domain: str,
    max_pages: int = 50
) -> Dict[str, str]:

    base_url = build_base_url(domain)

    pages: Dict[str, str] = {}
    visited: Set[str] = set()
    pending: Dict[str, int] = {}

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
            ),
            viewport={
                "width": 1440,
                "height": 900
            },
            ignore_https_errors=True
        )

        context.set_default_navigation_timeout(
            20000
        )

        try:

            print(
                f"[INFO] Starting crawl: "
                f"{base_url}"
            )

            # ------------------------------------------
            # Homepage
            # ------------------------------------------

            final_url, homepage = fetch_page(
                context,
                base_url
            )

            if not homepage:
                return pages

            homepage_url = (
                normalize_url(
                    base_url,
                    final_url
                )
                or base_url
            )

            pages[homepage_url] = homepage
            visited.add(homepage_url)

            # ------------------------------------------
            # Homepage navigation
            # ------------------------------------------

            page = context.new_page()

            try:
                page.goto(
                    homepage_url,
                    wait_until="domcontentloaded",
                    timeout=20000
                )

                page.wait_for_timeout(800)

                links = discover_links(
                    page,
                    homepage_url
                )

            except Exception:
                links = {}

            finally:
                try:
                    page.close()
                except Exception:
                    pass

            print(
                f"[INFO] Homepage discovered "
                f"{len(links)} HTML links."
            )

            for url, priority in links.items():
                if url not in visited:
                    pending[url] = max(
                        pending.get(url, 0),
                        priority
                    )

            # ------------------------------------------
            # Sitemap discovery
            # ------------------------------------------

            sitemap_pages = discover_sitemap_pages(
                context,
                base_url
            )

            print(
                f"[INFO] Sitemap HTML URLs discovered: "
                f"{len(sitemap_pages)}"
            )

            for url in sitemap_pages:

                if url in visited:
                    continue

                pending[url] = max(
                    pending.get(url, 0),
                    score_url(url)
                )

            # ------------------------------------------
            # Crawl
            # ------------------------------------------

            while (
                pending
                and len(pages) < max_pages
            ):

                url, priority = max(
                    pending.items(),
                    key=lambda item: (
                        item[1],
                        -len(item[0])
                    )
                )

                del pending[url]

                if url in visited:
                    continue

                visited.add(url)

                print(
                    f"[INFO] Crawling: "
                    f"{url} "
                    f"(priority={priority})"
                )

                final_url, html = fetch_page(
                    context,
                    url
                )

                if not html:
                    continue

                normalized = (
                    normalize_url(
                        base_url,
                        final_url
                    )
                    or url
                )

                if not is_same_domain(
                    base_url,
                    normalized
                ):
                    continue

                if not is_html_candidate(normalized):
                    continue

                pages[normalized] = html

                # ------------------------------------------
                # Discover more pages
                # ------------------------------------------

                page = context.new_page()

                try:
                    page.goto(
                        normalized,
                        wait_until="domcontentloaded",
                        timeout=20000
                    )

                    page.wait_for_timeout(600)

                    more_links = discover_links(
                        page,
                        normalized
                    )

                except Exception:
                    more_links = {}

                finally:
                    try:
                        page.close()
                    except Exception:
                        pass

                for new_url, new_priority in more_links.items():

                    if new_url not in visited:

                        pending[new_url] = max(
                            pending.get(new_url, 0),
                            new_priority
                        )

            print(
                f"[INFO] Crawl complete. "
                f"HTML pages: {len(pages)}"
            )

            return pages

        finally:

            try:
                context.close()
            except Exception:
                pass

            try:
                browser.close()
            except Exception:
                pass