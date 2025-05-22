import base64
import json
import os
import time
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def fetch_canine_health_data():
    BASE_URL = "https://www.vet.cornell.edu/departments-centers-and-institutes/riney-canine-health-center/canine-health-information"
    
    all_categories = []
    current_page = 0
    
    while True:
        # Construct URL with page parameter
        if current_page == 0:
            page_url = BASE_URL
        else:
            page_url = f"{BASE_URL}?page={current_page}"
        
        print(f"Fetching page {current_page + 1}...")
        
        try:
            response = requests.get(page_url)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching page {current_page}: {e}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find the view content container
        view_content = soup.find("div", class_="view-content cards")
        if not view_content:
            print(f"Could not find view-content on page {current_page}")
            # Let's see what div classes are available
            all_divs = soup.find_all("div", class_=True)
            print(f"Available div classes: {[' '.join(div.get('class', [])) for div in all_divs[:10]]}")
            break

        # Find all h3 category headers and their associated content
        current_category = None
        category_items = []
        
        # Get all direct children and iterate through them
        elements = list(view_content.children)
        
        for element in elements:
            if element.name == "h3":
                # Save previous category if exists
                if current_category and category_items:
                    # Check if this category already exists in our list
                    existing_category = next((cat for cat in all_categories if cat["title"] == current_category), None)
                    if existing_category:
                        existing_category["subcategories"].extend(category_items)
                    else:
                        all_categories.append({"title": current_category, "subcategories": category_items})
                
                # Start new category
                current_category = element.get_text(strip=True)
                category_items = []
                print(f"  Found category: {current_category}")
                
            elif element.name == "div" and element.get("class"):
                element_classes = " ".join(element.get("class", []))
                if "expander views-row card" in element_classes:
                    # Find the link in this card
                    link_element = element.find("a")
                    if link_element and current_category:
                        title = link_element.get_text(strip=True)
                        href = link_element.get("href")
                        if href:
                            full_url = urljoin(BASE_URL, href)
                            category_items.append({"title": title, "url": full_url})
                            print(f"    Found item: {title}")

        # Save the last category
        if current_category and category_items:
            existing_category = next((cat for cat in all_categories if cat["title"] == current_category), None)
            if existing_category:
                existing_category["subcategories"].extend(category_items)
            else:
                all_categories.append({"title": current_category, "subcategories": category_items})
        
        # Check if there's a next page
        pagination = soup.find("nav", class_="pager")
        if pagination:
            next_link = pagination.find("a", title=lambda x: x and "Go to next page" in x)
            if next_link:
                current_page += 1
                continue
        
        # No more pages
        break
    
    return all_categories


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
                    or "bigredbarkchat.vet.cornell.edu" in subcategory_url
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
    
    if data:
        with open("canine_health_topics.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Data successfully saved to canine_health_topics.json")
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