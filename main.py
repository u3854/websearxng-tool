from io import BytesIO
from typing import Literal, Optional

import requests
import trafilatura
from pdfminer.high_level import extract_text
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36"
    )
}

SEARX_HOST = "http://127.0.0.1:8080"


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
    format: Literal["json"] = "json",
    full_content: bool = False,
    max_results: int = 4,
) -> str:
    """Returns search results from web.

    Args:
        query (str): Search query.
        time_range (Optional[Literal[&quot;day&quot;, &quot;month&quot;, &quot;year&quot;]], optional): Get results from last day/month/year. Defaults to None.
        format (Literal[&quot;json&quot;], optional): Search result format. Defaults to "json".
        full_content (bool, optional): Whether to include full content from url or just snippets. Defaults to False.
        max_results (int, optional): Top n search results. Defaults to 4.

    Returns:
        str: Search results.
    """


if __name__ == "__main__":
    url = "https://docs.pydantic.dev/latest/logo-white.svg"

    text = get_url_content(url)
    print(text)
    print(text)
    print(text)
    print(text)
    print(text)
