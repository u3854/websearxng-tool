import argparse
import json
import sys
import logging
import os
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.box import ROUNDED

# Suppress noisy logs
os.environ["CURL_CFFI_LOG_LEVEL"] = "ERROR"
logging.basicConfig(level=logging.CRITICAL)

from websearx_tool.tools import web_search, get_url_content  # noqa: E402

console = Console()

def display_results(results, is_search=True):
    if not results:
        console.print("[yellow]No data found.[/yellow]")
        return

    if is_search:
        for i, res in enumerate(results, 1):
            content = [Text(res.get('snippet', ''), style="bright_white")]
            if res.get('full_content'):
                content.extend([Text("\n--- Scraped ---\n", style="bold cyan"), Markdown(res['full_content'])])
            
            console.print(Panel(
                Group(*content),
                title=f"[bold green]{i}. {res.get('title')}[/bold green]",
                subtitle=f"[cyan]{res.get('url')}[/cyan]",
                box=ROUNDED, border_style="blue"
            ))
    else:
        # Scrape display logic
        data = results if isinstance(results, dict) else {0: results}
        for idx, text in data.items():
            console.print(Panel(Markdown(text), title=f"Source {idx}", box=ROUNDED, border_style="magenta"))

def main():
    parser = argparse.ArgumentParser(description="WebSearch Tool")
    subparsers = parser.add_subparsers(dest="command")

    s = subparsers.add_parser("search")
    s.add_argument("query")
    s.add_argument("--time", "-t", choices=["day", "month", "year"])
    s.add_argument("--limit", "-l", type=int, default=5)
    s.add_argument("--scrape", "-s", action="store_true")
    s.add_argument("--json", "-j", action="store_true")

    sc = subparsers.add_parser("scrape")
    sc.add_argument("urls", nargs="+")
    sc.add_argument("--json", "-j", action="store_true")

    # Default to search if no command provided
    if len(sys.argv) > 1 and sys.argv[1] not in ["search", "scrape", "-h", "--help"]:
        sys.argv.insert(1, "search")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "search":
        res = web_search(args.query, args.time, args.scrape, args.limit)
        if args.json: 
            print(json.dumps(res, indent=2))
        else: 
            display_results(res)
    else:
        res = get_url_content(args.urls)
        if args.json: 
            print(json.dumps(res, indent=2))
        else: 
            display_results(res, is_search=False)

if __name__ == "__main__":
    main()