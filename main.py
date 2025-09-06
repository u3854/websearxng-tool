import json
import logging
from io import BytesIO
from pathlib import Path
from typing import List, Literal, Optional
import ddgs
import requests
import trafilatura
from pdfminer.high_level import extract_text
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(Path(__file__).stem)

logging.basicConfig(
    level=logging.DEBUG,
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
    def handle_aliases(cls, values):
        if "body" in values:
            values["snippet"] = values["body"]
        elif "content" in values:
            values["snippet"] = values["content"]


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
        self.agent = self._check_agent(agent)
        self.switch_and_retry = True


    def _check_agent(self, agent: _AGENTS):
        """Returns the search agent instance
        """
        if agent == "ddgs":
            return self.ddgs_search
        res = requests.get(SEARX_HOST + "/config")
        if res.ok and ("engines" in res.text):
            logger.debug("Using Searxng Host to search")
            return self.searxng_search
        else:
            logger.debug("Using DDGS to seach")
            return
        
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
            error_msg = "Search query cannot be NULL"
            logger.error(error_msg)
            raise ValueError(error_msg)
        # ------------------ SEARCH REQUEST ----------------------
        url = SEARX_HOST + "/search"
        res = requests.get(url, params=self._searxng_params())
        if res.status_code == 200:
            results_dict: dict = json.loads(res.text)
            results = results_dict.get("results", [])
            logger.debug(f"Searxng returned {len(results)} results")
            self.switch_and_retry = True # reset in case same instance is reused
            # return `max_results` no. of results
            return [Result(**result) for result in results][:self.max_results]
        else:
            logger.error(f"Searxng response code {res.status_code}: {res.text}")
            if self.switch_and_retry:
                self.switch_and_retry = False
                logger.info("Retrying with DDGS")
                self.ddgs_search(query)

    
    def _ddgs_params(self) -> dict:
        mapping = {
            "day": "d",
            "month": "m",
            "year": "y"
        }
        return {
            "query": self.query,
            "timelimit": mapping.get(self.time_range),
            "max_results": self.max_results
        }


    def ddgs_search(self, query: Optional[str] = None) -> List[Result] | None:
        if query is not None:
            self.query = query
        if not self.query.strip():
            error_msg = "Search query cannot be NULL"
            logger.error(error_msg)
            raise ValueError(error_msg)
        try:
            results = ddgs.DDGS().text(**self._ddgs_params())
            res = [Result(**result) for result in results][:self.max_results]
            if len(res) == 0:
                raise ValueError("0 results returned from DDGS search")
            self.switch_and_retry = True # reset in case same instance is reused
        except Exception as e:
            logger.error(f"DDGS search error: {e}")
            if self.switch_and_retry:
                self.switch_and_retry = False
                logger.info("Retrying with SEARXNG")
                self.searxng_search(query)



# -----------------------------------------------------------------------



def fetch_rendered_text(url: str) -> str | None:
    """Attempt to fetch a JS-rendered webpage with Playwright and clean it using Trafilatura."""
    with sync_playwright() as p:
        print("[ launching chromium browser instance ]")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")  # wait until network is idle
        html = page.content()  # get fully rendered HTML
        browser.close()

    # Pass rendered HTML to Trafilatura
    text = trafilatura.extract(html, url)
    return text


# SUB-TOOL
def get_url_content(url: str) -> str:
    """Extract **text** content from url
    Args:
        url (str): web page url

    Returns:
        str: text content from web page
    """

    # HEAD request to check content type (like curl -I -L -A)
    head: requests.Response = requests.head(
        url, headers=HEADERS, allow_redirects=True, timeout=15
    )
    content_type: str = head.headers.get("Content-Type", "").lower()

    # Case 1: PDF
    if "pdf" in content_type:
        print("[ pdf detected ]")
        r: requests.Response = requests.get(
            url, headers=HEADERS, allow_redirects=True, timeout=30
        )
        text = extract_text(BytesIO(r.content))
        return text.strip()

    # Case 2: HTML or other text-based
    else:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                if (
                    "enable javascript" in text.lower()
                    or "javascript to run this app" in text.lower()
                ):
                    text = fetch_rendered_text(url) or ""
                return text.strip()

    # Case 3: Fallback → Playwright (JS-heavy site)
    return fetch_rendered_text(url) or ""


# MAIN-TOOL
def web_search(
    query: str,
    time_range: Optional[Literal["day", "month", "year"]] = None,
    full_content: bool = False,
    max_results: int = 5,
) -> str:
    """Returns search results from web.

    Args:
        query (str): Search query.
        time_range (Optional[Literal[&quot;day&quot;, &quot;month&quot;, &quot;year&quot;]], optional): Get results from last day/month/year. Defaults to None.
        format (Literal[&quot;json&quot;], optional): Search result format. Defaults to "json".
        max_results (int, optional): Top n search results. Defaults to 4.

    Returns:
        str: Search results.
    """


if __name__ == "__main__":
    url = "https://docs.pydantic.dev/latest/logo-white.svg"

    # text = get_url_content(url)
    # print(text)
    print(__name__)
