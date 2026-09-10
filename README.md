# AI Company Intelligence Agent

An autonomous Python-based AI agent that crawls public company websites, extracts useful company information, and uses an LLM to generate structured company intelligence.

## Features

* Dynamic website crawling using Playwright
* Automatic discovery of relevant internal pages
* Handles JavaScript-rendered websites
* Extracts clean visible text from HTML
* Removes scripts, styles, SVGs, navigation, and footer boilerplate
* Extracts publicly available email addresses
* Extracts LinkedIn URLs from website content
* Uses Google Gemini for structured company analysis
* Pydantic schema validation
* Confidence scoring
* Error handling for failed pages
* Handles missing pages and 404 responses
* Handles page timeouts and navigation failures
* Continues processing when individual companies fail
* Saves final intelligence as JSON
* Supports custom company domains through command-line arguments

## Architecture

```text
Company Domains
      |
      v
Python Pipeline
      |
      v
Playwright Browser
      |
      v
Homepage + Relevant Internal Pages
      |
      v
Rendered HTML Content
      |
      v
HTML Cleaning & Extraction
      |
      +------> Public Emails
      |
      +------> LinkedIn URLs
      |
      v
Clean Website Text
      |
      v
Google Gemini LLM
      |
      v
Structured JSON Response
      |
      v
Pydantic Validation
      |
      v
data/output.json
```

## Project Structure

```text
AI_AGENT/
|
├── data/
│   └── output.json
|
├── src/
│   ├── __init__.py
│   ├── crawler.py
│   ├── extractor.py
│   ├── llm.py
│   ├── pipeline.py
│   └── schemas.py
|
├── .env
├── .gitignore
├── main.py
├── requirements.txt
└── README.md
```

## How the Agent Works

The system processes each company domain through multiple stages.

### 1. Input

The agent accepts company domains from the command line.

The default assignment domains are:

```text
postman.com
supabase.com
vapi.ai
```

Custom domains can also be provided.

### 2. Website Crawling

Playwright launches a headless Chromium browser and loads the company website.

The crawler first visits the homepage and then discovers relevant internal pages using links found on the homepage.

Relevant pages may include:

* About
* Company
* Team
* Leadership
* Contact
* Pricing

The crawler uses rendered browser content so that JavaScript-based websites can also be processed.

### 3. Content Extraction

The raw HTML is not directly sent to the LLM.

The extractor removes unnecessary elements such as:

* JavaScript
* CSS
* SVG
* iframe
* canvas
* noscript
* navigation
* footer

The remaining visible text is cleaned and normalized before being passed to the LLM.

This reduces unnecessary tokens and improves the quality of the information supplied to the model.

### 4. Contact Extraction

The extractor identifies publicly visible email addresses from the crawled HTML.

Only emails actually found in the website content are passed to the LLM.

The system does not generate or guess email addresses.

### 5. LinkedIn Extraction

The system also identifies LinkedIn URLs available in the website HTML.

These URLs can represent:

* Company LinkedIn pages
* Leadership profiles
* Team member profiles

Only discovered URLs are provided to the LLM.

### 6. LLM Analysis

The cleaned website information is passed to Google Gemini.

The LLM is instructed to analyze only the supplied website evidence and avoid hallucinating information.

The model extracts:

* Company overview
* Target audience / Ideal Customer Profile
* Public contact emails
* Key leadership/team members
* Roles and titles
* LinkedIn URLs when available
* Confidence score

### 7. Structured Output

The Gemini response is validated using Pydantic.

The output follows a fixed schema:

```json
{
    "domain": "example.com",
    "company_overview": "Company description...",
    "target_audience": "Target customers...",
    "contact_emails": [],
    "team_members": [],
    "confidence_score": 0.85
}
```

The confidence score is constrained between:

```text
0.0 and 1.0
```

### 8. Final Output

The final results are stored in:

```text
data/output.json
```

Each successfully processed company is stored as a separate JSON object.

## Technologies Used

### Python

The core programming language used to build the agent and pipeline.

### Playwright

Used for automated browser-based website crawling and JavaScript-rendered content.

### BeautifulSoup

Used for parsing HTML and extracting clean visible text.

### Google Gemini

Used as the LLM for company intelligence extraction and structured analysis.

### Pydantic

Used for schema validation and ensuring reliable structured output.

### python-dotenv

Used to securely load environment variables such as the Gemini API key.

### Tenacity

Included for retry and resilience handling for temporary API failures.

### tiktoken

Included for token-related processing and optimization support.

## Installation

### 1. Clone the Repository

After downloading or cloning the project:

```bash
git clone <your-github-repository-url>
cd AI_AGENT
```

### 2. Create a Virtual Environment

Windows:

```powershell
python -m venv venv
```

### 3. Activate the Virtual Environment

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell execution policy prevents activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install Python Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Install Playwright Chromium

```powershell
python -m playwright install chromium
```

## Environment Configuration

Create a `.env` file in the project root.

```text
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
```

The API key must not be committed to GitHub.

The `.gitignore` file excludes:

```text
.env
venv/
__pycache__/
*.pyc
```

## Running the Agent

### Run Default Assignment Domains

```powershell
python main.py
```

This processes:

```text
postman.com
supabase.com
vapi.ai
```

### Run Custom Domains

You can provide one or more domains:

```powershell
python main.py example.com example2.com
```

For example:

```powershell
python main.py postman.com supabase.com vapi.ai
```

## Example Execution

```text
AI COMPANY INTELLIGENCE AGENT
============================================================
Companies to process: 3

============================================================
Processing: postman.com
============================================================
[1/3] Crawling website...
[INFO] Discovered 5 relevant link(s).
[INFO] Successfully crawled 6 page(s).
[2/3] Cleaning and extracting information...
[INFO] Found 3 email(s)
[INFO] Found 4 LinkedIn URL(s)
[3/3] Sending evidence to LLM...
[SUCCESS] Company analysis completed.

============================================================
Processing: supabase.com
============================================================
[1/3] Crawling website...
[INFO] Discovered 5 relevant link(s).
[INFO] Successfully crawled 6 page(s).
[2/3] Cleaning and extracting information...
[INFO] Found 5 email(s)
[INFO] Found 0 LinkedIn URL(s)
[3/3] Sending evidence to LLM...
[SUCCESS] Company analysis completed.

============================================================
Processing: vapi.ai
============================================================
[1/3] Crawling website...
[INFO] Discovered 1 relevant link(s).
[INFO] Successfully crawled 2 page(s).
[2/3] Cleaning and extracting information...
[INFO] Found 0 email(s)
[INFO] Found 1 LinkedIn URL(s)
[3/3] Sending evidence to LLM...
[SUCCESS] Company analysis completed.

============================================================
PROCESSING COMPLETE
Successful companies: 3
Output saved to: data\output.json
============================================================
```

## Output Schema

The final output contains the following fields:

### domain

The company domain that was processed.

### company_overview

A concise two-sentence description of the company based on website evidence.

### target_audience

The identified target users or Ideal Customer Profile.

### contact_emails

Publicly available email addresses discovered from the website.

### team_members

Important team or leadership members discovered from the supplied website evidence.

Each team member may contain:

```json
{
    "name": "Person Name",
    "role": "Role or Title",
    "linkedin_url": "LinkedIn URL"
}
```

### confidence_score

A numerical value between `0.0` and `1.0` representing confidence in the extracted intelligence.

## Sample Output

Example structure:

```json
[
    {
        "domain": "postman.com",
        "company_overview": "Postman is an AI-native API platform designed to develop, test, manage, and distribute APIs and services.",
        "target_audience": "Software engineers, API developers, and enterprise organizations building and scaling APIs.",
        "contact_emails": [
            "info@postman.com"
        ],
        "team_members": [
            {
                "name": "Abhinav Asthana",
                "role": "CEO/Co-Founder",
                "linkedin_url": "https://www.linkedin.com/in/abhinavasthana"
            }
        ],
        "confidence_score": 0.95
    }
]
```

## Resilience and Error Handling

The pipeline is designed so that failures in individual pages or companies do not unnecessarily terminate the entire process.

The crawler handles:

* HTTP 404 responses
* Page navigation failures
* Page timeouts
* Missing links
* Missing HTML elements
* JavaScript-rendering issues
* Empty pages
* Bot-blocked or inaccessible pages

The extraction layer handles:

* Missing emails
* Missing LinkedIn URLs
* Empty page content
* Duplicate emails
* Duplicate LinkedIn URLs

The LLM layer validates its response using Pydantic.

If a company cannot be processed successfully, the pipeline returns `None` and continues with the remaining domains.

## Anti-Hallucination Approach

The LLM is explicitly instructed to use only the supplied website evidence.

The system prevents the model from:

* Inventing email addresses
* Inventing people
* Inventing job titles
* Inventing LinkedIn URLs
* Using unsupported external information

When information is unavailable, the model is instructed to return an empty value, empty list, or `null`.

This approach prioritizes factual reliability over filling every field.

## Token Optimization

The system does not send raw HTML trees directly to the LLM.

Before LLM processing:

1. HTML is parsed.
2. Scripts and styles are removed.
3. SVG and other unnecessary elements are removed.
4. Navigation and footer boilerplate are removed.
5. Visible text is extracted.
6. Whitespace is normalized.
7. Page text is limited to a reasonable maximum length.
8. Relevant extracted emails and LinkedIn URLs are supplied separately.

This reduces unnecessary context and makes the LLM input more focused.

## Testing

The agent was tested using the three assignment domains:

```text
postman.com
supabase.com
vapi.ai
```

The test successfully produced structured results for all three domains.

### Test Results

```text
postman.com
6 pages crawled
3 emails discovered
4 LinkedIn URLs discovered
LLM analysis successful

supabase.com
6 pages crawled
5 emails discovered
0 LinkedIn URLs discovered
LLM analysis successful

vapi.ai
2 pages crawled
0 emails discovered
1 LinkedIn URL discovered
LLM analysis successful
```

## Limitations

The current implementation relies primarily on information available on the company's public website.

If a company does not publish:

* Leadership information
* Contact emails
* LinkedIn profiles

the corresponding fields may remain empty.

The system does not fabricate missing information.

Some websites may also block automated browsing or require additional browser interaction.

## Future Improvements

Possible improvements include:

* External search integration using Tavily or SerpAPI
* Searching for leadership LinkedIn profiles when unavailable on the website
* More advanced agentic workflows using LangGraph or Browser-Use
* Automatic token and API cost tracking
* Persistent company intelligence storage
* Parallel processing of multiple companies
* More advanced duplicate-content detection
* Additional website discovery strategies
* Structured CSV export
* Confidence calibration based on evidence coverage

## Security

API keys are loaded from environment variables.

Secrets should never be placed directly inside source code.

The `.env` file is excluded from Git version control.

Never commit:

```text
.env
```

to the public repository.

## Assignment Requirements Covered

The implementation covers the major technical requirements:

* Automated browsing/content retrieval
* Dynamic JavaScript-compatible crawling
* Homepage and relevant subpage discovery
* HTML preprocessing
* Token/context optimization
* LLM-based company intelligence extraction
* Structured output
* Public contact extraction
* Leadership/team extraction
* LinkedIn URL extraction
* Confidence scoring
* Error handling
* 404 handling
* Timeout handling
* Pipeline continuation after failures
* Sample JSON output
* Modular Python architecture

## Author

A N SUPRIYA

B.E. Computer Science and Engineering (AI & ML)

Global Academy of Technology

2026
