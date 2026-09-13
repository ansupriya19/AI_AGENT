import re
from typing import Dict, List, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

LINKEDIN_PATTERN = re.compile(
    r"https?://(?:www\.)?linkedin\.com/"
    r"(?:in|company)/[A-Za-z0-9._/?=&%-]+",
    re.IGNORECASE,
)

ROLE_PATTERNS = [
    r"\bCEO\b",
    r"\bCTO\b",
    r"\bCFO\b",
    r"\bCOO\b",
    r"\bCPO\b",
    r"\bCMO\b",
    r"\bCISO\b",
    r"\bChief Executive Officer\b",
    r"\bChief Technology Officer\b",
    r"\bChief Financial Officer\b",
    r"\bChief Operating Officer\b",
    r"\bChief Product Officer\b",
    r"\bChief Marketing Officer\b",
    r"\bProduct Architect\b",
    r"\bFounder\b",
    r"\bCo-Founder\b",
    r"\bCofounder\b",
    r"\bPresident\b",
    r"\bVice President\b",
    r"\bVP\b",
    r"\bDirector\b",
    r"\bHead of [A-Za-z &/-]+\b",
    r"\bGeneral Manager\b",
    r"\bManaging Director\b",
]

ROLE_REGEX = re.compile(
    "|".join(ROLE_PATTERNS),
    re.IGNORECASE,
)


def normalize_email(email: str) -> str:
    email = email.strip().lower()

    # Remove common HTML/entity garbage
    email = email.replace(
        "u003e",
        ""
    )

    email = email.replace(
        "u003c",
        ""
    )

    email = email.replace(
        "&gt;",
        ""
    )

    email = email.replace(
        "&lt;",
        ""
    )

    return email


def normalize_linkedin_url(url: str) -> str:

    if not url:
        return ""

    if url.startswith("//"):
        url = "https:" + url

    if not url.startswith(
        ("http://", "https://")
    ):
        url = "https://" + url

    parsed = urlparse(url)

    if "linkedin.com" not in (
        parsed.netloc or ""
    ).lower():
        return ""

    path = parsed.path.rstrip("/")

    return (
        "https://www.linkedin.com"
        + path
    )


def clean_text(html: str) -> str:

    soup = BeautifulSoup(
        html,
        "lxml"
    )

    for element in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "canvas",
            "iframe",
        ]
    ):
        element.decompose()

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def extract_emails(
    html: str
) -> List[str]:

    soup = BeautifulSoup(
        html,
        "lxml"
    )

    emails = set()

    for match in EMAIL_PATTERN.findall(
        html
    ):
        email = normalize_email(
            match
        )

        if EMAIL_PATTERN.fullmatch(
            email
        ):
            emails.add(email)

    for anchor in soup.find_all(
        "a",
        href=True
    ):

        href = anchor.get(
            "href",
            ""
        ).strip()

        if href.lower().startswith(
            "mailto:"
        ):

            email = href[
                7:
            ].split("?")[0]

            email = normalize_email(
                email
            )

            if EMAIL_PATTERN.fullmatch(
                email
            ):
                emails.add(email)

    return sorted(emails)


def extract_linkedin_urls(
    html: str,
    base_url: str
) -> List[str]:

    soup = BeautifulSoup(
        html,
        "lxml"
    )

    urls = set()

    for match in LINKEDIN_PATTERN.findall(
        html
    ):

        normalized = normalize_linkedin_url(
            match
        )

        if normalized:
            urls.add(normalized)

    for anchor in soup.find_all(
        "a",
        href=True
    ):

        href = anchor.get(
            "href",
            ""
        ).strip()

        absolute = urljoin(
            base_url,
            href
        )

        normalized = normalize_linkedin_url(
            absolute
        )

        if normalized:
            urls.add(normalized)

    return sorted(urls)


def _looks_like_name(
    text: str
) -> bool:

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    if not text:
        return False

    if len(text) < 4 or len(text) > 100:
        return False

    words = text.split()

    if not 2 <= len(words) <= 6:
        return False

    bad_phrases = {
        "learn more",
        "read more",
        "view profile",
        "connect with",
        "follow us",
        "contact us",
        "our team",
        "linkedin",
        "click here",
    }

    if text.lower() in bad_phrases:
        return False

    return True


def _extract_role(
    text: str
) -> str:

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    # First try the complete professional title
    matches = ROLE_REGEX.findall(
        text
    )

    if not matches:
        return ""

    # Preserve the best descriptive role.
    roles = []

    for match in matches:

        role = (
            match
            if isinstance(match, str)
            else match[0]
        )

        role = re.sub(
            r"\s+",
            " ",
            role
        ).strip()

        if role:
            roles.append(role)

    if not roles:
        return ""

    # Prefer combined Founder roles
    for role in roles:

        if (
            "founder" in role.lower()
            and (
                "ceo" in role.lower()
                or "cto" in role.lower()
                or "architect" in role.lower()
            )
        ):
            return role

    # Otherwise return first match
    return roles[0]


def _extract_person_name(
    anchor_text: str,
    context_text: str
) -> str:

    anchor_text = re.sub(
        r"\s+",
        " ",
        anchor_text
    ).strip()

    context_text = re.sub(
        r"\s+",
        " ",
        context_text
    ).strip()

    if _looks_like_name(
        anchor_text
    ):
        return anchor_text

    # Look for:
    # Name, Role
    # Name - Role
    pattern = re.compile(
        r"\b("
        r"[A-Z][A-Za-z.'-]+"
        r"(?:\s+[A-Z][A-Za-z.'-]+){1,5}"
        r")"
        r"\s*(?:,|-|–|—)\s*"
        r"(?:CEO|CTO|CFO|COO|CPO|"
        r"Founder|Co-Founder|Cofounder|"
        r"Product Architect|President|"
        r"Director|VP|Head|Chief)",
        re.IGNORECASE
    )

    match = pattern.search(
        context_text
    )

    if match:

        candidate = match.group(
            1
        ).strip()

        if _looks_like_name(
            candidate
        ):
            return candidate

    return ""


def _get_context(
    anchor
) -> str:

    pieces = []

    # Anchor
    anchor_text = anchor.get_text(
        " ",
        strip=True
    )

    if anchor_text:
        pieces.append(
            anchor_text
        )

    # Parent
    parent = anchor.parent

    if parent:

        text = parent.get_text(
            " ",
            strip=True
        )

        if text:
            pieces.append(text)

    # Grandparent
    if parent and parent.parent:

        text = parent.parent.get_text(
            " ",
            strip=True
        )

        if text:
            pieces.append(text)

    # Nearby previous/next elements
    current = anchor

    for _ in range(3):

        previous = (
            current.find_previous(
                string=True
            )
        )

        if previous:
            pieces.append(
                str(previous)
            )

        current = previous.parent \
            if getattr(
                previous,
                "parent",
                None
            ) else None

        if current is None:
            break

    combined = " ".join(
        pieces
    )

    combined = re.sub(
        r"\s+",
        " ",
        combined
    ).strip()

    return combined


def extract_people_evidence(
    html: str,
    page_url: str
) -> List[dict]:

    soup = BeautifulSoup(
        html,
        "lxml"
    )

    people = []

    for anchor in soup.find_all(
        "a",
        href=True
    ):

        href = anchor.get(
            "href",
            ""
        ).strip()

        if "linkedin.com/in/" not in (
            href.lower()
        ):
            continue

        linkedin_url = normalize_linkedin_url(
            urljoin(
                page_url,
                href
            )
        )

        if not linkedin_url:
            continue

        anchor_text = re.sub(
            r"\s+",
            " ",
            anchor.get_text(
                " ",
                strip=True
            )
        ).strip()

        context = _get_context(
            anchor
        )

        name = _extract_person_name(
            anchor_text,
            context
        )

        role = _extract_role(
            context
        )

        # Second pass: examine nearby headings,
        # cards and text around the link.
        if not role:

            parent = anchor.parent

            for _ in range(4):

                if not parent:
                    break

                block = parent.get_text(
                    " ",
                    strip=True
                )

                role = _extract_role(
                    block
                )

                if role:
                    break

                parent = parent.parent

        if not name:

            name = _extract_person_name(
                anchor_text,
                context
            )

        people.append(
            {
                "name": name,
                "role": role,
                "linkedin_url": linkedin_url,
                "source_url": page_url,
            }
        )

    return people


def _deduplicate_people(
    people: List[dict]
) -> List[dict]:

    result = []
    seen = set()

    for person in people:

        linkedin = str(
            person.get(
                "linkedin_url"
            )
            or ""
        ).lower()

        name = str(
            person.get(
                "name"
            )
            or ""
        ).lower()

        key = (
            linkedin,
            name
        )

        if key in seen:
            continue

        seen.add(key)

        result.append(
            person
        )

    return result


def _deduplicate_urls(
    urls
) -> List[str]:

    result = []
    seen = set()

    for url in urls:

        url = str(
            url
        ).strip()

        if not url:
            continue

        key = url.rstrip(
            "/"
        ).lower()

        if key in seen:
            continue

        seen.add(key)

        result.append(
            url
        )

    return sorted(
        result
    )


def process_pages(
    pages: Dict[str, str]
) -> Tuple[
    str,
    List[str],
    List[str],
    List[dict],
    List[str],
]:

    if not pages:

        return (
            "",
            [],
            [],
            [],
            []
        )

    all_text = []
    all_emails = set()
    all_linkedin = set()
    all_people = []
    source_urls = []

    for page_url, html in pages.items():

        if not html:
            continue

        source_urls.append(
            page_url
        )

        text = clean_text(
            html
        )

        if text:
            all_text.append(
                f"SOURCE: {page_url}\n"
                f"{text}"
            )

        for email in extract_emails(
            html
        ):
            all_emails.add(
                email
            )

        for linkedin in extract_linkedin_urls(
            html,
            page_url
        ):
            all_linkedin.add(
                linkedin
            )

        people = extract_people_evidence(
            html,
            page_url
        )

        all_people.extend(
            people
        )

    all_people = _deduplicate_people(
        all_people
    )

    source_urls = _deduplicate_urls(
        source_urls
    )

    combined_text = "\n\n".join(
        all_text
    )

    # Keep enough website evidence for
    # names, leadership and company intelligence.
    max_text_chars = 16000

    combined_text = combined_text[
        :max_text_chars
    ]

    return (
        combined_text,
        sorted(all_emails),
        sorted(all_linkedin),
        all_people,
        source_urls,
    )