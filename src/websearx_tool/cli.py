import argparse
import json
import sys
import logging
import os

# Suppress logs BEFORE importing libraries that might initialize them
os.environ["CURL_CFFI_LOG_LEVEL"] = "ERROR" 

# Configure standard logging to be silent for 3rd party libs
logging.basicConfig(level=logging.CRITICAL)
for lib in ["curl_cffi", "httpx", "ddgs", "urllib3", "httpcore", "trafilatura", "primp"]:
    logging.getLogger(lib).setLevel(logging.CRITICAL)

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.box import ROUNDED
from rich.console import Group

from websearx_tool.tools import web_search, get_url_content

console = Console()

def display_search_results(results):
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    for i, res in enumerate(results, 1):
        title = res.get('title', 'No Title')
        url = res.get('url', res.get('href', 'No URL'))
        
        content_body = []
        
        snippet = res.get('snippet')
        if snippet:
            content_body.append(Text(snippet, style="bright_white"))

        full_text = res.get('full_content')
        if full_text:
            content_body.append(Text("\n\n--- Full Scraped Content ---\n", style="bold cyan"))
            content_body.append(Markdown(full_text))

        final_content = Group(*content_body)

        panel = Panel(
            final_content,
            title=f"[bold green]{i}. {title}[/bold green]",
            subtitle=f"[cyan]{url}[/cyan]",
            subtitle_align="right",
            box=ROUNDED,
            expand=False,
            border_style="blue"
        )
        console.print(panel)
        console.print("")

def display_scrape_results(data):
    if isinstance(data, dict):
        for idx, content in data.items():
            panel = Panel(
                Markdown(content),
                title=f"[bold magenta]Source {idx}[/bold magenta]",
                box=ROUNDED,
                border_style="magenta"
            )
            console.print(panel)
    else:
        panel = Panel(
            Markdown(data),
            title="[bold magenta]Scraped Content[/bold magenta]",
            box=ROUNDED,
            border_style="magenta"
        )
        console.print(panel)

def main():
    parser = argparse.ArgumentParser(description="Web Search & Scraping Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Search Command
    search_parser = subparsers.add_parser(
        "search", 
        help="Search the web (default)",
        description="Search the web. (Note: To scrape specific URLs without searching, use 'websearx scrape')"
    )
    search_parser.add_argument("query", help="Search query string")
    search_parser.add_argument("--time", "-t", choices=["day", "month", "year"], help="Time range")
    search_parser.add_argument("--limit", "-l", type=int, default=5, help="Max results")
    search_parser.add_argument("--scrape", "-s", action="store_true", help="Scrape content of results")
    search_parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON")

    # Scrape Command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape URLs directly")
    scrape_parser.add_argument("urls", nargs="+", help="One or more URLs to scrape")
    scrape_parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON")

    # If NO arguments are passed, print help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # If arguments exist but don't match a command, default to "search"
    if len(sys.argv) > 1 and sys.argv[1] not in ["search", "scrape", "-h", "--help"]:
        sys.argv.insert(1, "search")

    args = parser.parse_args()

    # --- EXECUTION ---
    if args.command == "search":
        if not args.json:
            with console.status(f"[bold green]Searching for: {args.query}...[/bold green]", spinner="dots"):
                results = web_search(args.query, args.time, args.scrape, args.limit)
        else:
            results = web_search(args.query, args.time, args.scrape, args.limit)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            display_search_results(results)

    elif args.command == "scrape":
        if not args.json:
            with console.status(f"[bold magenta]Scraping {len(args.urls)} URL(s)...[/bold magenta]", spinner="dots"):
                data = get_url_content(args.urls)
        else:
             data = get_url_content(args.urls)
        
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            display_scrape_results(data)

if __name__ == "__main__":
    main()