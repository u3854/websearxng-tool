import json
import logging
from typing import List, Union, Optional

from websearx_tool.core import WebSearchAgent, UrlContent, smart_fetch

logger = logging.getLogger("websearx_tool.tools")

def get_url_content(urls: Union[str, List[str]]) -> Union[str, dict]:
    """
    Extracts text content from one or multiple URLs.
    Handles PDFs, HTML, and JS-rendered pages automatically.
    
    Args:
        urls: A single URL string or a list of URL strings.
    
    Returns:
        If input is single URL -> str (content)
        If input is list -> dict {index: content}
    """
    # 1. Sanitize Inputs
    url_list = []

    if isinstance(urls, str):
        cleaned = urls.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                parsed = json.loads(cleaned)
                url_list = parsed if isinstance(parsed, list) else [cleaned]
            except Exception:
                try:
                    parsed = json.loads(cleaned.replace("'", '"'))
                    url_list = parsed if isinstance(parsed, list) else [cleaned]
                except Exception:
                    url_list = [cleaned]
        elif "," in cleaned:
             url_list = [u.strip() for u in cleaned.split(",") if u.strip()]
        else:
            url_list = [cleaned]
    elif isinstance(urls, list):
        url_list = urls
    
    # Ensure clean list of strings
    url_list = [str(u) for u in url_list if u]
    
    # 2. Run Scraping Logic
    n = len(url_list)
    content = UrlContent(n)

    for current_url in url_list:
        # Try fast fetch (Requests/Trafilatura/PDF)
        fetched_text = smart_fetch(current_url)
        
        if fetched_text:
            content.add_text(fetched_text)
        else:
            # Fallback to slow fetch (Playwright)
            content.add_to_queue(current_url)

    result = content.dump()
    return result

def web_search(
    query: str,
    time_range: Optional[str] = None,
    full_content: bool = False,
    max_results: int = 5,
) -> List[dict]:
    """
    Performs a web search and optionally scrapes the content.
    Returns a list of dictionaries (not a JSON string).
    """
    # 1. Sanitize Inputs
    valid_ranges = ["day", "month", "year"]
    if time_range is None:
        pass
    elif isinstance(time_range, str):
        if time_range.lower() == "null" or time_range not in valid_ranges:
            time_range = None
            
    # 2. Run Search
    agent = WebSearchAgent(query=query, time_range=time_range, max_results=max_results)
    results = agent.agent_func(query) if agent.agent_func else agent.ddgs_search(query)

    if not results:
        return []

    # 3. Optional Scraping
    if full_content:
        urls = [r.url for r in results]
        scraped_data = get_url_content(urls)
        
        if isinstance(scraped_data, dict):
            scraped_map = {int(k): v for k, v in scraped_data.items()}
            for i, result in enumerate(results):
                if i in scraped_map:
                    result.full_content = scraped_map[i]
        elif isinstance(scraped_data, str) and len(results) == 1:
             results[0].full_content = scraped_data

    return [r.model_dump(exclude_none=True) for r in results]