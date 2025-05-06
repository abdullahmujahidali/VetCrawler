import json
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def fetch_feline_health_data():
    BASE_URL = "https://www.vet.cornell.edu/departments-centers-and-institutes/cornell-feline-health-center/health-information/feline-health-topics"

    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    expander = soup.find("div", class_="expander")
    if not expander:
        print("Could not find the expander div containing categories.")
        return None

    categories = []
    h3_elements = expander.find_all("h3")

    for h3 in h3_elements:
        category_title = h3.get_text(strip=True)
        subcategory_div = h3.find_next_sibling("div")
        if not subcategory_div:
            continue

        subcategories = []
        links = subcategory_div.find_all("a")

        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href")
            if href:
                full_url = urljoin(BASE_URL, href)
                subcategories.append({"title": title, "url": full_url})
        categories.append({"title": category_title, "subcategories": subcategories})
    return categories


if __name__ == "__main__":
    data = fetch_feline_health_data()

    if data:
        with open("feline_health_topics.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"Data successfully saved to feline_health_topics.json")
        print(
            f"Found {len(data)} categories with a total of {sum(len(cat['subcategories']) for cat in data)} subcategories"
        )
    else:
        print("Failed to retrieve data")
