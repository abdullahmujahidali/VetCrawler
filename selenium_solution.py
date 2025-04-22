import json
import os
import re
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def extract_content_from_page(driver, url, base_section_path):
    """
    Extract links from a page - works for both subsections and in-depth pages
    """
    links = driver.find_elements(By.TAG_NAME, "a")
    content_links = []
    base_url = "https://www.merckvetmanual.com"

    for link in links:
        try:
            href = link.get_attribute("href")
            text = link.text.strip()

            if (
                href
                and text
                and len(text) > 3
                and href.startswith(base_url)
                and href != url
                and not any(
                    x in text.lower()
                    for x in [
                        "veterinary",
                        "pet owners",
                        "resources",
                        "quizzes",
                        "about",
                        "contact",
                        "disclaimer",
                        "privacy",
                        "terms",
                        "cookie",
                        "licensing",
                        "copyright",
                    ]
                )
            ):

                if base_section_path in href:
                    content_links.append({"title": text, "url": href})
        except Exception as e:
            print(f"  Error processing link: {e}")
            continue

    return content_links


def extract_subsections_with_selenium(url, section_title):
    """
    Extract subsections and their in-depth content from Merck Veterinary Manual section
    """
    print(f"Extracting subsections for {section_title} from {url}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(5)
        section_path = url.split("merckvetmanual.com")[1]
        base_url = "https://www.merckvetmanual.com"
        print("Extracting first-level subsections...")
        subsections = extract_content_from_page(driver, url, section_path)
        filtered_subsections = []
        for item in subsections:
            relative_path = item["url"].replace(base_url, "")
            parts = relative_path.strip("/").split("/")

            if len(parts) > 1 and section_path.strip("/") == parts[0]:
                filtered_subsections.append(item)
                print(f"Found subsection: {item['title']}")

        processed_subsections = []
        for i, subsection in enumerate(filtered_subsections):
            print(
                f"Processing subsection {i+1}/{len(filtered_subsections)}: {subsection['title']}"
            )

            subsection_data = {
                "title": subsection["title"],
                "url": subsection["url"],
                "in_depth_links": [],
            }
            try:
                driver.get(subsection["url"])
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(3)
                list_indicators = driver.find_elements(
                    By.CSS_SELECTOR,
                    "ul li a, div[class*='subsection'] a, div[class*='section'] a",
                )

                in_depth_links = []

                if list_indicators:
                    print(f"  Found potential in-depth links on subsection page")
                    section_base_path = subsection["url"].replace(base_url, "")
                    in_depth_links = extract_content_from_page(
                        driver, subsection["url"], section_base_path
                    )
                    filtered_links = []
                    for link in in_depth_links:
                        if (
                            section_base_path in link["url"]
                            and link["url"] != subsection["url"]
                        ):
                            filtered_links.append(link)
                            print(f"  Found in-depth link: {link['title']}")

                    in_depth_links = filtered_links

                subsection_data["in_depth_links"] = in_depth_links
                processed_subsections.append(subsection_data)
                if i < len(filtered_subsections) - 1:
                    time.sleep(1)

            except Exception as e:
                print(f"  Error processing subsection {subsection['title']}: {e}")
                processed_subsections.append(subsection_data)

        return processed_subsections

    except Exception as e:
        print(f"Error: {e}")
        return []

    finally:
        driver.quit()


def main():
    test_mode = "--test" in sys.argv
    sections_path = os.path.join("merck", "clean_sections.json")

    if not os.path.exists(sections_path):
        print(f"Error: {sections_path} not found")
        return

    try:
        with open(sections_path, "r") as f:
            sections = json.load(f)

        output_dir = os.path.join("merck", "subsections")
        Path(output_dir).mkdir(exist_ok=True)
        if test_mode:
            print("Running in TEST mode - only processing Circulatory System")
        else:
            print(f"Preparing to extract subsections for {len(sections)} sections")

        processed = 0
        successful = 0
        if test_mode:
            circulatory_section = next(
                (s for s in sections if s["title"] == "Circulatory System"), None
            )
            if circulatory_section:
                sections = [circulatory_section]
            else:
                print("Error: Circulatory System section not found")
                return
        total_sections = len(sections)
        for i, section in enumerate(sections, 1):
            title = section.get("title")
            url = section.get("url")

            if not title or not url:
                continue

            print(f"\n[{i}/{total_sections}] Processing: {title}")
            subsections = extract_subsections_with_selenium(url, title)
            processed += 1

            if subsections:
                safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
                output_path = os.path.join(output_dir, f"{safe_title}.json")

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(subsections, f, indent=2, ensure_ascii=False)

                print(f"✓ Saved {len(subsections)} subsections to {output_path}")
                successful += 1
            else:
                print(f"✗ No subsections found for {title}")
            if i < total_sections:
                print("Waiting 2 seconds before next request...")
                time.sleep(2)
        print(f"\n=== Summary ===")
        print(f"Processed: {processed}/{total_sections} sections")
        print(f"Successful: {successful}/{processed} sections")
        print(f"All subsections have been saved to: {os.path.abspath(output_dir)}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
