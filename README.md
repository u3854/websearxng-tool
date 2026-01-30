(**NOTE**: Large parts of the project are **AI-generated**. I just didn't want to keep it in a perpetual WIP state. Not fully tested, not being actively worked on, so some manual intervention might be needed to run smoothly.)

# 🌐 WebSearx

**WebSearx** is an all-in-one web search and scraping suite. It functions as a high-performance Python library, a CLI utility, and a Model Context Protocol (MCP) server for LLMs (like Claude).

## Key Features

* **Self-Hosted Search:** Bundled `docker-compose` setup for SearXNG + Redis.
* **Privacy First:** Defaults to local SearXNG; falls back to DuckDuckGo (ddgs) if SearXNG is offline.
* **Hybrid Scraping:** 
    * **Fast Track:** Uses `trafilatura` for lightning-fast static extraction.
    * **Deep Track:** Automatically triggers `Playwright` (Headless Chromium) for JS-heavy or protected sites.


* **PDF Intelligence:** Native text extraction for PDF links.
* **MCP Ready:** Plug it straight into Claude Desktop or any MCP-compatible client.

---

## 🚀 Quick Start (Docker - Recommended)

The fastest way to get the full stack (App + Search Engine) running is via Docker:

```bash
# 1. Clone and navigate
git clone https://github.com/u3854/websearxng-tool.git
cd websearxng-tool

# 2. Spin up the stack
docker-compose up -d

```

**What this does:**

* Starts **SearXNG** (Search Engine) at `http://localhost:8080`
* Starts **Redis** (Search Cache)
* Starts the **WebSearx App** container, pre-configured to use the internal SearXNG.

---

## 🛠 Manual Installation

### Option 1: Via Pip

```bash
pip install "git+https://github.com/u3854/websearxng-tool.git"
playwright install chromium

```

### Option 2: Local Development (uv)

```bash
uv sync
uv run playwright install chromium

```

---

## 💻 Usage

### 1. Command Line (CLI)

The CLI automatically switches between a clean "Rich" UI and raw JSON.

```bash
# Basic Search
websearx "current nvidia stock price"

# Search + Deep Scrape (Visits the websites to get full text)
websearx "latest spacex launch" --scrape --limit 3

# Direct Scraping
websearx scrape https://docs.python.org/3/

```

### 2. MCP Server (For AI Agents)

To use WebSearx with Claude Desktop, add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "websearx": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "--network", "searx_net", "websearx_app"]
    }
  }
}

```

---

## 🏗 Architecture

1. **Search Layer:** Queries SearXNG (Local) -> DuckDuckGo (Cloud Fallback).
2. **Extraction Layer:** 
    * `smart_fetch`: Checks headers. If PDF or static HTML, extracts immediately.
    * `browser_fetch`: If `smart_fetch` fails or finds "JS Required" signals, it spawns a headless browser.


3. **Interface Layer:** CLI (Rich), MCP (JSON-RPC), or Python API.

---

## ⚙️ Configuration

WebSearx uses environment variables for easy config:

| Variable | Description | Default |
| --- | --- | --- |
| `SEARXNG_HOST` | URL of your SearXNG instance | `http://127.0.0.1:8080` |
| `CURL_CFFI_LOG_LEVEL` | Suppress noisy library logs | `ERROR` |

---

## ⚖️ Licensing & Open Source

This project is open-source. It orchestrates several powerful tools:

* **SearXNG:** AGPL-3.0
* **Trafilatura:** GPL-3.0
* **Playwright:** Apache-2.0

As a `docker-compose` aggregation, you can use and modify this stack freely for personal or research use.