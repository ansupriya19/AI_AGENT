import re
import html as html_module
from typing import Dict, List

from bs4 import BeautifulSoup


EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"


def clean_html(html: str) -> str:
    """
    Remove unnecessary HTML elements and return clean text.
    """

    soup = BeautifulSoup(html, "html.parser")

    # Remove elements that usually contain non-useful content
    for element in soup(
        ["script", "style", "svg", "noscript", "iframe", "canvas"]
    ):
        element.decompose()

    # Remove common navigation and footer boilerplate
    for element in soup(["nav", "footer"]):
        element.decompose()

    # Extract visible text
    text = soup.get_text(separator=" ", strip=True)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Limit page text to avoid sending unnecessary content to the LLM
    MAX_TEXT_LENGTH = 12000

    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + " ..."

    return text.strip()


def extract_emails(html: str) -> List[str]:
    """
    Extract public email addresses from HTML.

    Decodes HTML entities and removes malformed email artifacts.
    """

    # Decode HTML entities such as &gt; and &#62;
    decoded_html = html_module.unescape(html)

    emails = re.findall(
        EMAIL_PATTERN,
        decoded_html,
    )

    cleaned_emails = []

    for email in emails:

        # Remove obvious HTML artifacts
        email = email.strip(" <>\"'")

        # Ignore malformed encoded fragments
        if email.startswith("u003e"):
            email = email[5:]

        if email.startswith("003e"):
            email = email[4:]

        if email and email not in cleaned_emails:
            cleaned_emails.append(email)

    return cleaned_emails


def extract_linkedin_urls(html: str) -> List[str]:
    """
    Extract LinkedIn profile/company URLs from HTML.
    """

    soup = BeautifulSoup(html, "html.parser")

    linkedin_urls = []

    for link in soup.find_all("a", href=True):

        href = link["href"]

        if "linkedin.com/" in href.lower():
            linkedin_urls.append(href)

    # Remove duplicates
    return list(dict.fromkeys(linkedin_urls))


def process_pages(pages: Dict[str, str]) -> Dict[str, object]:
    """
    Process all crawled pages and combine their useful information.
    """

    combined_text = []
    all_emails = []
    all_linkedin_urls = []

    for url, html in pages.items():

        # Clean page text
        text = clean_html(html)

        if text:
            combined_text.append(
                f"\nSOURCE URL: {url}\n{text}"
            )

        # Extract emails
        emails = extract_emails(html)

        for email in emails:

            if email not in all_emails:
                all_emails.append(email)

        # Extract LinkedIn URLs
        linkedin_urls = extract_linkedin_urls(html)

        for linkedin_url in linkedin_urls:

            if linkedin_url not in all_linkedin_urls:
                all_linkedin_urls.append(linkedin_url)

    return {
        "clean_text": "\n".join(combined_text),
        "contact_emails": all_emails,
        "linkedin_urls": all_linkedin_urls,
    }