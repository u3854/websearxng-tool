import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Literal, Optional
import ddgs
import requests
import trafilatura
from pdfminer.high_level import extract_text
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(Path(__file__).stem)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36"
    )
}

SEARX_HOST = "http://127.0.0.1:8080"


class Result(BaseModel):
    url: str = Field(..., alias="href")
    title: str
    snippet: Optional[str] = Field(..., description="Short snippet from web page")
    full_content: Optional[str] = Field(
        None, description="Fully extracted text content from webpage"
    )

    @model_validator(mode="before")
    @classmethod  # Best practice for mode='before' to use @classmethod
    def handle_aliases(cls, values):
        # 1. Ensure values is a dict (just in case)
        if not isinstance(values, dict):
            return values
            
        # 2. Handle aliases
        if "body" in values:
            values["snippet"] = values["body"]
        elif "content" in values:
            values["snippet"] = values["content"]
            
        # 3. CRITICAL: Return the modified values
        return values


# -----------------------------------------------------------------------

class WebSearchAgent():
    _TIME_RANGE = Literal["day", "month", "year"]
    _AGENTS = Literal["searxng", "ddgs"]
    
    def __init__(self,
                 query: Optional[str] = "",
                 time_range: Optional[_TIME_RANGE] = None,
                 max_results: int = 4,
                 agent: _AGENTS = "searxng"):
        self.query = query
        self.time_range = time_range
        self.max_results = max_results
        self.agent_name = agent # Store name to check logic later
        self.switch_and_retry = True
        self.agent_func = self._check_agent(agent) # Bind function

    def _check_agent(self, agent: _AGENTS):
        """Returns the search agent instance function"""
        if agent == "ddgs":
            return self.ddgs_search
            
        try:
            res = requests.get(SEARX_HOST + "/config", timeout=2)
            if res.ok and ("engines" in res.text):
                logger.debug("Using Searxng Host to search")
                return self.searxng_search
        except requests.exceptions.ConnectionError:
            pass
            
        logger.debug("Searxng unavailable. Defaulting to DDGS.")
        return self.ddgs_search
        
    def _searxng_params(self) -> dict:
        return {
            "q": self.query,
            "format": "json",
            "time_range": self.time_range
        }

    def searxng_search(self, query: Optional[str] = None) -> List[Result] | None:
        if query is not None:
            self.query = query
        if not self.query.strip():
            raise ValueError("Search query cannot be NULL")

        url = SEARX_HOST + "/search"
        try:
            res = requests.get(url, params=self._searxng_params())
            if res.status_code == 200:
                results_dict: dict = json.loads(res.text)
                results = results_dict.get("results", [])
                self.switch_and_retry = True 
                return [Result(**result) for result in results][:self.max_results]
            else:
                logger.error(f"Searxng error {res.status_code}")
                # Trigger fallback
                raise Exception("Searxng Error")
        except Exception:
            if self.switch_and_retry:
                self.switch_and_retry = False
                logger.info("Retrying with DDGS")
                return self.ddgs_search(query)
            return []

    def _ddgs_params(self) -> dict:
        mapping = {"day": "d", "month": "m", "year": "y"}
        return {
            "query": self.query,
            "timelimit": mapping.get(self.time_range),
            "max_results": self.max_results
        }

    def ddgs_search(self, query: Optional[str] = None) -> List[Result] | None:
        if query is not None:
            self.query = query
        if not self.query.strip():
            raise ValueError("Search query cannot be NULL")
        try:
            results = ddgs.DDGS().text(**self._ddgs_params())
            res = [Result(**result) for result in results][:self.max_results]
            self.switch_and_retry = True
            return res
        except Exception as e:
            logger.error(f"DDGS search error: {e}")
            if self.switch_and_retry and self.agent_name != "searxng":
                self.switch_and_retry = False
                logger.info("Retrying with SEARXNG")
                return self.searxng_search(query)
            return []


# -----------------------------------------------------------------------

def fetch_rendered_text(urls: Dict[int, str]) -> Dict:
    """Attempt to fetch a JS-rendered webpage with Playwright."""
    content = {}
    if not urls:
        return content

    with sync_playwright() as p:
        logger.info("Launching chromium browser instance")
        browser = p.chromium.launch(headless=True)
        # Create a context to share user-agent
        context = browser.new_context(user_agent=HEADERS["User-Agent"])
        
        for index, target_url in urls.items():
            try:
                page = context.new_page()
                # Increased timeout and changed wait condition
                page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                html = page.content()
                
                text = trafilatura.extract(html, target_url)
                content[index] = text if text else ""
                page.close()
            except Exception as e:
                logger.error(f"Playwright error for {target_url}: {e}")
                content[index] = ""
                
        browser.close()
        logger.info("Closing chromium browser instance")
    return content


class UrlContent():
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
        # If it's single mode, we still need to increment index to maintain order logic, 
        # though 'text' variable handling is slightly different.

    def dump(self) -> str | dict:
        if self.pw_queue:
            content = fetch_rendered_text(self.pw_queue)
            if self.is_dict:
                self.text.update(content)
            else:
                # If single URL and it went to queue, return that single result
                if 0 in content:
                    self.text = content[0]
        return self.text


# SUB-TOOL
def get_url_content(url: str | List[str]) -> str | Dict[int, str]:
    """Gets text content from the webpage at the url"""
    
    # Normalize to list
    if isinstance(url, str):
        urls = [url]
    else:
        urls = url
        
    n = len(urls)
    content = UrlContent(n)

    # and to handle indexing correctly.
    for current_url in urls:
        try:
            # HEAD request
            head = requests.head(
                current_url, headers=HEADERS, allow_redirects=True, timeout=10
            )
            content_type = head.headers.get("Content-Type", "").lower()

            # Case 1: PDF
            if "pdf" in content_type:
                logger.debug(f"PDF detected: {current_url}")
                # FIX: Pass 'current_url', not the list 'url'
                r = requests.get(
                    current_url, headers=HEADERS, allow_redirects=True, timeout=30
                )
                text = extract_text(BytesIO(r.content)) 
                content.add_text(text)

            # Case 2: HTML or other text-based
            else:
                # FIX: Pass 'current_url'
                downloaded = trafilatura.fetch_url(current_url)
                if downloaded:
                    text = trafilatura.extract(downloaded)
                    if text:
                        if ("enable javascript" in text.lower() 
                                or "javascript to run this app" in text.lower()):
                            logger.debug(f"JS site detected: {current_url}")
                            content.add_to_queue(current_url)
                        else:
                            content.add_text(text)
                    else:
                        # trafilatura fetched but couldn't extract -> try playwright
                        content.add_to_queue(current_url)
                else:
                    # trafilatura failed to fetch -> try playwright
                    content.add_to_queue(current_url)
                    
        except Exception as e:
            logger.error(f"Error processing {current_url}: {e}")
            content.add_to_queue(current_url)

    return content.dump()


# MAIN-TOOL
def web_search(
    query: str,
    time_range: Optional[Literal["day", "month", "year"]] = None,
    full_content: bool = False,
    max_results: int = 5,
) -> str:
    """Returns search results from web."""
    
    agent = WebSearchAgent(
            query=query, 
            time_range=time_range, 
            max_results=max_results
        )
        
    # Execute the selected agent function
    if agent.agent_func:
        results = agent.agent_func(query)
    else:
        results = agent.ddgs_search(query)

    if not results:
        return "No results found."

    # If full_content requested, scrape the URLs found
    if full_content:
        logger.info("Fetching full content for results...")
        urls = [r.url for r in results]
        scraped_data = get_url_content(urls)
        
        # Merge scraped text into results
        if isinstance(scraped_data, dict):
            for i, result in enumerate(results):
                # Ensure we match the index logic from UrlContent
                if i in scraped_data:
                    result.full_content = scraped_data[i]

    return json.dumps([r.model_dump(exclude_none=True) for r in results], indent=2)


if __name__ == "__main__":
    # Test 1: Single URL Scrape
    url = "https://docs.pydantic.dev/latest/logo-white.svg" # This is an SVG, might fail text extract
    print(f"Testing URL: {url}")
    # text = get_url_content(url)
    # print(text)
    
    # Test 2: Search
    print("\nTesting Search:")
    try:
        res = web_search("python pydantic tutorial", full_content=False, max_results=2)
        print(res)
    except Exception as e:
        print(f"Search failed: {e}")