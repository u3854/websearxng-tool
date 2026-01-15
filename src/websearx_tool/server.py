import json
import logging
from typing import Union, List
from fastmcp import FastMCP
from websearx_tool.tools import web_search as run_search
from websearx_tool.tools import get_url_content as run_scrape

# Initialize FastMCP Server
mcp = FastMCP("WebSearchScraper")

# Configure basic logging for the server
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logging.getLogger("primp").setLevel(logging.WARNING)
logging.getLogger("trafilatura").setLevel(logging.WARNING)

@mcp.tool()
def get_url_content(urls: Union[str, List[str]]) -> str:
    """
    Extracts text content from one or multiple URLs.
    Handles PDFs, HTML, and JS-rendered pages automatically.
    
    Args:
        urls: A single URL string or a list of URL strings.
    """
    result = run_scrape(urls)
    return json.dumps(result) if isinstance(result, dict) else str(result)

@mcp.tool()
def web_search(
    query: str,
    time_range: Union[str, None] = None,
    full_content: Union[bool, str] = False,
    max_results: Union[int, str, None] = 5,
) -> str:
    """
    Performs a web search and optionally scrapes the content.
    
    Args:
        query: The search query.
        time_range: Filter by 'day', 'month', 'year' (or null).
        full_content: If True, visits results and extracts text.
        max_results: Max results to return (default 5).
    """
    # FastMCP/LLMs sometimes pass "true"/"false" strings instead of bools
    if isinstance(full_content, str):
        full_content = full_content.lower() == "true"
        
    # Handle string integers
    if isinstance(max_results, str):
        if max_results.lower() == "null":
            max_results = 5
        else:
            try:
                max_results = int(max_results)
            except ValueError:
                max_results = 5
    elif max_results is None:
        max_results = 5

    results = run_search(
        query=query, 
        time_range=time_range, 
        full_content=full_content, 
        max_results=max_results
    )
    
    if not results:
        return "No results found."

    return json.dumps(results, indent=2)

def main():
    """Entry point for running the server directly."""
    mcp.run()

if __name__ == "__main__":
    main()