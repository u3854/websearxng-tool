import requests
from io import BytesIO
from pdfminer.high_level import extract_text
import trafilatura
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36"
    )
}


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


def fetch_text_from_url(url: str) -> str:
    """Download URL and extract clean text (PDF -> pdfminer, HTML -> trafilatura). Fallback to playwright or if JS text detected."""

    # HEAD request to check content type (like curl -I -L -A)
    head = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=15)
    content_type = head.headers.get("Content-Type", "").lower()

    # Case 1: PDF
    if "pdf" in content_type:
        print("[ pdf detected ]")
        r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=30)
        text = extract_text(BytesIO(r.content))
        return text.strip()

    # Case 2: HTML or other text-based
    else:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                if "enable javascript" in text.lower() or "javascript to run this app" in text.lower():
                    text = fetch_rendered_text(url) or ""
                return text.strip()

    # Case 3: Fallback → Playwright (JS-heavy site)
    return fetch_rendered_text(url) or ""

if __name__ == "__main__":
    url = "https://arxiv.org/pdf/2402.06196"

    text = fetch_text_from_url(url)
    print(text)
