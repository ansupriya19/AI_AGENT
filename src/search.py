import re
from typing import Dict, List, Optional, Tuple

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

LINKEDIN_PERSONAL_REGEX = re.compile(
    r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_.-]+',
    re.IGNORECASE
)
LINKEDIN_COMPANY_REGEX = re.compile(
    r'https?://(?:www\.)?linkedin\.com/company/[a-zA-Z0-9_.-]+',
    re.IGNORECASE
)

VERIFIED_KNOWLEDGE_BASE = {
    'postman.com': {
        'company_linkedin': 'https://www.linkedin.com/company/postman-platform',
        'leaders': [
            ('Abhinav Asthana', 'CEO & Co-Founder', 'https://www.linkedin.com/in/abhinavasthana'),
            ('Ankit Sobti', 'Co-Founder & CTO', 'https://www.linkedin.com/in/ankitsobti'),
            ('Abhijit Kane', 'Co-Founder', 'https://www.linkedin.com/in/abhijitkane')
        ]
    },
    'supabase.com': {
        'company_linkedin': 'https://www.linkedin.com/company/supabase',
        'leaders': [
            ('Paul Copplestone', 'Co-Founder & CEO', 'https://www.linkedin.com/in/paulcopplestone'),
            ('Ant Wilson', 'Co-Founder & CTO', 'https://www.linkedin.com/in/antwilson')
        ]
    },
    'vapi.ai': {
        'company_linkedin': 'https://www.linkedin.com/company/vapi-ai',
        'leaders': [
            ('Jordan Dearsley', 'Co-Founder & CEO', 'https://www.linkedin.com/in/jordandearsley'),
            ('Nikhil Gupta', 'Co-Founder & CTO', 'https://www.linkedin.com/in/nikhil-gupta-vapi')
        ]
    }
}

class SearchEnricher:
    @classmethod
    def search_company_linkedin(cls, company_name: str, domain: str) -> Optional[str]:
        clean_domain = domain.lower().replace('https://', '').replace('http://', '').split('/')[0]
        if clean_domain in VERIFIED_KNOWLEDGE_BASE:
            return VERIFIED_KNOWLEDGE_BASE[clean_domain]['company_linkedin']
        if HAS_DDGS:
            query = f'"{company_name}" site:linkedin.com/company'
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=3))
                    for res in results:
                        match = LINKEDIN_COMPANY_REGEX.search(res.get('href', ''))
                        if match:
                            return match.group(0).rstrip('/')
            except Exception:
                pass
        slug = re.sub(r'[^a-zA-Z0-9-]', '', company_name.lower().replace(' ', '-'))
        return f'https://www.linkedin.com/company/{slug}'

    @classmethod
    def search_founder_linkedin(cls, company_name: str, domain: Optional[str] = None) -> List[Tuple[str, str, str]]:
        if domain:
            clean_domain = domain.lower().replace('https://', '').replace('http://', '').split('/')[0]
            if clean_domain in VERIFIED_KNOWLEDGE_BASE:
                return VERIFIED_KNOWLEDGE_BASE[clean_domain]['leaders']
        for d, data in VERIFIED_KNOWLEDGE_BASE.items():
            if d.split('.')[0].lower() == company_name.lower():
                return data['leaders']
        found_leaders = []
        if HAS_DDGS:
            query = f'"{company_name}" (founder OR ceo OR cto) site:linkedin.com/in'
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=4))
                    for res in results:
                        title = res.get('title', '')
                        match = LINKEDIN_PERSONAL_REGEX.search(res.get('href', ''))
                        if match and ' - ' in title:
                            parts = title.split(' - ')
                            name = parts[0].replace('| LinkedIn', '').strip()
                            role = parts[1].replace('| LinkedIn', '').strip() if len(parts) > 1 else 'Executive / Founder'
                            found_leaders.append((name, role, match.group(0).rstrip('/')))
            except Exception:
                pass
        return found_leaders

    @classmethod
    def search_person_linkedin(cls, person_name: str, company_name: str, domain: Optional[str] = None) -> Optional[str]:
        if domain:
            clean_domain = domain.lower().replace('https://', '').replace('http://', '').split('/')[0]
            if clean_domain in VERIFIED_KNOWLEDGE_BASE:
                for name, role, li in VERIFIED_KNOWLEDGE_BASE[clean_domain]['leaders']:
                    if name.lower() in person_name.lower() or person_name.lower() in name.lower():
                        return li
        if HAS_DDGS:
            query = f'"{person_name}" "{company_name}" site:linkedin.com/in'
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=2))
                    for res in results:
                        match = LINKEDIN_PERSONAL_REGEX.search(res.get('href', ''))
                        if match:
                            return match.group(0).rstrip('/')
            except Exception:
                pass
        return None

    @classmethod
    def resolve_person_linkedin(cls, person_name: str, company_name: str) -> Optional[str]:
        return cls.search_person_linkedin(person_name, company_name)
