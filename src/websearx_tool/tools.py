from typing import List, Union, Optional
from websearx_tool.core import WebSearchAgent, UrlContent, smart_fetch

def get_url_content(urls: Union[str, List[str]]) -> Union[str, dict]:
    url_list = [urls] if isinstance(urls, str) else urls
    content_manager = UrlContent(len(url_list))

    for url in url_list:
        text = smart_fetch(url)
        if text:
            content_manager.add_text(text)
        else:
            content_manager.add_to_queue(url)

    return content_manager.dump()

def web_search(
    query: str,
    time_range: Optional[str] = None,
    full_content: bool = False,
    max_results: int = 5,
) -> List[dict]:
    agent = WebSearchAgent(time_range=time_range, max_results=max_results)
    results = agent.search(query)

    if full_content and results:
        urls = [r.url for r in results]
        scraped = get_url_content(urls)
        if isinstance(scraped, dict):
            for i, res in enumerate(results):
                res.full_content = scraped.get(i)

    return [r.model_dump(exclude_none=True) for r in results]