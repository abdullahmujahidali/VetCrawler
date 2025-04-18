#!/usr/bin/env python
"""
Debug tool to check CSS selectors against the Merck Vet Manual website.
This can help identify the correct selectors to use in your spider.
"""

import argparse
import json
import logging

import requests
from parsel import Selector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("debug_selector.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Debug CSS selectors for web scraping")
    parser.add_argument(
        "--url",
        default="https://www.merckvetmanual.com/veterinary-topics",
        help="URL to test selectors against (default: Merck Vet Manual topics page)",
    )
    parser.add_argument(
        "--selector",
        default='div#bodyContent a[href*="/"]',
        help="CSS selector to test",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Limit the number of results to display"
    )
    parser.add_argument(
        "--output", default="debug_results.json", help="Output file for full results"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info(f"Testing selector '{args.selector}' on {args.url}")

    # Fetch the page
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(args.url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch URL: {e}")
        return

    # Parse with the selector
    selector = Selector(response.text)
    elements = selector.css(args.selector)

    logger.info(f"Found {len(elements)} matching elements")

    # Collect results
    results = []
    for i, element in enumerate(elements):
        text = element.css("::text").get()
        href = element.css("::attr(href)").get()

        # Clean up text
        if text:
            text = text.strip()

        result = {"index": i, "text": text, "href": href, "html": element.get()}
        results.append(result)

        # Display limited results in console
        if i < args.limit:
            logger.info(f"Element {i}:")
            logger.info(f"  Text: {text}")
            logger.info(f"  HREF: {href}")

    # Save full results to file
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"Full results saved to {args.output}")


if __name__ == "__main__":
    main()
