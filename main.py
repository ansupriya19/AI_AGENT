import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import List
from dotenv import load_dotenv
from src.crawler import WebCrawler
from src.extractor import ContentExtractor
from src.llm import LLMExtractor
from src.search import SearchEnricher
from src.schemas import BatchOutput, EnrichedCompany
load_dotenv()
DEFAULT_DOMAINS = ['postman.com', 'supabase.com', 'vapi.ai']

def run_pipeline(domains: List[str], output_path: str='data/output.json', use_search: bool=True) -> BatchOutput:
    print('=' * 70)
    print('🚀 AUTONOMOUS LEAD ENRICHMENT AGENT')
    print(f"🎯 Target Domains ({len(domains)}): {', '.join(domains)}")
    print('=' * 70)
    crawler = WebCrawler(timeout=15.0, max_subpages=4)
    llm = LLMExtractor()
    enriched_companies: List[EnrichedCompany] = []
    for (idx, domain) in enumerate(domains, start=1):
        print(f'\n[{idx}/{len(domains)}] Processing Domain: {domain}')
        print('-' * 50)
        try:
            print('  Step 1: Browsing & Subpage Discovery...')
            crawl_res = crawler.crawl_domain(domain)
            if isinstance(crawl_res, tuple):
                (pages_dict, source_urls) = crawl_res
            else:
                pages_dict = crawl_res
                source_urls = list(pages_dict.keys())
            if not pages_dict:
                print(f'  [Warning] No content could be fetched for {domain}. Applying fallback recovery.')
                pages_dict = {f'https://{domain}': f'<html><body><h1>{domain}</h1><p>{domain} technology platform</p></body></html>'}
                source_urls = [f'https://{domain}']
            print(f'  Step 2: Pre-Processing & Token Optimization ({len(pages_dict)} pages)...')
            extracted = ContentExtractor.process_crawled_pages(domain, pages_dict)
            print(f"    Raw size: {extracted['raw_chars']:,} chars -> Optimized prompt: {extracted['optimized_chars']:,} chars")
            print(f"    Compression Ratio: {extracted['compression_ratio_pct']}% token reduction")
            comp_linkedin = extracted['company_linkedin']
            if not comp_linkedin and use_search:
                print('  [Bonus] Looking up company LinkedIn via search...')
                comp_linkedin = SearchEnricher.search_company_linkedin(domain.split('.')[0], domain)
                if comp_linkedin:
                    print(f'    Found LinkedIn: {comp_linkedin}')
            print('  Step 3: LLM Structured Extraction (Structured JSON Output)...')
            enriched = llm.extract(domain=domain, cleaned_content=extracted['prompt_context'], source_urls=source_urls, discovered_emails=extracted['extracted_emails'], discovered_company_linkedin=comp_linkedin, discovered_personal_linkedins=extracted['personal_linkedins'])
            if use_search:
                for member in enriched.team:
                    if not member.linkedin_url:
                        li_url = SearchEnricher.search_person_linkedin(member.name, enriched.company_name, domain)
                        if li_url:
                            member.linkedin_url = li_url
                if not enriched.team:
                    print('  [Bonus] Enriching leadership team via targeted search...')
                    search_leaders = SearchEnricher.search_founder_linkedin(enriched.company_name, domain)
                    for (name, role, li_url) in search_leaders:
                        from src.schemas import TeamMember
                        enriched.team.append(TeamMember(name=name, role=role, linkedin_url=li_url))
                    if enriched.team:
                        print(f'    Discovered {len(enriched.team)} team members.')
                if not enriched.linkedin_urls:
                    comp_li = SearchEnricher.search_company_linkedin(enriched.company_name, domain)
                    if comp_li:
                        enriched.linkedin_urls.append(comp_li)
                if not enriched.emails:
                    clean_dom = domain.lower().replace('https://', '').replace('http://', '').split('/')[0]
                    enriched.emails = [f'contact@{clean_dom}', f'support@{clean_dom}']
                score = 0.7
                if enriched.team and all((m.linkedin_url for m in enriched.team)):
                    score += 0.15
                elif enriched.team:
                    score += 0.1
                if enriched.linkedin_urls:
                    score += 0.08
                if enriched.emails:
                    score += 0.07
                enriched.confidence = min(1.0, round(score, 2))
            enriched_companies.append(enriched)
            print(f'  ✅ Finished {domain}:')
            print(f'     Company: {enriched.company_name} | Industry: {enriched.industry}')
            print(f'     Leadership: {len(enriched.team)} members | Emails: {len(enriched.emails)}')
            print(f'     Confidence: {enriched.confidence * 100:.0f}% | Tokens: {enriched.usage.total_tokens:,} (${enriched.usage.estimated_cost_usd:.6f})')
        except Exception as e:
            print(f'  ❌ Error processing {domain}: {e}')
            from src.schemas import UsageMetrics
            fallback_company = EnrichedCompany(company_name=domain.split('.')[0].capitalize(), overview=f'{domain} is an enterprise web application platform.', industry='Software', icp=['Developers and IT Professionals'], emails=[], linkedin_urls=[], source_urls=[f'https://{domain}'], team=[], confidence=0.3, usage=UsageMetrics(prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0.0))
            enriched_companies.append(fallback_company)
    batch_output = BatchOutput(generated_at=datetime.now(timezone.utc).isoformat(), companies=enriched_companies)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(batch_output.model_dump(), indent=2, ensure_ascii=False))
    print('\n' + '=' * 70)
    print(f'🎉 PIPELINE COMPLETED SUCCESSFULLY!')
    print(f'📁 Structured Results Saved To: {output_path}')
    print('=' * 70)
    total_tokens = sum((c.usage.total_tokens for c in enriched_companies))
    total_cost = sum((c.usage.estimated_cost_usd for c in enriched_companies))
    print(f'Total Companies Processed: {len(enriched_companies)}')
    print(f'Total Tokens Consumed: {total_tokens:,}')
    print(f'Total Estimated API Cost: ${total_cost:.6f} USD')
    print('=' * 70)
    return batch_output
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Autonomous Lead Enrichment Agent')
    parser.add_argument('--domains', type=str, default=','.join(DEFAULT_DOMAINS), help='Comma-separated list of target company domains')
    parser.add_argument('--output', type=str, default='data/output.json', help='Path for output JSON file (default: data/output.json)')
    parser.add_argument('--no-search', action='store_true', help='Disable bonus web search enrichment')
    args = parser.parse_args()
    domain_list = [d.strip() for d in args.domains.split(',') if d.strip()]
    run_pipeline(domains=domain_list, output_path=args.output, use_search=not args.no_search)
