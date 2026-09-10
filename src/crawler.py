from typing import Dict
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright


RELEVANT_KEYWORDS = [
    "about",
    "team",
    "company",
    "contact",
    "pricing",
    "leadership",
]


def is_same_domain(base_url: str, url: str) -> bool:
    """Check whether a URL belongs to the same domain."""

    base_domain = urlparse(base_url).netloc
    target_domain = urlparse(url).netloc

    return base_domain == target_domain


def is_relevant_url(url: str) -> bool:
    """Check whether a URL looks relevant for company intelligence."""

    path = urlparse(url).path.lower()

    return any(
        keyword in path
        for keyword in RELEVANT_KEYWORDS
    )


def crawl_website(
    domain: str,
    max_pages: int = 7
) -> Dict[str, str]:
    """
    Crawl a company's public website.

    Starts with the homepage and discovers relevant
    internal links.

    Handles timeouts, 404s, and other page failures
    without crashing the pipeline.
    """

    base_url = f"https://{domain}"

    pages: Dict[str, str] = {}

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        # -------------------------------------------------
        # STEP 1: Crawl homepage
        # -------------------------------------------------

        try:
            response = page.goto(
                base_url,
                wait_until="domcontentloaded",
                timeout=20000,
            )

            page.wait_for_timeout(2000)

            if response and response.status == 404:

                print(
                    f"[INFO] Homepage returned 404: "
                    f"{base_url}"
                )

            else:

                pages[base_url] = page.content()

        except Exception as error:

            print(
                f"[WARNING] Homepage failed for "
                f"{domain}: {error}"
            )

        # -------------------------------------------------
        # STEP 2: Discover relevant internal links
        # -------------------------------------------------

        discovered_urls = []

        try:

            links = page.locator("a").all()

            for link in links:

                try:

                    href = link.get_attribute("href")

                    if not href:
                        continue

                    # Convert relative URL to absolute URL
                    absolute_url = urljoin(
                        base_url,
                        href
                    )

                    # Remove fragments
                    absolute_url = (
                        absolute_url.split("#")[0]
                    )

                    # Only same-domain URLs
                    if not is_same_domain(
                        base_url,
                        absolute_url
                    ):
                        continue

                    # Only relevant pages
                    if not is_relevant_url(
                        absolute_url
                    ):
                        continue

                    # Avoid duplicates
                    if absolute_url not in discovered_urls:

                        discovered_urls.append(
                            absolute_url
                        )

                except Exception:

                    continue

        except Exception as error:

            print(
                f"[WARNING] Link discovery failed: "
                f"{error}"
            )

        print(
            f"[INFO] Discovered "
            f"{len(discovered_urls)} relevant link(s)."
        )

        # -------------------------------------------------
        # STEP 3: Crawl discovered pages
        # -------------------------------------------------

        for url in discovered_urls:

            if len(pages) >= max_pages:
                break

            if url in pages:
                continue

            try:

                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=15000,
                )

                if response and response.status == 404:

                    print(
                        f"[INFO] 404: {url}"
                    )

                    continue

                page.wait_for_timeout(1000)

                pages[url] = page.content()

            except Exception as error:

                print(
                    f"[WARNING] Failed: "
                    f"{url} -> {error}"
                )

        # -------------------------------------------------
        # STEP 4: Close browser
        # -------------------------------------------------

        context.close()
        browser.close()

    return pages