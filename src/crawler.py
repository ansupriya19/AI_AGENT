import re
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

PRIORITY_PATTERNS = [
    r'/(?:company/)?about(?:-[a-z0-9]+)?/?$',
    r'/pricing/?$',
    r'/(?:contact|company/contact)(?:-[a-z0-9]+|/sales)?/?$',
    r'/(?:support|help)/?$',
    r'/careers/?$'
]

EXCLUDED_SEGMENTS = [
    '/customers/', '/case-studies/', '/category/', '/tag/',
    '/author/', '/blog/', '/posts/', '/p/', '/feed/',
    '/wp-content/', '/wp-json/', '/assets/', '/static/'
]

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

class WebCrawler:
    def __init__(self, timeout: float = 12.0, max_subpages: int = 4):
        self.timeout = timeout
        self.max_subpages = max_subpages

    def normalize_url(self, domain: str) -> str:
        cleaned = domain.strip().lower()
        if not cleaned.startswith('http://') and not cleaned.startswith('https://'):
            return f'https://{cleaned}'
        return cleaned

    def discover_subpage_links(self, base_url: str, html: str) -> List[str]:
        parsed_base = urlparse(base_url)
        base_netloc = parsed_base.netloc.replace('www.', '')
        root_domain = '.'.join(base_netloc.split('.')[-2:]) if '.' in base_netloc else base_netloc
        try:
            soup = BeautifulSoup(html, 'html.parser')
            anchor_elements = soup.find_all('a', href=True)
        except Exception:
            anchor_elements = []
        selected_links: List[str] = []
        seen_paths: Set[str] = set()
        for a in anchor_elements:
            href = a.get('href', '').split('#')[0].split('?')[0].strip()
            if not href or href.startswith(('mailto:', 'tel:', 'javascript:', 'data:')):
                continue
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            cand_netloc = parsed.netloc.replace('www.', '')
            if cand_netloc != base_netloc and not cand_netloc.endswith('.' + root_domain):
                continue
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in ['.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.css', '.js', '.ico']):
                continue
            if any(ex in path for ex in EXCLUDED_SEGMENTS):
                continue
            if not any(re.search(pat, path) for pat in PRIORITY_PATTERNS):
                continue
            canonical_path = path.rstrip('/')
            if canonical_path in seen_paths or canonical_path == '':
                continue
            seen_paths.add(canonical_path)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{path}"
            selected_links.append(clean_url)
            if len(selected_links) >= self.max_subpages:
                break
        return selected_links

    def crawl_domain(self, domain: str) -> Tuple[Dict[str, str], List[str]]:
        base_url = self.normalize_url(domain)
        results: Dict[str, str] = {}
        source_urls: List[str] = []
        with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True, verify=False) as client:
            try:
                resp = client.get(base_url)
                if resp.status_code < 400:
                    results[str(resp.url)] = resp.text
                    source_urls.append(str(resp.url))
                    discovered_links = self.discover_subpage_links(str(resp.url), resp.text)
                    for link in discovered_links:
                        if link in results:
                            continue
                        try:
                            sub_resp = client.get(link)
                            if sub_resp.status_code < 400:
                                results[str(sub_resp.url)] = sub_resp.text
                                source_urls.append(str(sub_resp.url))
                        except Exception:
                            continue
            except Exception as e:
                print(f'[Crawler] Warning: Failed to fetch {base_url}: {e}')
        return (results, source_urls)
