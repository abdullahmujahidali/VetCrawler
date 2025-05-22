import base64
import json
import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def fetch_canine_health_data():
    BASE_URL = "https://www.vet.cornell.edu/departments-centers-and-institutes/riney-canine-health-center/canine-health-information"

    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    print("souop: ", soup)

    # Find the expandable sections that contain categories
    expander = soup.find("div", class_="expander")
    if not expander:
        print("Could not find the expander div containing categories.")
        return None

    categories = []

    # Each category has an h3 header followed by a div containing links
    h3_elements = expander.find_all("h3")

    for h3 in h3_elements:
        category_title = h3.get_text(strip=True)

        # Find the div that follows this h3 (contains the subcategories)
        subcategory_div = h3.find_next_sibling("div")
        if not subcategory_div:
            continue

        subcategories = []
        # Get all links in this div
        links = subcategory_div.find_all("a")

        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href")
            if href:
                full_url = urljoin(BASE_URL, href)
                subcategories.append({"title": title, "url": full_url})

        # Add this category and its subcategories to our list
        categories.append({"title": category_title, "subcategories": subcategories})

    return categories


def save_url_as_pdf(driver, url, pdf_path, timeout=30):
    """Save a URL as PDF using Chrome's built-in PDF printing capability"""

    try:
        driver.get(url)
        time.sleep(5)
        result = driver.execute_cdp_cmd(
            "Page.printToPDF",
            {
                "printBackground": True,
                "preferCSSPageSize": True,
                "marginTop": 0,
                "marginBottom": 0,
                "marginLeft": 0,
                "marginRight": 0,
            },
        )
        pdf_data = base64.b64decode(result["data"])
        with open(pdf_path, "wb") as f:
            f.write(pdf_data)

        return True
    except Exception as e:
        print(f"Error saving PDF: {e}")
        return False


def save_pages_as_pdf(categories):
    pdf_dir = "canine_health_pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1200,1200")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    processed_log = []

    try:
        for category in categories:
            category_title = category["title"]
            print(f"\nProcessing category: {category_title}")
            category_dir = os.path.join(
                pdf_dir, category_title.replace(" ", "_").replace("/", "_")
            )
            os.makedirs(category_dir, exist_ok=True)

            for subcategory in category["subcategories"]:
                subcategory_title = subcategory["title"]
                subcategory_url = subcategory["url"]
                if (
                    "youtube.com" in subcategory_url
                    or "goo.gl" in subcategory_url
                    or "veritasdvm.com" in subcategory_url
                ):
                    print(f"  • Skipping external URL: {subcategory_title}")
                    processed_log.append(
                        {
                            "category": category_title,
                            "title": subcategory_title,
                            "url": subcategory_url,
                            "status": "skipped",
                            "reason": "External URL",
                        }
                    )
                    continue
                safe_title = (
                    subcategory_title.replace(" ", "_")
                    .replace("/", "_")
                    .replace(":", "")
                    .replace("?", "")
                    .replace('"', "")
                )
                pdf_path = os.path.join(category_dir, f"{safe_title}.pdf")
                print(f"  • Saving: {subcategory_title}")
                try:
                    if save_url_as_pdf(driver, subcategory_url, pdf_path):
                        processed_log.append(
                            {
                                "category": category_title,
                                "title": subcategory_title,
                                "url": subcategory_url,
                                "pdf_path": pdf_path,
                                "status": "success",
                            }
                        )
                    else:
                        processed_log.append(
                            {
                                "category": category_title,
                                "title": subcategory_title,
                                "url": subcategory_url,
                                "status": "error",
                                "error": "Failed to save PDF",
                            }
                        )
                except Exception as e:
                    print(f"    Error processing {subcategory_title}: {e}")
                    processed_log.append(
                        {
                            "category": category_title,
                            "title": subcategory_title,
                            "url": subcategory_url,
                            "status": "error",
                            "error": str(e),
                        }
                    )
                time.sleep(1)

    finally:
        driver.quit()
        with open(
            os.path.join(pdf_dir, "processing_log.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(processed_log, f, indent=4, ensure_ascii=False)

        print(
            f"\nProcessing complete. See log at {os.path.join(pdf_dir, 'processing_log.json')}"
        )


if __name__ == "__main__":
    data = fetch_canine_health_data()
    print("data: ", data)
    if data:
        with open("feline_health_topics.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Data successfully saved to feline_health_topics.json")
        print(
            f"Found {len(data)} categories with a total of {sum(len(cat['subcategories']) for cat in data)} subcategories"
        )
        proceed = input("Do you want to download PDFs for all subcategories? (y/n): ")
        if proceed.lower() == "y":
            save_pages_as_pdf(data)
        else:
            print("PDF download skipped.")
    else:
        print("Failed to retrieve data")
