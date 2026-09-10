import json
import sys
from pathlib import Path

# Add src folder to Python's import path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.pipeline import run_company_pipeline


def main():
    # Get domains from command-line arguments
    domains = sys.argv[1:]

    # Use assignment domains if none are provided
    if not domains:
        domains = [
            "postman.com",
            "supabase.com",
            "vapi.ai",
        ]

    print("\nAI COMPANY INTELLIGENCE AGENT")
    print("=" * 60)
    print(f"Companies to process: {len(domains)}")

    results = []

    for domain in domains:
        result = run_company_pipeline(domain)

        if result:
            results.append(result.model_dump())

    # Create data folder if it doesn't exist
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    # Save results
    output_file = output_dir / "output.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print(f"Successful companies: {len(results)}")
    print(f"Output saved to: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()