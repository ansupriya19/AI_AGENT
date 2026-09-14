import re
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse
import httpx
PRIORITY_KEYWORDS = ['support', 'help', 'chat', 'chat-with-us', 'talk-to-us', 'talk-to-sales', 'contact', 'contact-us', 'sales', 'demo', 'book-a-demo', 'reach-us', 'about', 'team', 'company', 'leadership', 'people', 'founders', 'pricing', 'plans', 'product', 'enterprise', 'our-story', 'customer-support']
ANCHOR_TEXT_KEYWORDS = ['support', 'help', 'help center', 'chat', 'chat with us', 'talk to us', 'talk to sales', 'contact', 'contact us', 'contact sales', 'get in touch', 'sales', 'demo', 'about', 'about us', 'team', 'leadership', 'our team', 'pricing', 'plans', 'reach us', 'customer support']
DEFAULT_HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.9', 'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Ch-Ua-Platform': '"macOS"', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none', 'Sec-Fetch-User': '?1', 'Upgrade-Insecure-Requests': '1'}

class WebCrawler:

    def __init__(self, timeout: float=12.0, max_subpages: int=5):
        self.timeout = timeout
        self.max_subpages = max_subpages

    def normalize_url(self, domain: str) -> str:
        cleaned = domain.strip().lower()
        if not cleaned.startswith('http://') and (not cleaned.startswith('https://')):
            return f'https://{cleaned}'
        return cleaned

    def discover_subpage_links(self, base_url: str, html: str) -> List[str]:
        discovered: Set[str] = set()
        parsed_base = urlparse(base_url)
        base_netloc = parsed_base.netloc.replace('www.', '')
        root_domain = '.'.join(base_netloc.split('.')[-2:]) if '.' in base_netloc else base_netloc
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(html, 'html.parser')
            anchor_elements = soup.find_all('a', href=True)
        except Exception:
            anchor_elements = []
        support_chat_links: List[str] = []
        contact_sales_links: List[str] = []
        about_team_links: List[str] = []
        pricing_product_links: List[str] = []
        other_priority_links: List[str] = []
        for a in anchor_elements:
            href = a.get('href', '').split('#')[0].split('?')[0].strip()
            if not href or href.startswith(('mailto:', 'tel:', 'javascript:', 'data:')):
                continue
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            cand_netloc = parsed.netloc.replace('www.', '')
            is_company_domain = cand_netloc == base_netloc or cand_netloc.endswith('.' + root_domain)
            if not is_company_domain:
                continue
            path = parsed.path.lower()
            if any((path.endswith(ext) for ext in ['.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.css', '.js', '.ico'])):
                continue
            anchor_text = a.get_text(strip=True).lower()
            aria_label = str(a.get('aria-label', '')).lower()
            combined_desc = f'{path} {anchor_text} {aria_label} {cand_netloc}'
            if any((k in combined_desc for k in ['support', 'help', 'chat', 'chat-with-us', 'live-chat', 'talk-to-us'])):
                if full_url not in support_chat_links:
                    support_chat_links.append(full_url)
            elif any((k in combined_desc for k in ['contact', 'sales', 'demo', 'get in touch', 'reach us'])):
                if full_url not in contact_sales_links:
                    contact_sales_links.append(full_url)
            elif any((k in combined_desc for k in ['about', 'team', 'company', 'leadership', 'people', 'founders'])):
                if full_url not in about_team_links:
                    about_team_links.append(full_url)
            elif any((k in combined_desc for k in ['pricing', 'plans'])):
                if full_url not in pricing_product_links:
                    pricing_product_links.append(full_url)
            elif any((kw in combined_desc for kw in PRIORITY_KEYWORDS)):
                if full_url not in other_priority_links:
                    other_priority_links.append(full_url)
        selected: List[str] = []
        for (lst, limit) in [(support_chat_links, 2), (contact_sales_links, 2), (about_team_links, 2), (pricing_product_links, 1), (other_priority_links, 1)]:
            for u in lst:
                if u not in selected and len(selected) < self.max_subpages:
                    selected.append(u)
        return selected

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
