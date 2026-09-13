import json
import os
import sys
from datetime import datetime

from src.pipeline import run_company_pipeline


DEFAULT_DOMAINS = [
    "postman.com",
    "supabase.com",
    "vapi.ai",
]


def get_crawl_limit() -> int:
    """
    Read MAX_CRAWL_PAGES.

    Default = 50.
    This allows the agent to inspect substantially more
    internal pages when the environment variable is absent.
    """

    raw_value = os.getenv(
        "MAX_CRAWL_PAGES",
        "50"
    )

    try:
        crawl_limit = int(raw_value)
    except ValueError:
        print(
            "[WARNING] Invalid MAX_CRAWL_PAGES="
            f"{raw_value!r}. Using 50."
        )
        crawl_limit = 50

    if crawl_limit < 1:
        print(
            "[WARNING] MAX_CRAWL_PAGES must be >= 1. "
            "Using 50."
        )
        crawl_limit = 50

    return crawl_limit


def save_results(results):
    """
    Save final intelligence to data/output.json.
    """

    os.makedirs(
        "data",
        exist_ok=True
    )

    output = {
        "generated_at": (
            datetime.utcnow().isoformat()
            + "Z"
        ),
        "companies": results
    }

    output_path = os.path.join(
        "data",
        "output.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    return output_path


def main():

    print(
        "=" * 70
    )

    print(
        "AI COMPANY INTELLIGENCE AGENT"
    )

    print(
        "=" * 70
    )

    # ---------------------------------------------------------
    # DOMAIN INPUT
    # ---------------------------------------------------------

    if len(sys.argv) > 1:

        domains = [
            arg.strip()
            for arg in sys.argv[1:]
            if arg.strip()
        ]

    else:

        domains = DEFAULT_DOMAINS

    if not domains:

        print(
            "[ERROR] No domains supplied."
        )

        sys.exit(1)

    # ---------------------------------------------------------
    # CRAWL CONFIGURATION
    # ---------------------------------------------------------

    crawl_limit = get_crawl_limit()

    print(
        f"\n[CONFIG] MAX_CRAWL_PAGES = "
        f"{crawl_limit}"
    )

    print(
        "[CONFIG] The crawler will inspect "
        "all sections of every successfully "
        "rendered page within this crawl limit."
    )

    # ---------------------------------------------------------
    # DOMAINS
    # ---------------------------------------------------------

    print(
        "\nDomains to process:"
    )

    for domain in domains:

        print(
            f"  - {domain}"
        )

    results = []

    # ---------------------------------------------------------
    # PROCESS EACH COMPANY
    # ---------------------------------------------------------

    for domain in domains:

        print(
            "\n" + "=" * 70
        )

        print(
            f"STARTING COMPANY: {domain}"
        )

        print(
            "=" * 70
        )

        try:

            result = run_company_pipeline(
                domain=domain,
                max_pages=crawl_limit
            )

            if not isinstance(
                result,
                dict
            ):
                result = {
                    "company_name": domain,
                    "overview": "",
                    "industry": "",
                    "icp": [],
                    "team": [],
                    "emails": [],
                    "linkedin_urls": [],
                    "source_urls": [],
                    "confidence": 0.0,
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "estimated_cost_usd": 0.0
                    }
                }

            results.append(result)

        except KeyboardInterrupt:

            print(
                "\n[WARNING] "
                "Process interrupted by user."
            )

            break

        except Exception as exc:

            print(
                "\n[ERROR] "
                f"Failed to process {domain}"
            )

            print(
                f"{type(exc).__name__}: {exc}"
            )

            # Keep the company in the final JSON
            # instead of losing the whole run.
            results.append(
                {
                    "company_name": domain,
                    "overview": "",
                    "industry": "",
                    "icp": [],
                    "team": [],
                    "emails": [],
                    "linkedin_urls": [],
                    "source_urls": [],
                    "confidence": 0.0,
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "estimated_cost_usd": 0.0
                    },
                    "error": str(exc)
                }
            )

    # ---------------------------------------------------------
    # SAVE RESULTS
    # ---------------------------------------------------------

    output_path = save_results(
        results
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "PROCESSING COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        f"\nCompanies processed: "
        f"{len(results)}"
    )

    print(
        f"Results saved to:\n"
        f"{output_path}"
    )


if __name__ == "__main__":
    main()