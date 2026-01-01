import json
import logging
from io import BytesIO
from typing import Dict, List, Literal, Optional, Union

# Third-party imports
import ddgs
import requests
import trafilatura
from pdfminer.high_level import extract_text
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field, model_validator
from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("WebSearchScraper")

logger = logging.getLogger("server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logging.getLogger("primp").setLevel(logging.WARNING)
logging.getLogger("trafilatura").setLevel(logging.WARNING)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36"
    )
}

SEARX_HOST = "http://127.0.0.1:8080"

# --- Data Models & Helper Classes (Unchanged) ---

class Result(BaseModel):
    url: str = Field(..., alias="href")
    title: str
    snippet: Optional[str] = Field(None, description="Short snippet from web page")
    full_content: Optional[str] = Field(None, description="Fully extracted text content from webpage")

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, values):
        if isinstance(values, dict):
            if "body" in values:
                values["snippet"] = values["body"]
            elif "content" in values:
                values["snippet"] = values["content"]
        return values

class WebSearchAgent:
    # (Same as your previous code, kept for brevity)
    _TIME_RANGE = Literal["day", "month", "year"]
    _AGENTS = Literal["searxng", "ddgs"]
    
    def __init__(self, query: Optional[str] = "", time_range: Optional[_TIME_RANGE] = None, max_results: int = 4, agent: _AGENTS = "searxng"):
        self.query = query
        self.time_range = time_range
        self.max_results = max_results
        self.agent_name = agent
        self.switch_and_retry = True
        self.agent_func = self._check_agent(agent)

    def _check_agent(self, agent: _AGENTS):
        if agent == "ddgs": 
            return self.ddgs_search
        try:
            res = requests.get(SEARX_HOST + "/config", timeout=2)
            if res.ok and ("engines" in res.text): 
                return self.searxng_search
        except requests.exceptions.ConnectionError: 
            pass
        return self.ddgs_search
        
    def _searxng_params(self) -> dict:
        return {"q": self.query, "format": "json", "time_range": self.time_range}

    def searxng_search(self, query: Optional[str] = None) -> List[Result]:
        if query: 
            self.query = query
        try:
            res = requests.get(SEARX_HOST + "/search", params=self._searxng_params())
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                self.switch_and_retry = True 
                return [Result(**r) for r in results][:self.max_results]
            raise Exception("Searxng Error")
        except Exception:
            if self.switch_and_retry:
                self.switch_and_retry = False
                logger.info("Retrying with DDGS")
                return self.ddgs_search(query)
            return []

    def _ddgs_params(self) -> dict:
        mapping = {"day": "d", "month": "m", "year": "y"}
        return {"query": self.query, "timelimit": mapping.get(self.time_range), "max_results": self.max_results}

    def ddgs_search(self, query: Optional[str] = None) -> List[Result]:
        if query: 
            self.query = query
        try:
            results = ddgs.DDGS().text(**self._ddgs_params())
            res = [Result(**r) for r in results][:self.max_results]
            self.switch_and_retry = True
            return res
        except Exception as e:
            logger.error(f"DDGS search error: {e}")
            if self.switch_and_retry and self.agent_name != "searxng":
                self.switch_and_retry = False
                return self.searxng_search(query)
            return []

def fetch_rendered_text(urls: Dict[int, str]) -> Dict:
    content = {}
    if not urls: 
        return content
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=HEADERS["User-Agent"])
        for index, target_url in urls.items():
            try:
                page = context.new_page()
                page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                text = trafilatura.extract(page.content(), target_url)
                content[index] = text if text else ""
                page.close()
            except Exception as e:
                logger.error(f"Playwright error for {target_url}: {e}")
                content[index] = ""
        browser.close()
    return content

class UrlContent:
    def __init__(self, n: int):
        self.text = {} if n > 1 else ""
        self.index = 0
        self.pw_queue = {}
        self.is_dict = n > 1

    def add_text(self, text: str):
        if self.is_dict: 
            self.text[self.index] = text
        else: 
            self.text = text
        self.index += 1
    
    def add_to_queue(self, url: str):
        self.pw_queue[self.index] = url
        self.index += 1

    def dump(self) -> Union[str, Dict]:
        if self.pw_queue:
            content = fetch_rendered_text(self.pw_queue)
            if self.is_dict: 
                self.text.update(content)
            else: 
                if 0 in content: 
                    self.text = content[0]
        return self.text

# --- UPDATED MCP TOOLS ---

@mcp.tool()
def get_url_content(urls: Union[str, List[str]]) -> str:
    """
    Extracts text content from one or multiple URLs.
    Handles PDFs, HTML, and JS-rendered pages automatically.
    
    CRITICAL: If you need to read multiple pages, pass a LIST of strings 
    (e.g. urls=['http...', 'http...']) in a SINGLE function call. 
    DO NOT generate multiple function calls separated by semicolons.
    
    Args:
        urls: A single URL string or a list of URL strings.
    """
    # --- 1. Sanitize Inputs ---
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
    
    # --- 2. Scraping Logic ---
    n = len(url_list)
    content = UrlContent(n)

    for current_url in url_list:
        try:
            # Quick Check: Is it a PDF?
            head = requests.head(current_url, headers=HEADERS, allow_redirects=True, timeout=10)
            content_type = head.headers.get("Content-Type", "").lower()

            if "pdf" in content_type:
                r = requests.get(current_url, headers=HEADERS, timeout=30)
                text = extract_text(BytesIO(r.content)) 
                content.add_text(text)
            else:
                downloaded = trafilatura.fetch_url(current_url)
                if downloaded:
                    text = trafilatura.extract(downloaded)
                    if text and ("enable javascript" not in text.lower()):
                        content.add_text(text)
                    else:
                        content.add_to_queue(current_url)
                else:
                    content.add_to_queue(current_url)
        except Exception as e:
            logger.error(f"Error processing {current_url}: {e}")
            content.add_to_queue(current_url)

    result = content.dump()
    return json.dumps(result) if isinstance(result, dict) else str(result)

@mcp.tool()
def web_search(
    query: str,
    time_range: Union[str, None] = None,
    full_content: Union[bool, str] = False,
    max_results: Union[int, str, None] = 5,  # ALLOW NONE HERE
) -> str:
    """
    Performs a web search and optionally scrapes the content.
    
    Args:
        query: The search query.
        time_range: Filter by 'day', 'month', 'year' (or null).
        full_content: If True, visits results and extracts text.
        max_results: Max results to return (default 5).
    """
    # --- 1. Sanitize Inputs ---
    
    # Fix time_range (Handle "null" string or None)
    valid_ranges = ["day", "month", "year"]
    if time_range is None:
        pass
    elif isinstance(time_range, str):
        if time_range.lower() == "null" or time_range not in valid_ranges:
            time_range = None
            
    # Fix full_content (Handle "true"/"false" strings)
    if isinstance(full_content, str):
        full_content = full_content.lower() == "true"
        
    # Fix max_results (Handle None, "null", or "5")
    if max_results is None:
        max_results = 5
    elif isinstance(max_results, str):
        if max_results.lower() == "null":
            max_results = 5
        else:
            try:
                max_results = int(max_results)
            except ValueError:
                max_results = 5
            
    # --- 2. Run Search ---
    agent = WebSearchAgent(query=query, time_range=time_range, max_results=max_results)
    results = agent.agent_func(query) if agent.agent_func else agent.ddgs_search(query)

    if not results:
        return "No results found."

    if full_content:
        urls = [r.url for r in results]
        scraped_json = get_url_content(urls) 
        scraped_data = json.loads(scraped_json)
        
        if isinstance(scraped_data, dict):
            scraped_map = {int(k): v for k, v in scraped_data.items()}
            for i, result in enumerate(results):
                if i in scraped_map:
                    result.full_content = scraped_map[i]

    return json.dumps([r.model_dump(exclude_none=True) for r in results], indent=2)

if __name__ == "__main__":
    mcp.run()