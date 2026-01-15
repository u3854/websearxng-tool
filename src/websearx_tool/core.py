import logging
import os
from io import BytesIO
from typing import Dict, List, Literal, Optional, Union

# Third-party imports
from ddgs import DDGS
import requests
import trafilatura
from pdfminer.high_level import extract_text
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field, model_validator

# Configure Logging
logger = logging.getLogger("websearx_tool")

# Read from env var "SEARXNG_HOST", default to localhost if not set
SEARX_HOST = os.getenv("SEARXNG_HOST", "http://127.0.0.1:8080")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36"
    )
}

class Result(BaseModel):
    # Allow input to be 'href' OR 'url'
    url: str = Field(..., alias="href") 
    title: str
    snippet: Optional[str] = Field(None, description="Short snippet from web page")
    full_content: Optional[str] = Field(None, description="Fully extracted text content from webpage")

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, values):
        if isinstance(values, dict):
            # Map 'body' or 'content' to 'snippet'
            if "body" in values:
                values["snippet"] = values["body"]
            elif "content" in values:
                values["snippet"] = values["content"]
            
            # Map 'url' to 'href' if 'href' is missing
            if "url" in values and "href" not in values:
                values["href"] = values["url"]
        return values

class WebSearchAgent:
    _TIME_RANGE = Literal["day", "month", "year"]
    _AGENTS = Literal["searxng", "ddgs"]
    
    def __init__(self, query: str = "", time_range: Optional[_TIME_RANGE] = None, max_results: int = 4, agent: _AGENTS = "searxng"):
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
        # FIXED: Changed 'keywords' to 'query' to match ddgs 9.x API
        return {"query": self.query, "timelimit": mapping.get(self.time_range), "max_results": self.max_results}

    def ddgs_search(self, query: Optional[str] = None) -> List[Result]:
        if query: 
            self.query = query
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(**self._ddgs_params()))
            
            return [Result(**r) for r in results][:self.max_results]
        except Exception as e:
            logger.error(f"DDGS search error: {e}")
            if self.switch_and_retry and self.agent_name != "searxng":
                self.switch_and_retry = False
                return self.searxng_search(query)
            return []

def smart_fetch(url: str) -> Optional[str]:
    """
    Attempts to fetch content via Requests/PDFMiner/Trafilatura.
    Returns the text if successful, or None if it requires a browser (Playwright).
    """
    try:
        head = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=10)
        content_type = head.headers.get("Content-Type", "").lower()

        if "pdf" in content_type:
            r = requests.get(url, headers=HEADERS, timeout=30)
            return extract_text(BytesIO(r.content))
        
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and ("enable javascript" not in text.lower()):
                return text
    except Exception as e:
        logger.warning(f"Smart fetch failed for {url}: {e}")
    
    return None

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
                text = trafilatura.extract(page.content(), url=target_url)
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