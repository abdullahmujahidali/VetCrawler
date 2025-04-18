"""
Quick test script to analyze the Merck Vet Manual website structure using Selenium.
This script will help identify the correct selectors for scraping.
"""

import json
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def analyze_website_structure():
    """Analyze the structure of the Merck Vet Manual website and save findings."""
    print("Starting website structure analysis...")

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    # Initialize WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)

    try:
        # Navigate to the veterinary topics page
        url = "https://www.merckvetmanual.com/veterinary-topics"
        print(f"Navigating to: {url}")
        driver.get(url)
        time.sleep(5)  # Allow page to fully load

        # Save page source for inspection
        with open("full_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Saved complete page source to full_page_source.html")

        # Collect all HTML elements that might be sections or topics
        results = {
            "page_title": driver.title,
            "url": url,
            "headings": [],
            "potential_section_containers": [],
            "potential_section_links": [],
            "page_structure": [],
        }

        # Find all headings
        for level in range(1, 7):
            headings = driver.find_elements(By.TAG_NAME, f"h{level}")
            for heading in headings:
                results["headings"].append(
                    {
                        "level": level,
                        "text": heading.text.strip(),
                        "classes": heading.get_attribute("class"),
                    }
                )

        # Find potential section containers
        containers = driver.find_elements(By.TAG_NAME, "div")
        for container in containers:
            # Only collect containers with multiple links (potential section containers)
            links = container.find_elements(By.TAG_NAME, "a")
            if len(links) >= 3:
                container_info = {
                    "tag": "div",
                    "id": container.get_attribute("id") or "none",
                    "classes": container.get_attribute("class") or "none",
                    "link_count": len(links),
                    "sample_links": [],
                }

                # Collect sample links
                for link in links[:5]:
                    container_info["sample_links"].append(
                        {
                            "text": link.text.strip(),
                            "href": link.get_attribute("href") or "none",
                        }
                    )

                results["potential_section_containers"].append(container_info)

        # Find all links that might be sections
        all_links = driver.find_elements(By.TAG_NAME, "a")
        section_keywords = [
            "behavior",
            "circulatory",
            "clinical",
            "digestive",
            "ear",
            "emergency",
            "endocrine",
            "exotic",
            "eye",
            "generalized",
            "immune",
            "infectious",
        ]

        for link in all_links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()

            # Skip empty links or non-relevant links
            if not text or not href or "#" in href or "javascript:" in href:
                continue

            # Check if the link text or href contains section keywords
            if any(
                keyword in text.lower() or keyword in href.lower()
                for keyword in section_keywords
            ):
                results["potential_section_links"].append(
                    {
                        "text": text,
                        "href": href,
                        "classes": link.get_attribute("class") or "none",
                        "parent_tag": link.find_element(By.XPATH, "..").tag_name,
                        "parent_classes": link.find_element(
                            By.XPATH, ".."
                        ).get_attribute("class")
                        or "none",
                    }
                )

        # Analyze the overall page structure
        body = driver.find_element(By.TAG_NAME, "body")
        analyze_element_structure(body, results["page_structure"], max_depth=3)

        # Save analysis results
        with open("website_analysis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("Saved analysis results to website_analysis.json")

        # Take a screenshot
        driver.save_screenshot("website_screenshot.png")
        print("Saved screenshot to website_screenshot.png")

        return results

    finally:
        driver.quit()
        print("Browser closed")


def analyze_element_structure(element, structure_list, level=0, max_depth=3):
    """Recursively analyze the structure of HTML elements."""
    if level >= max_depth:
        return

    # Get element information
    tag_name = element.tag_name
    element_id = element.get_attribute("id") or ""
    element_class = element.get_attribute("class") or ""

    # Create element info dictionary
    element_info = {
        "level": level,
        "tag": tag_name,
        "id": element_id,
        "class": element_class,
        "text": element.text[:100] + "..." if len(element.text) > 100 else element.text,
        "children": [],
    }

    # Add to structure list
    structure_list.append(element_info)

    # Recursively process child elements
    if level < max_depth - 1:
        try:
            children = element.find_elements(By.XPATH, "./*")
            for child in children[:10]:  # Limit to 10 children for brevity
                analyze_element_structure(
                    child, element_info["children"], level + 1, max_depth
                )

            # If there are more children, add a placeholder
            if len(children) > 10:
                element_info["children"].append(
                    {"note": f"...and {len(children) - 10} more children"}
                )
        except:
            # Ignore errors when fetching children
            pass


if __name__ == "__main__":
    analyze_website_structure()
