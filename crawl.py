import json
import re

import requests
from bs4 import BeautifulSoup


def scrape_merck_vet_manual_sections():
    url = "https://www.merckvetmanual.com/veterinary-topics"

    # Send HTTP request to the website
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to retrieve the page: Status code {response.status_code}")
        return

    # Look for the data in the __NEXT_DATA__ script tag
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        response.text,
        re.DOTALL,
    )

    if not match:
        print("Could not find __NEXT_DATA__ script")
        return

    try:
        data = json.loads(match.group(1))
        # Navigate to the section data in the JSON structure
        section_data = (
            data.get("props", {})
            .get("pageProps", {})
            .get("componentProps", {})
            .get("eb190e7b-5914-4f3d-91a8-3fa8542b6178", {})
            .get("data", [])
        )

        # Extract the sections
        sections = []
        for item in section_data:
            title = item.get("titlecomputed_t", "")
            path = item.get("relativeurlcomputed_s", "")

            if title and path:
                url = f"https://www.merckvetmanual.com{path}"
                sections.append({"title": title, "url": url})

        return sections

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON data: {e}")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return


if __name__ == "__main__":
    sections = scrape_merck_vet_manual_sections()

    if sections:
        print(f"Found {len(sections)} sections:")
        for section in sections:
            print(f"Title: {section['title']}")
            print(f"URL: {section['url']}")
            print("-" * 30)
    else:
        print("No sections found or there was an error during scraping.")
