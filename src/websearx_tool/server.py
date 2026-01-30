import json
import logging
from typing import Union, List, Optional, Literal
from fastmcp import FastMCP
from websearx_tool.tools import web_search as run_search
from websearx_tool.tools import get_url_content as run_scrape

# Configure logging
logging.basicConfig(level=logging.INFO)
for lib in ["httpcore", "httpx", "trafilatura", "playwright"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

mcp = FastMCP("WebSearchScraper")

@mcp.tool()
def scrape_urls(urls: List[str]) -> str:
    """Extracts text content from a list of URLs."""
    return json.dumps(run_scrape(urls))

@mcp.tool()
def web_search(
    query: str,
    time_range: Optional[Literal["day", "month", "year"]] = None,
    full_content: bool = False,
    max_results: int = 5,
) -> str:
    """Search the web and optionally scrape full content."""
    results = run_search(query, time_range, full_content, max_results)
    return json.dumps(results, indent=2) if results else "No results found."

def main():
    """Entry point for the Docker container."""
    # CRITICAL CHANGE: 
    # 1. transport="sse" -> Starts a web server instead of a command-line pipe
    # 2. host="0.0.0.0"  -> Listens on all Docker network interfaces (required for containers)
    # 3. port=8000       -> Matches your docker-compose ports
    mcp.run(transport="sse", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()