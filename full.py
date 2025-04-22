# full.py

import base64
import json
import os
import re
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def handle_cookie_consent(driver):
    """Handle cookie consent modals if they appear"""
    try:
        cookie_selectors = [
            "button.Accept.All.Cookies",
            ".Accept.All.Cookies",
            "button[aria-label*='Accept All Cookies']",
            "#onetrust-accept-btn-handler",
            ".accept-all-cookies",
        ]

        for selector in cookie_selectors:
            try:
                cookie_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                print("  Found cookie consent button, clicking it...")
                cookie_button.click()
                time.sleep(1)
                return True
            except:
                continue

        buttons = driver.find_elements(By.TAG_NAME, "button")
        for button in buttons:
            if "Accept All" in button.text:
                print(f"  Found Accept All button with text: {button.text}")
                button.click()
                time.sleep(1)
                return True

        driver.execute_script(
            """
            var buttons = document.querySelectorAll('button');
            for(var i=0; i<buttons.length; i++) {
                if(buttons[i].textContent.indexOf('Accept All') !== -1) {
                    buttons[i].click();
                    return;
                }
            }
        """
        )

        return False
    except Exception as e:
        print(f"  Error handling cookie consent: {e}")
        return False


def save_page_as_pdf(driver, section_title, subsection_title=None, output_dir="pdfs"):
    """Save the current page as a PDF using Chrome's built-in print functionality"""
    try:
        Path(output_dir).mkdir(exist_ok=True)
        if subsection_title:
            filename = f"{clean_filename(section_title)}_{clean_filename(subsection_title)}.pdf"
        else:
            filename = f"{clean_filename(section_title)}.pdf"

        filepath = os.path.join(output_dir, filename)

        print(f"  Saving PDF for: {filename}")
        pdf_data = driver.execute_cdp_cmd(
            "Page.printToPDF",
            {
                "printBackground": True,
                "preferCSSPageSize": True,
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4,
                "scale": 0.9,
            },
        )

        with open(filepath, "wb") as file:
            file.write(base64.b64decode(pdf_data["data"]))

        print(f"  PDF saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"  Error saving PDF: {e}")
        return None


def clean_filename(text):
    """Clean a string to be used as a filename"""
    return re.sub(r'[\\/*?:"<>|]', "_", text).strip()


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


def extract_subsections_with_selenium(driver, url, section_title, save_pdfs=False):
    """
    Extract subsections and their in-depth content from Merck Veterinary Manual section
    """
    print(f"Extracting subsections for {section_title} from {url}")

    try:
        driver.get(url)
        handle_cookie_consent(driver)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            print("  Timeout waiting for page to load. Continuing anyway...")
        time.sleep(3)
        if save_pdfs:
            save_page_as_pdf(driver, section_title)
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
                "pdf_path": None,
            }

            try:
                driver.get(subsection["url"])
                handle_cookie_consent(driver)
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except TimeoutException:
                    print(
                        "  Timeout waiting for subsection page to load. Continuing anyway..."
                    )
                time.sleep(2)
                if save_pdfs:
                    pdf_path = save_page_as_pdf(
                        driver, section_title, subsection["title"]
                    )
                    if pdf_path:
                        subsection_data["pdf_path"] = pdf_path
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
                            link["pdf_path"] = None
                            filtered_links.append(link)
                            print(f"  Found in-depth link: {link['title']}")
                            if save_pdfs:
                                try:
                                    driver.get(link["url"])
                                    handle_cookie_consent(driver)
                                    try:
                                        WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located(
                                                (By.TAG_NAME, "body")
                                            )
                                        )
                                    except TimeoutException:
                                        print(
                                            "  Timeout waiting for in-depth page to load. Continuing anyway..."
                                        )

                                    time.sleep(1)
                                    in_depth_title = (
                                        f"{subsection['title']}_{link['title']}"
                                    )
                                    pdf_path = save_page_as_pdf(
                                        driver, section_title, in_depth_title
                                    )
                                    if pdf_path:
                                        link["pdf_path"] = pdf_path
                                except Exception as e:
                                    print(f"  Error saving in-depth page as PDF: {e}")

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


def main():
    test_mode = "--test" in sys.argv
    save_pdfs = "--save-pdfs" in sys.argv
    sections_path = "merck_sections.json"
    if not os.path.exists(sections_path):
        sections_path = os.path.join("merck", "clean_sections.json")
        if not os.path.exists(sections_path):
            print(
                f"Error: Neither merck_sections.json nor merck/clean_sections.json found"
            )
            return

    try:
        with open(sections_path, "r") as f:
            sections = json.load(f)

        print(f"Loaded {len(sections)} sections from {sections_path}")
        output_dir = "merck_data"
        Path(output_dir).mkdir(exist_ok=True)

        if save_pdfs:
            pdf_dir = os.path.join(output_dir, "pdfs")
            Path(pdf_dir).mkdir(exist_ok=True)
            print(f"PDFs will be saved to {pdf_dir}")

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Use the new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        print("Initializing Chrome WebDriver...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        if test_mode:
            print("Running in TEST mode - only processing Circulatory System")
        else:
            print(f"Preparing to extract subsections for {len(sections)} sections")

        processed = 0
        successful = 0
        if test_mode:
            circulatory_section = next(
                (
                    s
                    for s in sections
                    if "title" in s and s["title"] == "Circulatory System"
                ),
                None,
            )
            if circulatory_section:
                test_sections = [circulatory_section]
                print("Found Circulatory System section for testing")
            else:
                test_sections = [sections[0]]
                print(
                    f"Circulatory System section not found, using first section: {test_sections[0].get('title', 'Unknown')}"
                )
        else:
            test_sections = sections
        total_sections = len(test_sections)
        complete_data = []

        for i, section in enumerate(test_sections, 1):
            title = section.get("title")
            url = section.get("url")

            if not title or not url:
                print(f"Skipping section {i} - missing title or URL")
                continue

            print(f"\n[{i}/{total_sections}] Processing: {title}")
            subsections = extract_subsections_with_selenium(
                driver, url, title, save_pdfs
            )
            processed += 1
            section_data = {"title": title, "url": url, "subsections": subsections}
            complete_data.append(section_data)

            if subsections:
                print(
                    f"✓ Successfully processed {len(subsections)} subsections for {title}"
                )
                successful += 1
            else:
                print(f"✗ No subsections found for {title}")

            if i < total_sections:
                print("Waiting 2 seconds before next request...")
                time.sleep(2)
        complete_output_path = os.path.join(output_dir, "merck_complete_data.json")
        with open(complete_output_path, "w", encoding="utf-8") as f:
            json.dump(complete_data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Saved complete data to {complete_output_path}")

        print(f"\n=== Summary ===")
        print(f"Processed: {processed}/{total_sections} sections")
        print(f"Successful: {successful}/{processed} sections")
        print(f"All data has been saved to: {os.path.abspath(complete_output_path)}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if "driver" in locals():
            driver.quit()
            print("WebDriver closed")


if __name__ == "__main__":
    main()
