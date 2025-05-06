import base64
import json
import os
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def fetch_feline_health_data():
    BASE_URL = "https://www.vet.cornell.edu/departments-centers-and-institutes/cornell-feline-health-center/health-information/feline-health-topics"

    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

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
        # Navigate to the page
        driver.get(url)

        # Wait for the page to load (adjust as needed)
        time.sleep(5)

        # Execute CDP command to print the page to PDF
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

        # Decode the base64 encoded PDF
        pdf_data = base64.b64decode(result["data"])

        # Write PDF data to file
        with open(pdf_path, "wb") as f:
            f.write(pdf_data)

        return True
    except Exception as e:
        print(f"Error saving PDF: {e}")
        return False


def save_pages_as_pdf(categories):
    # Create a PDF directory if it doesn't exist
    pdf_dir = "feline_health_pdfs"
    os.makedirs(pdf_dir, exist_ok=True)

    # Set up Chrome options for headless PDF printing
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "--window-size=1200,1200"
    )  # Ensure good size for printing

    # Initialize the WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Create a log of processed URLs
    processed_log = []

    try:
        for category in categories:
            category_title = category["title"]
            print(f"\nProcessing category: {category_title}")

            # Create category directory
            category_dir = os.path.join(
                pdf_dir, category_title.replace(" ", "_").replace("/", "_")
            )
            os.makedirs(category_dir, exist_ok=True)

            for subcategory in category["subcategories"]:
                subcategory_title = subcategory["title"]
                subcategory_url = subcategory["url"]

                # YouTube playlists and external sites may cause issues, so handle them differently
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

                # Create a safe filename
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
                    # Save the page as PDF
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

                # Add a small delay between requests to be gentle on the server
                time.sleep(1)

    finally:
        # Close the browser
        driver.quit()

        # Save processing log
        with open(
            os.path.join(pdf_dir, "processing_log.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(processed_log, f, indent=4, ensure_ascii=False)

        print(
            f"\nProcessing complete. See log at {os.path.join(pdf_dir, 'processing_log.json')}"
        )


if __name__ == "__main__":
    data = fetch_feline_health_data()

    if data:
        # Save to a JSON file
        with open("feline_health_topics.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"Data successfully saved to feline_health_topics.json")
        print(
            f"Found {len(data)} categories with a total of {sum(len(cat['subcategories']) for cat in data)} subcategories"
        )

        # Ask user if they want to download PDFs
        proceed = input("Do you want to download PDFs for all subcategories? (y/n): ")
        if proceed.lower() == "y":
            save_pages_as_pdf(data)
        else:
            print("PDF download skipped.")
    else:
        print("Failed to retrieve data")
