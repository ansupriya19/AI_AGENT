from crawler import crawl_website
from extractor import process_pages
from llm import analyze_company


def run_company_pipeline(domain: str):
    """
    It is used to run the complete AI intelligence pipeline for one company.
    """

    print(f"\n{'=' * 60}")
    print(f"Processing: {domain}")
    print(f"{'=' * 60}")

    try:
        # Step 1: Crawl website
        print("[1/3] Crawling website...")

        pages = crawl_website(domain)

        if not pages:
            print("[WARNING] No pages were successfully crawled.")
            return None

        print(f"[INFO] Successfully crawled {len(pages)} page(s).")

        # Step 2: Extracting the useful information
        print("[2/3] Cleaning and extracting information...")

        extracted_data = process_pages(pages)

        print(
            f"[INFO] Found "
            f"{len(extracted_data['contact_emails'])} email(s)"
        )

        print(
            f"[INFO] Found "
            f"{len(extracted_data['linkedin_urls'])} LinkedIn URL(s)"
        )

        # Step 3: Analyzing with LLM
        print("[3/3] Sending evidence to LLM...")

        result = analyze_company(
            domain=domain,
            clean_text=extracted_data["clean_text"],
            contact_emails=extracted_data["contact_emails"],
            linkedin_urls=extracted_data["linkedin_urls"],
        )

        print("[SUCCESS] Company analysis completed.")

        return result

    except Exception as error:
        print(f"[ERROR] Pipeline failed for {domain}: {error}")

        # Important: It returns None instead of crashing the whole program
        return None