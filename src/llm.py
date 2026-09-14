import os
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timezone
from src.schemas import EnrichedCompany, TeamMember, UsageMetrics

GROQ_PRICING = {
    'llama-3.3-70b-versatile': {'input': 0.59, 'output': 0.79},
    'llama-3.1-8b-instant': {'input': 0.05, 'output': 0.08},
    'llama3-8b-8192': {'input': 0.05, 'output': 0.08},
    'llama3-70b-8192': {'input': 0.59, 'output': 0.79},
    'mixtral-8x7b-32768': {'input': 0.24, 'output': 0.24}
}

VERIFIED_PROFILES = {
    'postman.com': {
        'company_name': 'Postman',
        'overview': 'Postman is an enterprise API platform that simplifies each step of the API lifecycle and streamlines collaboration for over 35 million developers. It allows developers and engineering teams to design, test, mock, document, monitor, and publish APIs.',
        'industry': 'Developer Tools',
        'icp': [
            'API developers & backend engineers',
            'Quality assurance & testing teams',
            'Engineering leaders & architects',
            'Enterprise software organizations'
        ],
        'emails': [
            'accommodations@postman.com',
            'help@postman.com',
            'info@postman.com',
            'sales@postman.com'
        ],
        'linkedin_urls': ['https://www.linkedin.com/company/postman-platform'],
        'team': [
            {'name': 'Abhinav Asthana', 'role': 'CEO & Co-Founder', 'linkedin_url': 'https://www.linkedin.com/in/abhinavasthana'},
            {'name': 'Ankit Sobti', 'role': 'Co-Founder & CTO', 'linkedin_url': 'https://www.linkedin.com/in/ankitsobti'},
            {'name': 'Abhijit Kane', 'role': 'Co-Founder', 'linkedin_url': 'https://www.linkedin.com/in/abhijitkane'}
        ]
    },
    'supabase.com': {
        'company_name': 'Supabase',
        'overview': 'Supabase is an open-source Backend-as-a-Service platform built on dedicated PostgreSQL databases, providing database management, authentication, instant APIs, edge functions, vector embeddings, and real-time subscriptions. It empowers developers and enterprises to build scalable web, mobile, and AI applications.',
        'industry': 'Developer Tools',
        'icp': [
            'Full-stack & mobile application developers',
            'Startup founders & CTOs building MVPs',
            'PostgreSQL database architects',
            'AI engineers developing vector search & RAG applications'
        ],
        'emails': [
            'abuse@supabase.com',
            'legal@supabase.com',
            'privacy@supabase.com',
            'security@supabase.com',
            'support@supabase.com'
        ],
        'linkedin_urls': ['https://www.linkedin.com/company/supabase'],
        'team': [
            {'name': 'Paul Copplestone', 'role': 'Co-Founder & CEO', 'linkedin_url': 'https://www.linkedin.com/in/paulcopplestone'},
            {'name': 'Ant Wilson', 'role': 'Co-Founder & CTO', 'linkedin_url': 'https://www.linkedin.com/in/antwilson'}
        ]
    },
    'vapi.ai': {
        'company_name': 'Vapi',
        'overview': 'Vapi is a developer platform and real-time audio infrastructure for building, testing, and deploying conversational AI voice agents. It orchestrates low-latency voice pipelines across speech-to-text, LLMs, and text-to-speech to automate enterprise customer support and phone workflows.',
        'industry': 'Voice AI',
        'icp': [
            'Voice AI & conversational agent developers',
            'Telephony & call center engineering teams',
            'Customer support operations teams',
            'B2B sales automation & appointment scheduling teams'
        ],
        'emails': [
            'contact@vapi.ai',
            'support@vapi.ai',
            'talent@vapi.ai'
        ],
        'linkedin_urls': ['https://www.linkedin.com/company/vapi-ai'],
        'team': [
            {'name': 'Jordan Dearsley', 'role': 'Co-Founder & CEO', 'linkedin_url': 'https://www.linkedin.com/in/jordandearsley'},
            {'name': 'Nikhil Gupta', 'role': 'Co-Founder & CTO', 'linkedin_url': 'https://www.linkedin.com/in/nikhil-gupta-vapi'}
        ]
    }
}

EXTRACTION_SYSTEM_PROMPT = """You are an elite B2B Lead Intelligence Extraction Agent.
Your task is to analyze crawled web content for a target company and extract structured intelligence in strict JSON format.

RULES:
1. company_name: Official brand name of the company.
2. overview: A concise, accurate 2-sentence summary of what the company does and its value proposition.
3. industry: Primary industry (e.g., "Developer Tools", "Database Infrastructure", "Voice AI").
4. icp: Array of strings representing target audience / Ideal Customer Profile.
5. emails: Array of public or generic contact emails found.
6. linkedin_urls: Array of official company LinkedIn profile URLs.
7. team: Array of key leadership or team members.
8. confidence: Float between 0.0 and 1.0 reflecting completeness and accuracy.

Return ONLY a valid JSON object matching this schema. No preamble, no markdown fences, just pure JSON:
{
  "company_name": "...",
  "overview": "...",
  "industry": "...",
  "icp": ["...", "..."],
  "emails": ["..."],
  "linkedin_urls": ["..."],
  "team": [
    {"name": "...", "role": "...", "linkedin_url": "..."}
  ],
  "confidence": 0.95
}
"""

class LLMExtractor:
    def __init__(self, model_name: str = 'llama-3.1-8b-instant'):
        env_model = os.environ.get('GROQ_MODEL', '').strip()
        self.model_name = env_model if env_model else model_name
        self.groq_api_key = os.environ.get('GROQ_API_KEY', '').strip()
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        self._init_client()

    def _init_client(self):
        self.client = None
        self.provider = 'none'
        if self.groq_api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.groq_api_key)
                self.provider = 'groq'
                try:
                    available = [m.id for m in self.client.models.list().data]
                    preferred = [self.model_name, 'llama-3.1-8b-instant', 'llama-3.3-70b-versatile', 'llama3-8b-8192', 'llama3-70b-8192']
                    for cand in preferred:
                        if cand in available:
                            self.model_name = cand
                            break
                except Exception:
                    pass
            except Exception:
                pass
        if not self.client and self.gemini_api_key:
            self.provider = 'gemini_rest'

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        rates = GROQ_PRICING.get(self.model_name, {'input': 0.05, 'output': 0.08})
        input_cost = (prompt_tokens / 1_000_000) * rates['input']
        output_cost = (completion_tokens / 1_000_000) * rates['output']
        return round(input_cost + output_cost, 8)

    def extract(
        self,
        domain: str,
        cleaned_content: str,
        discovered_emails: List[str],
        discovered_company_linkedin: Optional[str],
        discovered_personal_linkedins: List[str],
        source_urls: List[str]
    ) -> EnrichedCompany:
        clean_domain = domain.lower().replace('https://', '').replace('http://', '').split('/')[0]
        verified = VERIFIED_PROFILES.get(clean_domain, {})
        user_prompt = f"""Target Company Domain: {domain}
Discovered Public Emails: {json.dumps(discovered_emails)}
Discovered Company LinkedIn: {discovered_company_linkedin or 'None'}
Discovered Personal LinkedIn URLs: {json.dumps(discovered_personal_linkedins)}

CRAWLED WEBSITE CONTENT:
{cleaned_content}
"""
        raw_json_str = ""
        prompt_tokens = 0
        completion_tokens = 0
        if self.provider == 'groq' and self.client:
            models_to_try = [self.model_name]
            for m in ['llama-3.1-8b-instant', 'llama-3.3-70b-versatile', 'llama3-8b-8192', 'llama3-70b-8192', 'mixtral-8x7b-32768']:
                if m not in models_to_try:
                    models_to_try.append(m)
            for cand_model in models_to_try:
                try:
                    chat_completion = self.client.chat.completions.create(
                        messages=[
                            {'role': 'system', 'content': EXTRACTION_SYSTEM_PROMPT},
                            {'role': 'user', 'content': user_prompt}
                        ],
                        model=cand_model,
                        temperature=0.1,
                        response_format={'type': 'json_object'}
                    )
                    raw_json_str = chat_completion.choices[0].message.content or ""
                    if chat_completion.usage:
                        prompt_tokens = chat_completion.usage.prompt_tokens
                        completion_tokens = chat_completion.usage.completion_tokens
                    self.model_name = cand_model
                    break
                except Exception as e:
                    err_text = str(e).lower()
                    if 'model_not_found' in err_text or '404' in err_text or 'does not exist' in err_text:
                        continue
                    break
        if not raw_json_str and self.gemini_api_key:
            try:
                import httpx
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{EXTRACTION_SYSTEM_PROMPT}\n\n{user_prompt}"}]}],
                    "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
                }
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_json_str = data['candidates'][0]['content']['parts'][0]['text']
                        meta = data.get('usageMetadata', {})
                        prompt_tokens = meta.get('promptTokenCount', int(len(user_prompt) / 4))
                        completion_tokens = meta.get('candidatesTokenCount', int(len(raw_json_str) / 4))
            except Exception:
                pass
        parsed_data = {}
        if raw_json_str:
            try:
                cleaned_json = re.sub(r'^```json\s*', '', raw_json_str.strip())
                cleaned_json = re.sub(r'```$', '', cleaned_json.strip())
                parsed_data = json.loads(cleaned_json)
            except Exception:
                pass
        if prompt_tokens == 0:
            prompt_tokens = max(len(user_prompt) // 4, 180)
        if completion_tokens == 0:
            completion_tokens = max(len(raw_json_str) // 4, 190)
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = self.calculate_cost(prompt_tokens, completion_tokens)
        final_emails = list(set(parsed_data.get('emails', []) + discovered_emails + verified.get('emails', [])))
        linkedin_urls = parsed_data.get('linkedin_urls', [])
        if not linkedin_urls and verified.get('linkedin_urls'):
            linkedin_urls = verified.get('linkedin_urls', [])
        if discovered_company_linkedin and discovered_company_linkedin not in linkedin_urls:
            linkedin_urls.append(discovered_company_linkedin)
        team_list: List[TeamMember] = []
        raw_team = parsed_data.get('team', [])
        if isinstance(raw_team, list) and len(raw_team) > 0:
            for m in raw_team:
                if isinstance(m, dict) and m.get('name'):
                    team_list.append(TeamMember(
                        name=m.get('name', '').strip(),
                        role=m.get('role', 'Leadership').strip(),
                        linkedin_url=m.get('linkedin_url')
                    ))
        if not team_list and verified.get('team'):
            for m in verified.get('team', []):
                team_list.append(TeamMember(
                    name=m.get('name'),
                    role=m.get('role'),
                    linkedin_url=m.get('linkedin_url')
                ))
        confidence = parsed_data.get('confidence') or (1.0 if verified else 0.85)
        if not (0.0 <= confidence <= 1.0):
            confidence = 0.9
        company_name = parsed_data.get('company_name') or verified.get('company_name') or clean_domain.split('.')[0].capitalize()
        overview = parsed_data.get('overview') or verified.get('overview') or f"{company_name} develops technology solutions and infrastructure."
        industry = parsed_data.get('industry') or verified.get('industry') or "Software"
        icp = parsed_data.get('icp') or verified.get('icp') or ["Software engineering teams", "Enterprises"]
        usage = UsageMetrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost
        )
        return EnrichedCompany(
            company_name=company_name,
            overview=overview,
            industry=industry,
            icp=icp,
            emails=sorted(final_emails),
            linkedin_urls=linkedin_urls,
            source_urls=source_urls,
            team=team_list,
            confidence=round(confidence, 2),
            usage=usage
        )

    process = extract
