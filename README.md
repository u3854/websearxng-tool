# WebSearx

A flexible and simple web search and scraping tool that works as a Python library, a CLI utility, and an MCP server. (Not fully tested, not in active development)

## Features

* **Search Engine Agnostic:** Defaults to SearXNG (if available), falls back to DuckDuckGo (ddgs).
* **Smart Scraping:** Attempts fast scraping (Requests/Trafilatura) first, falls back to headless browser (Playwright) for JS-heavy sites.
* **PDF Support:** Automatically detects and extracts text from PDF URLs.
* **Dual Interface:** Run as a command-line tool or an MCP server for LLMs.
* **Format Options:** Output human-readable rich text or raw JSON.

## Installation

### Option 1: Install from GitHub (Recommended for users)
You can install this directly into your environment using pip:

```bash
pip install "git+[https://github.com/u3854/websearxng-tool.git](https://github.com/u3854/websearxng-tool.git)"

```

**Post-Install:** You must install the browser binaries for the scraper to work on JS-heavy sites:

```bash
playwright install chromium

```

### Option 2: Local Development

This project is managed with `uv`.

```bash
uv sync

```

## CLI Usage

If installed via pip, use `websearx`. If using uv, use `uv run websearx`.

### Searching

```bash
# Basic search
websearx "python async tutorial"

# Search and scrape the top 3 results
websearx "latest ai news" --scrape --limit 3

# Filter by time (day, month, year)
websearx "stock market" --time day

```

### Scraping

```bash
# Scrape one or more URLs directly
websearx scrape [https://example.com](https://example.com) [https://another.com](https://another.com)

```

### JSON Output

Add `--json` to any command to get raw JSON output (useful for piping to `jq`).

```bash
websearx "linux commands" --json

```

## Library Usage

You can import the core functions directly into your Python scripts:

```python
from websearx_tool.tools import web_search, get_url_content

# Search (returns list of dicts)
results = web_search("manchester united", limit=3)

# Scrape (returns dict of {index: text})
content = get_url_content(["[https://example.com](https://example.com)"])

```

## MCP Server Usage

To use this as a Model Context Protocol (MCP) server:

```bash
# If installed via pip
python -m websearx_tool.server

# If using uv
uv run python -m websearx_tool.server

```

### Available Tools

* `web_search(query, time_range, full_content, max_results)`
* `get_url_content(urls)`

## Configuration

* **SearXNG Host:** Set the `SEARXNG_HOST` environment variable to point to your instance.
* Default: `http://127.0.0.1:8080`



```

```