# AI Company Intelligence Agent

An autonomous AI-powered company intelligence agent that accepts public company domains, automatically crawls relevant website pages, extracts useful business and leadership information, enriches the collected evidence, and produces structured company intelligence in JSON format.

The system is designed to work with different public company websites instead of depending on fixed company-specific URLs.

---

## Features

- Accepts one or multiple company domains as input
- Automatically crawls public company websites
- Uses Playwright for JavaScript-rendered websites
- Discovers relevant pages such as:
  - About
  - Company
  - Team
  - Leadership
  - Founders
  - People
  - Contact
  - Pricing
  - Press / Media
- Extracts public business emails
- Extracts LinkedIn URLs
- Identifies leadership and team members
- Identifies roles such as CEO, CTO, Founder, Director, VP, Head of, and similar positions
- Uses external search for additional public information
- Uses Groq LLM for structured company intelligence extraction
- Uses compact evidence instead of sending raw HTML to the LLM
- Tracks token usage
- Estimates LLM API cost
- Handles page failures and individual company failures without stopping the complete pipeline
- Saves final results as structured JSON

---

# Architecture

text
Company Domains
       |
       v
Playwright Web Crawler
       |
       v
Rendered Website Content
       |
       v
HTML / Text Preprocessing
       |
       +----------------------+
       |                      |
       v                      v
Deterministic Extraction   External Search
       |                      |
       +----------+-----------+
                  |
                  v
          Compact Evidence
                  |
                  v
              Groq LLM
                  |
                  v
        Structured JSON Output
                  |
                  v
        Evidence Merge Layer
                  |
                  v
          data/output.json
```

---

# Project Structure

```text
AI_AGENT/
│
├── main.py
├── README.md
├── requirements.txt
├── .env
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── crawler.py
│   ├── extractor.py
│   ├── search.py
│   ├── llm.py
│   ├── pipeline.py
│   └── schemas.py
│
└── data/
    └── output.json
```

---

# Technologies Used

- Python
- Playwright
- BeautifulSoup
- Requests
- Groq API
- Pydantic
- python-dotenv
- Git
- GitHub

---

# File Responsibilities

## `main.py`

Main entry point of the project.

It:

- accepts company domains
- starts the company intelligence pipeline
- controls crawl limits
- saves the final output

---

## `src/crawler.py`

Responsible for:

- opening websites
- rendering JavaScript
- discovering internal pages
- prioritizing relevant company pages
- reading sitemap information
- handling failed pages
- avoiding unnecessary low-value URLs

---

## `src/extractor.py`

Responsible for deterministic extraction of:

- email addresses
- `mailto:` links
- LinkedIn URLs
- names
- leadership roles
- source URLs
- cleaned page content

---

## `src/search.py`

Responsible for optional external search enrichment.

This can be used to find additional public company or leadership information that may not be available directly on the company website.

---

## `src/llm.py`

Responsible for the Groq LLM request.

The LLM receives compact evidence rather than raw HTML.

It generates structured information such as:

- company name
- overview
- industry
- target audience / ICP
- leadership team
- emails
- LinkedIn URLs
- source URLs
- confidence score

---

## `src/pipeline.py`

Coordinates the complete workflow:

```text
Crawling
   ↓
Extraction
   ↓
External Search
   ↓
LLM Processing
   ↓
Evidence Merging
   ↓
Final Result
```

---

## `src/schemas.py`

Contains structured data definitions used for validating the extracted company information.

---

# Installation

## 1. Clone the repository

```powershell
git clone https://github.com/ansupriya19/AI_AGENT.git
cd AI_AGENT


---

## 2. Create a virtual environment

```powershell
python -m venv venv
```

---

## 3. Activate the virtual environment

```powershell
.\venv\Scripts\Activate.ps1
```

---

## 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

---

## 5. Install Playwright Chromium

```powershell
python -m playwright install chromium
```

---

# Environment Configuration

Create a file named:

```text
.env
```

in the root directory of the project.

The project uses environment variables so that API keys and runtime configuration do not need to be hard-coded in Python files.

Your project should contain:

```text
AI_AGENT/
│
├── .env
├── main.py
├── requirements.txt
├── README.md
└── src/
```

---

# `.env` Configuration

Use the following configuration:

```env
GROQ_API_KEY=YOUR_GROQ_API_KEY
GROQ_MODEL=openai/gpt-oss-20b

MAX_CRAWL_PAGES=50
ENABLE_EXTERNAL_SEARCH=true

LLM_MAX_INPUT_CHARS=7500
LLM_MAX_PEOPLE=20
LLM_MAX_EMAILS=25
LLM_MAX_LINKEDIN=30
LLM_MAX_SOURCES=15
LLM_MAX_SEARCH=15

GROQ_INPUT_PRICE_PER_1M=0.075
GROQ_OUTPUT_PRICE_PER_1M=0.30
```

---

# Environment Variable Explanation

## `GROQ_API_KEY`

Your Groq API key.

```env
GROQ_API_KEY=YOUR_GROQ_API_KEY
```

---

## `GROQ_MODEL`

The LLM model used by the project.

```env
GROQ_MODEL=openai/gpt-oss-20b
```

---

## `MAX_CRAWL_PAGES`

Maximum number of pages to crawl for each company.

```env
MAX_CRAWL_PAGES=50
```

---

## `ENABLE_EXTERNAL_SEARCH`

Controls whether external search enrichment is enabled.

```env
ENABLE_EXTERNAL_SEARCH=true
```

---

## `LLM_MAX_INPUT_CHARS`

Maximum amount of compact evidence sent to the LLM.

```env
LLM_MAX_INPUT_CHARS=7500
```

---

## `LLM_MAX_PEOPLE`

Maximum number of people entries sent to the LLM.

```env
LLM_MAX_PEOPLE=20
```

---

## `LLM_MAX_EMAILS`

Maximum number of email addresses passed to the LLM.

```env
LLM_MAX_EMAILS=25
```

---

## `LLM_MAX_LINKEDIN`

Maximum number of LinkedIn URLs passed to the LLM.

```env
LLM_MAX_LINKEDIN=30
```

---

## `LLM_MAX_SOURCES`

Maximum number of source URLs passed to the LLM.

```env
LLM_MAX_SOURCES=15
```

---

## `LLM_MAX_SEARCH`

Maximum amount of external search evidence used.

```env
LLM_MAX_SEARCH=15
```

---

## `GROQ_INPUT_PRICE_PER_1M`

Input token price used for local cost estimation.

```env
GROQ_INPUT_PRICE_PER_1M=0.075
```

---

## `GROQ_OUTPUT_PRICE_PER_1M`

Output token price used for local cost estimation.

```env
GROQ_OUTPUT_PRICE_PER_1M=0.30
```

---

# Security

**Never commit your real `.env` file to GitHub.**

Add the following entries to `.gitignore`:

```gitignore
.env
venv/
__pycache__/
*.pyc
data/output.json
```

GitHub recommends securing repositories against accidentally exposed secrets such as API keys and tokens. :contentReference[oaicite:1]{index=1}

---

# Running the Project

## Run with default companies

```powershell
python main.py
```

The default companies are:

```text
postman.com
supabase.com
vapi.ai
```

---

## Run one company

```powershell
python main.py postman.com
```

---

## Run multiple companies

```powershell
python main.py postman.com supabase.com vapi.ai
```

---

# Changing the Crawl Limit

For example:

```powershell
$env:MAX_CRAWL_PAGES="50"
python main.py postman.com
```

For a smaller test:

```powershell
$env:MAX_CRAWL_PAGES="10"
python main.py postman.com
```

For deeper crawling:

```powershell
$env:MAX_CRAWL_PAGES="75"
python main.py postman.com
```

---

# How the Agent Works

## Step 1 - Company Input

The user provides one or more public company domains.

Example:

```text
postman.com
supabase.com
vapi.ai
```

---

## Step 2 - Website Crawling

The Playwright crawler opens the company website and searches for useful internal pages.

Priority is given to pages such as:

```text
/about
/company
/team
/leadership
/founders
/people
/contact
/contact-sales
/pricing
/press
/media
```

The crawler can also inspect sitemap information to discover additional public pages.

---

## Step 3 - JavaScript Rendering

Some modern websites generate their content dynamically using JavaScript.

Because of this, normal HTTP requests alone may not expose the complete page.

Playwright launches Chromium and renders the page before extraction.

---

## Step 4 - Evidence Extraction

The project extracts useful information directly from the website.

Examples include:

```text
Email addresses
LinkedIn URLs
Names
Leadership roles
Company pages
Source URLs
```

This extraction happens before the LLM step.

---

## Step 5 - Data Cleaning

The system removes unnecessary content such as:

```text
Scripts
CSS
SVG content
Navigation boilerplate
Unnecessary HTML structure
```

The goal is to create compact evidence.

---

## Step 6 - External Search

When enabled, the agent can perform additional public searches.

This can help identify information such as:

```text
Founder LinkedIn profiles
Leadership profiles
Additional public company information
```

---

## Step 7 - LLM Processing

The cleaned evidence is sent to the Groq LLM.

The model converts the evidence into structured company intelligence.

The LLM does **not** receive the complete raw HTML tree.

---

## Step 8 - Structured Output

The model generates fields such as:

```json
{
  "company_name": "",
  "overview": "",
  "industry": "",
  "icp": "",
  "team": [],
  "emails": [],
  "linkedin_urls": [],
  "source_urls": [],
  "confidence": 0.0
}
```

---

## Step 9 - Evidence Merge

The project merges deterministic extraction results with the LLM result.

This helps preserve information such as:

- emails
- LinkedIn URLs
- team members
- source URLs

even when the LLM response does not include every extracted item.

---

# Output

The final output is saved in:

```text
data/output.json
```

Example:

```json
{
  "generated_at": "2026-09-13T00:00:00",
  "companies": [
    {
      "company_name": "Example Company",
      "overview": "Example Company provides software solutions for modern businesses.",
      "industry": "Software",
      "icp": "Technology teams and businesses",
      "team": [
        {
          "name": "Example Founder",
          "role": "Co-Founder & CEO",
          "linkedin_url": "https://www.linkedin.com/in/example"
        }
      ],
      "emails": [
        "info@example.com"
      ],
      "linkedin_urls": [
        "https://www.linkedin.com/company/example"
      ],
      "source_urls": [
        "https://example.com/about"
      ],
      "confidence": 0.92
    }
  ]
}
```

---

# Output Fields

## `company_name`

The normalized company name.

---

## `overview`

A concise description of what the company does.

---

## `industry`

The inferred business or technology industry.

---

## `icp`

The target audience or Ideal Customer Profile.

---

## `team`

Leadership and relevant team members discovered from public sources.

Each member can contain:

```json
{
  "name": "",
  "role": "",
  "linkedin_url": ""
}
```

---

## `emails`

Publicly available company or generic email addresses.

---

## `linkedin_urls`

Relevant LinkedIn company and personal-profile URLs.

---

## `source_urls`

Public pages used as evidence.

---

## `confidence`

A confidence score between:

```text
0.0
```

and:

```text
1.0
```

---

# Token Optimization

A major design goal of this project is to avoid sending unnecessarily large website content to the LLM.

Instead of:

```text
Website → Raw HTML → LLM
```

the system uses:

```text
Website
   ↓
Rendered HTML
   ↓
Cleaning
   ↓
Deterministic Extraction
   ↓
Compact Evidence
   ↓
LLM
```

This reduces unnecessary token usage and helps avoid request-size and token-per-minute limits.

The project controls the amount of information sent to the LLM using:

```env
LLM_MAX_INPUT_CHARS=7500
LLM_MAX_PEOPLE=20
LLM_MAX_EMAILS=25
LLM_MAX_LINKEDIN=30
LLM_MAX_SOURCES=15
LLM_MAX_SEARCH=15
```

---

# Cost Tracking

The project records:

```text
Prompt tokens
Completion tokens
Total tokens
Estimated cost
```

Example:

```text
Prompt tokens: 2200
Completion tokens: 300
Total tokens: 2500
Estimated cost: $0.0003
```

The exact values depend on the pages crawled and the LLM response.

---

# Resilience

The system is designed so that a single failure does not stop the complete process.

The pipeline can handle situations such as:

- 404 pages
- page timeouts
- redirects
- blocked pages
- missing content
- JavaScript errors
- broken links
- sitemap failures
- individual company failures
- LLM request failures

For example:

```text
postman.com     ✓
supabase.com    ✓
vapi.ai         ✗
```

The successful companies can still be processed and stored.

---

# Anti-Hallucination Design

The project uses a combination of deterministic extraction and LLM reasoning.

The deterministic extractor obtains information directly from public website evidence.

For example:

```text
Email
LinkedIn URL
Name
Role
Source URL
```

The LLM is then used for:

```text
Company overview
Industry classification
ICP identification
Normalization
Reasoning
Confidence estimation
```

This architecture reduces the possibility of the LLM inventing information that does not appear in the collected evidence.

---

# Validation

Before running the project, use:

```powershell
python -m py_compile main.py src\crawler.py src\extractor.py src\search.py src\llm.py src\pipeline.py src\schemas.py
```

If there is no output, the files passed the Python syntax check.

---

# Testing

## Test one company

```powershell
python main.py postman.com
```

---

## Test multiple companies

```powershell
python main.py postman.com supabase.com vapi.ai
```

---

## View the output

```powershell
Get-Content data\output.json
```

---

## View formatted JSON

```powershell
Get-Content data\output.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

---

# Troubleshooting

## Playwright browser is not installed

Run:

```powershell
python -m playwright install chromium
```

---

## Groq API Error

Check your `.env` file:

```env
GROQ_API_KEY=YOUR_GROQ_API_KEY
```

Make sure the `.env` file is located in the project root.

---

## Request Too Large

Reduce the LLM limits:

```env
LLM_MAX_INPUT_CHARS=5000
LLM_MAX_PEOPLE=10
LLM_MAX_EMAILS=15
LLM_MAX_LINKEDIN=20
LLM_MAX_SOURCES=10
LLM_MAX_SEARCH=8
```

You can also reduce:

```env
MAX_CRAWL_PAGES=20
```

---

## Very Few Pages Are Being Crawled

Increase:

```env
MAX_CRAWL_PAGES=50
```

or:

```powershell
$env:MAX_CRAWL_PAGES="75"
python main.py postman.com
```

---

## Leadership Information Is Missing

Some companies do not publish leadership information directly on their website.

The agent can attempt to use:

```text
/team
/leadership
/founders
/about
/press
```

and optional external search enrichment.

---

## Emails Are Missing

A company may simply not expose public email addresses.

The agent does not invent private email addresses.

Possible public sources include:

```text
/contact
/contact-us
/company/contact-us
/press
```

---

# Assignment Requirements Covered

| Requirement | Implementation |
|---|---|
| Company domains as input | `main.py` |
| Automated browsing | Playwright |
| JavaScript-rendered content | Playwright Chromium |
| Homepage crawling | Crawler |
| Relevant subpages | Page prioritization |
| DOM preprocessing | `extractor.py` |
| Raw HTML not directly sent to LLM | Compact evidence |
| Company overview | Groq LLM |
| Target audience / ICP | Groq LLM |
| Public emails | Deterministic extraction |
| Leadership/team | Extractor + LLM |
| LinkedIn URLs | Extractor + search |
| Confidence score | Structured output |
| Failure resilience | Error handling |
| Token optimization | Evidence limits |
| Cost tracking | Token/cost calculation |
| Multi-step workflow | Crawl → Extract → Search → LLM → Merge |

---

# Limitations

The system depends on publicly accessible information.

It cannot guarantee that every company website provides:

- leadership information
- public emails
- LinkedIn URLs
- complete team information
- accessible sitemap data

Some websites may also block automated crawling or require login.

Only information available from permitted public sources should be considered valid output.

---

# Future Improvements

Possible future enhancements include:

- Better LinkedIn discovery
- More advanced search integration
- Website page classification
- Persistent crawl cache
- Parallel crawling
- Database storage
- Streamlit dashboard
- CSV / Excel export
- REST API
- Automated testing
- GitHub Actions CI/CD
- More advanced observability
- Crawl checkpoint and resume support

---

# GitHub Workflow

After making changes locally, check the status:

```powershell
git status
```

Add the changes:

```powershell
git add .
```

Commit the changes:

```powershell
git commit -m "Update AI company intelligence agent"
```

Push the changes:

```powershell
git push
```

Your local changes do not automatically synchronize with GitHub. Changes need to be committed and pushed to update the remote repository. :contentReference[oaicite:2]{index=2}

---

# Repository

GitHub repository:

```text
https://github.com/ansupriya19/AI_AGENT
```

---

# Author

**A N SUPRIYA**

B.E. Computer Science and Engineering (AI & ML)

---

# License

This project can be distributed under a license of the author's choice.

If publishing it as open source, add an appropriate `LICENSE` file to the repository.

---

# Quick Start

```powershell
git clone https://github.com/ansupriya19/AI_AGENT.git

cd AI_AGENT

python -m venv venv

.\venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

python -m playwright install chromium
```

Create `.env`:

```env
GROQ_API_KEY=YOUR_GROQ_API_KEY
GROQ_MODEL=openai/gpt-oss-20b

MAX_CRAWL_PAGES=50
ENABLE_EXTERNAL_SEARCH=true

LLM_MAX_INPUT_CHARS=7500
LLM_MAX_PEOPLE=20
LLM_MAX_EMAILS=25
LLM_MAX_LINKEDIN=30
LLM_MAX_SOURCES=15
LLM_MAX_SEARCH=15

GROQ_INPUT_PRICE_PER_1M=0.075
GROQ_OUTPUT_PRICE_PER_1M=0.30
```

Run:

```powershell
python main.py postman.com supabase.com vapi.ai
```

Generated output:


data/output.json
```

---

# Project Goal

The goal of this project is to build a practical autonomous company-intelligence system that can discover, extract, validate, enrich, and structure publicly available company information with minimal manual intervention.