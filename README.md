# reconAPI

A reconnaissance toolkit that discovers and tests API endpoints by analyzing JavaScript files loaded by a target website.

## How It Works

1. **Scan** — Uses Playwright to visit the target URL and intercept all JavaScript files loaded by the page
2. **Download** — Fetches each JS file
3. **Parse** — Uses tree-sitter to extract API endpoint URLs from the JavaScript source code
4. **Test** — Sends OPTIONS requests to each discovered endpoint and reports status codes and allowed methods
5. **Report** — Outputs findings to the console or generates a PDF report

## Requirements

- Python 3.14+
- Windows (subfinder.exe is Windows-only in the current setup)

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/bbbmasterlolz/recon-url.git
cd recon-url

python -m venv .venv
.venv\Scripts\activate
```

### 2. Install the package

```bash
pip install -e .
```

### 3. Install tools

This installs Playwright (Chromium) and subfinder:

```bash
reconAPI setup
```

## Usage

### Scan a single URL

```bash
reconAPI https://example.com
```

### Scan with aggressive mode

Tests all possible base URL combinations for relative API paths instead of stopping at the first match:

```bash
reconAPI https://example.com -a
```

### Save results to PDF

Generates a PDF report named `<domain>_<date>.pdf`:

```bash
reconAPI https://example.com -o
```

### Scan all subdomains of a domain

Uses subfinder to enumerate subdomains, then scans each one individually (results are output immediately per subdomain):

```bash
reconAPI https://example.com -d
```

### Combine flags

```bash
# Aggressive + PDF
reconAPI https://example.com -a -o

# Domain mode + aggressive + PDF (one PDF per subdomain)
reconAPI https://example.com -d -a -o
```

### Other commands

```bash
# Show help
reconAPI --help

# Explicit scan subcommand (same as bare URL)
reconAPI scan https://example.com -a -o
```

## Project Structure

```
src/recon/
├── cli.py            # CLI argument parsing and entry point
├── main.py           # Orchestrator — controls the pipeline
├── scanner.py        # Playwright-based JS URL discovery
├── downloader.py     # Downloads JS files to temp storage
├── parser.py         # Tree-sitter endpoint extraction
├── tester.py         # OPTIONS request testing
├── reporter.py       # Console output and PDF generation
├── subdomain.py      # Subfinder wrapper for subdomain enumeration
├── setup/
│   └── installer.py  # Tool installer (Playwright, subfinder)
└── tool_installer/
    └── subfinder.py  # Subfinder download logic
```

## Architecture

All modules are **single-responsibility** and return results to `main.py`. The orchestrator decides what to call next:

```
main.py
  ├── scanner.find_js_urls()        → list of JS URLs
  ├── downloader.download_js()      → temp file path
  ├── parser.extract_endpoints()    → set of endpoint URLs
  ├── tester.test_urls()            → list of test results
  └── reporter.print / make_pdf()   → output
```

In domain mode (`-d`), `main.py` first calls `subdomain.find_subdomains()`, then runs the full pipeline for each subdomain with immediate output.
