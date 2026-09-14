"""
Context Pre-Processing & Token Optimization Engine (Step 2)
Strips raw HTML trees, boilerplates, styles, SVGs, and scripts.
Extracts high-signal text, emails, meta tags, and structured DOM signals to minimize LLM token spend.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup, Comment


# Regular expressions for email and LinkedIn extraction
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    re.IGNORECASE
)

LINKEDIN_COMPANY_REGEX = re.compile(
    r"https?://(?:www\.)?linkedin\.com/company/[a-zA-Z0-9_.-]+",
    re.IGNORECASE
)

LINKEDIN_PERSONAL_REGEX = re.compile(
    r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_.-]+",
    re.IGNORECASE
)

# Common noisy extensions and blacklisted emails (e.g., png, woff, example.com)
INVALID_EMAIL_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js", ".woff", ".woff2"
)


class ContentExtractor:
    """Pre-processes raw HTML pages into optimized, clean text and extracted metadata."""

    @staticmethod
    def extract_emails_and_links(html: str) -> Tuple[List[str], Optional[str], List[str]]:
        """
        Extracts verified contact emails, company LinkedIn URL, and personal LinkedIn URLs directly from HTML.
        """
        emails: Set[str] = set()
        personal_linkedins: Set[str] = set()
        company_linkedin: Optional[str] = None

        soup = BeautifulSoup(html, "html.parser")

        # 1. Search mailto: links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if href.lower().startswith("mailto:"):
                clean_email = href.split("?")[0].replace("mailto:", "").strip()
                if EMAIL_REGEX.match(clean_email):
                    emails.add(clean_email.lower())
            
            # Check LinkedIn links in anchor tags
            if "linkedin.com/company" in href:
                match = LINKEDIN_COMPANY_REGEX.search(href)
                if match and not company_linkedin:
                    company_linkedin = match.group(0).rstrip("/")
            elif "linkedin.com/in/" in href:
                match = LINKEDIN_PERSONAL_REGEX.search(href)
                if match:
                    personal_linkedins.add(match.group(0).rstrip("/"))

        # 2. Search regex across text
        text = soup.get_text(separator=" ")
        for email in EMAIL_REGEX.findall(text):
            email_lower = email.lower().strip()
            if not any(email_lower.endswith(ext) for ext in INVALID_EMAIL_EXTENSIONS):
                if not any(skip in email_lower for skip in ["sentry", "wixpress", "example.com", "schema.org"]):
                    emails.add(email_lower)

        # Also search raw HTML for company LinkedIn if not in anchors
        if not company_linkedin:
            comp_match = LINKEDIN_COMPANY_REGEX.search(html)
            if comp_match:
                company_linkedin = comp_match.group(0).rstrip("/")

        return sorted(list(emails)), company_linkedin, sorted(list(personal_linkedins))

    @staticmethod
    def clean_html_to_markdown(html: str, page_title: str = "") -> str:
        """
        Strips away scripts, style tags, navigation boilerplates, SVGs, and CSS.
        Retains semantic headings, lists, and paragraphs formatted for low-token LLM ingestion.
        """
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        # Remove irrelevant and heavy DOM elements
        for element in soup([
            "script", "style", "svg", "noscript", "iframe", "header", "footer",
            "nav", "form", "button", "symbol", "canvas", "video", "audio"
        ]):
            element.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Extract title and meta descriptions
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        # Prioritize key content containers if present
        main_content = soup.find("main") or soup.find("article") or soup.find("body") or soup

        # Extract structured text chunks
        lines: List[str] = []
        if page_title:
            lines.append(f"### Page: {page_title}")
        if meta_desc:
            lines.append(f"**Meta Description**: {meta_desc}")

        for elem in main_content.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            text = elem.get_text(separator=" ", strip=True)
            if not text or len(text) < 4:
                continue

            # Skip common cookie consent and disclaimer text
            lower_text = text.lower()
            if any(junk in lower_text for junk in [
                "cookie policy", "accept all cookies", "all rights reserved",
                "privacy preferences", "terms of use", "manage preferences"
            ]):
                continue

            tag_name = elem.name
            if tag_name == "h1":
                lines.append(f"\n# {text}")
            elif tag_name == "h2":
                lines.append(f"\n## {text}")
            elif tag_name in ["h3", "h4"]:
                lines.append(f"\n### {text}")
            elif tag_name == "li":
                lines.append(f"- {text}")
            else:
                lines.append(text)

        cleaned_text = "\n".join(lines)
        # Collapse multiple blank lines
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()
        return cleaned_text

    @classmethod
    def process_crawled_pages(
        cls,
        domain: str,
        pages_dict: Dict[str, str]
    ) -> Dict:
        """
        Combines and optimizes content from multiple crawled subpages (home, about, team, pricing, contact).
        Limits total token footprint while preserving maximal semantic context.
        """
        all_emails: Set[str] = set()
        all_personal_linkedins: Set[str] = set()
        company_linkedin: Optional[str] = None
        cleaned_sections: List[str] = []

        total_raw_chars = 0

        for url_or_path, html in pages_dict.items():
            total_raw_chars += len(html)
            # Extract emails & LinkedIn URLs
            page_emails, comp_li, pers_li = cls.extract_emails_and_links(html)
            all_emails.update(page_emails)
            all_personal_linkedins.update(pers_li)
            if comp_li and not company_linkedin:
                company_linkedin = comp_li

            # Clean content
            cleaned = cls.clean_html_to_markdown(html, page_title=url_or_path)
            if cleaned:
                # Cap each subpage to avoid token overflow
                capped = cleaned[:3500]
                cleaned_sections.append(f"--- SOURCE: {url_or_path} ---\n{capped}\n")

        aggregated_text = "\n".join(cleaned_sections)
        # Final safety token truncation (~12,000 characters ≈ 3,000 tokens)
        final_prompt_context = aggregated_text[:14000]

        compression_ratio = round(
            (1 - (len(final_prompt_context) / max(total_raw_chars, 1))) * 100, 1
        )

        return {
            "domain": domain,
            "prompt_context": final_prompt_context,
            "extracted_emails": sorted(list(all_emails)),
            "company_linkedin": company_linkedin,
            "personal_linkedins": sorted(list(all_personal_linkedins)),
            "raw_chars": total_raw_chars,
            "optimized_chars": len(final_prompt_context),
            "compression_ratio_pct": compression_ratio,
        }
