#!/usr/bin/env python
"""
Utility script to run the Merck Vet Manual scraper with various options.
Place this in the root directory of your scrapy project.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="Run Merck Vet Manual scraper")
    parser.add_argument(
        "--full", action="store_true", help="Run the full scraper (follows links)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "xml"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: auto-generated)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=0,
        help="Limit the number of items to scrape (0 for no limit)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Choose which spider to run
    spider_name = "merck_vet_manual_full" if args.full else "merck_vet_manual"

    # Generate output filename if not provided
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"output/merck_vet_topics_{timestamp}.{args.format}"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Build command
    cmd = ["scrapy", "crawl", spider_name, "-o", args.output]

    # Add item limit if specified
    if args.limit > 0:
        cmd.extend(["-s", f"CLOSESPIDER_ITEMCOUNT={args.limit}"])

    # Run the spider
    print(f"Starting scraper: {' '.join(cmd)}")
    subprocess.run(cmd)
    print(f"Scraping completed. Results saved to {args.output}")


if __name__ == "__main__":
    main()
