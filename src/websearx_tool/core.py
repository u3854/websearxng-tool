import logging
import os
import requests
import trafilatura
from io import BytesIO
from typing import Dict, List, Optional, Union
from ddgs import DDGS
from pdfminer.high_level import extract_text
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("websearx_tool")
SEARX_HOST = os.getenv("SEARXNG_HOST", "http://127.0.0.1:8080")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

class Result(BaseModel):
    url: str = Field(..., alias="href") 
    title: str
    snippet: Optional[str] = None
    full_content: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, values):
        if isinstance(values, dict):
            for k in ["body", "content", "snippet"]:
                if k in values:
                    values["snippet"] = values.pop(k)
            if "url" in values and "href" not in values:
                values["href"] = values["url"]
        return values

class WebSearchAgent:
    def __init__(self, time_range: Optional[str] = None, max_results: int = 5):
        self.time_range = time_range
        self.max_results = max_results

    def search(self, query: str) -> List[Result]:
        try:
            return self._searxng_search(query)
        except Exception as e:
            logger.warning(f"SearxNG failed, trying DDGS: {e}")
            return self._ddgs_search(query)

    def _searxng_search(self, query: str) -> List[Result]:
        params = {"q": query, "format": "json", "time_range": self.time_range}
        res = requests.get(f"{SEARX_HOST}/search", params=params, timeout=5)
        res.raise_for_status()
        results = res.json().get("results", [])
        return [Result(**r) for r in results][:self.max_results]

    def _ddgs_search(self, query: str) -> List[Result]:
        mapping = {"day": "d", "month": "m", "year": "y"}
        with DDGS() as ddgs:
            results = list(ddgs.text(
                keywords=query, 
                timelimit=mapping.get(self.time_range), 
                max_results=self.max_results
            ))
        return [Result(**r) for r in results]

def smart_fetch(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if "application/pdf" in r.headers.get("Content-Type", ""):
            return extract_text(BytesIO(r.content))
        
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and "javascript" not in text.lower()[:200]:
                return text
    except Exception as e:
        logger.debug(f"Smart fetch skipped {url}: {e}")
    return None

def browser_fetch(urls: Dict[int, str]) -> Dict[int, str]:
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=HEADERS["User-Agent"])
        for idx, url in urls.items():
            try:
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                results[idx] = trafilatura.extract(page.content()) or ""
                page.close()
            except Exception as e:
                logger.error(f"Playwright failed for {url}: {e}")
                results[idx] = ""
        browser.close()
    return results

class UrlContent:
    def __init__(self, n: int):
        self.is_dict = n > 1
        self.text = {} if self.is_dict else ""
        self.index = 0
        self.pw_queue = {}

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
            rendered = browser_fetch(self.pw_queue)
            if self.is_dict: 
                self.text.update(rendered)
            elif 0 in rendered: 
                self.text = rendered[0]
        return self.text