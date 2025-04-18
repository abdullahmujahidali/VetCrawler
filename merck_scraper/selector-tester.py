#!/usr/bin/env python
"""
A simple script to test CSS selectors against the Merck Vet Manual website.
Run this before your spider to verify the selectors are working.
"""

import requests
from bs4 import BeautifulSoup
import json
import argparse

def test_selector(url, selector):
    """Test a CSS selector against a webpage and print results."""
    print(f"Testing selector '{selector}' on {url}")
    
    # Set headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Fetch the page
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find elements matching the selector
    elements = soup.select(selector)
    
    print(f"Found {len(elements)} matching elements")
    
    # Print details of each element
    for i, element in enumerate(elements[:10]):  # Show first 10
        print(f"\nElement {i+1}:")
        
        # Show the element's tag name and attributes
        print(f"  Tag: {element.name}")
        if element.attrs:
            print(f"  Attributes: {element.attrs}")
        
        # If it's a link, show href and text
        if element.name == 'a':
            print(f"  Text: {element.get_text().strip()}")
            print(f"  HREF: {element.get('href', 'N/A')}")
        else:
            # Show some content
            text = element.get_text().strip()
            print(f"  Text: {text[:100]}..." if len(text) > 100 else f"  Text: {text}")
    
    # If there are more elements, indicate there are more
    if len(elements) > 10:
        print(f"\n... and {len(elements) - 10} more elements")
    
    # Save all elements to a JSON file
    results = []
    for i, element in enumerate(elements):
        elem_dict = {
            "index": i,
            "tag": element.name,
            "attributes": element.attrs,
            "text": element.get_text().strip()
        }
        
        if element.name == 'a':
            elem_dict["href"] = element.get('href', 'N/A')
        
        results.append(elem_dict)
    
    with open("selector_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nAll results saved to selector_results.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test CSS selectors on a webpage")
    parser.add_argument(
        "--url", 
        default="https://www.merckvetmanual.com/veterinary-topics",
        help="URL to test against"
    )
    parser.add_argument(
        "--selector", 
        default="div.SectionList_sectionListItem__NNP4c a",
        help="CSS selector to test"
    )
    args = parser.parse_args()
    
    test_selector(args.url, args.selector)