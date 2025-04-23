# full.py - With animal filtering to focus on cats and dogs

import base64
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# List of sections to ignore
IGNORED_SECTIONS = ["Behavior", "Poultry", "Special Subjects", "Public Health"]

# List of animal terms to exclude (these are animals we're NOT interested in)
EXCLUDED_ANIMALS = [
    "horse",
    "horses",
    "equine",
    "pig",
    "pigs",
    "swine",
    "sow",
    "boar",
    "hog",
    "cow",
    "cows",
    "cattle",
    "bovine",
    "bull",
    "heifer",
    "calf",
    "calves",
    "sheep",
    "lamb",
    "lambs",
    "ovine",
    "goat",
    "goats",
    "caprine",
    "chicken",
    "chickens",
    "poultry",
    "hen",
    "rooster",
    "turkey",
    "turkeys",
    "bird",
    "birds",
    "avian",
    "rabbit",
    "rabbits",
    "bunny",
    "bunnies",
    "rodent",
    "rodents",
    "rat",
    "rats",
    "mouse",
    "mice",
    "hamster",
    "hamsters",
    "gerbil",
    "gerbils",
    "ferret",
    "ferrets",
    "reptile",
    "reptiles",
    "lizard",
    "lizards",
    "snake",
    "snakes",
    "human",
    "humans",
    "people",
    "person",
    "people",
    "camel",
    "camels",
    "llama",
    "llamas",
    "alpaca",
    "alpacas",
    "fish",
    "fishes",
    "goldfish",
    "tropical fish",
]


def is_relevant_title(title):
    """
    Check if the title is relevant (does not explicitly mention excluded animals)
    Returns True if the title is relevant (for cats/dogs or general), False otherwise
    """
    # Convert to lowercase for case-insensitive matching
    lower_title = title.lower()

    # If "cat", "cats", "dog", or "dogs" is in the title, it's definitely relevant
    if any(
        animal in lower_title
        for animal in [
            "cat",
            "cats",
            "dog",
            "dogs",
            "kitten",
            "kittens",
            "puppy",
            "puppies",
            "feline",
            "canine",
        ]
    ):
        return True

    # Check if any excluded animal terms are in the title
    for excluded in EXCLUDED_ANIMALS:
        # Use word boundary matching to avoid partial matches (e.g., 'rat' in 'strategy')
        pattern = r"\b" + re.escape(excluded) + r"\b"
        if re.search(pattern, lower_title):
            return False

    # If no excluded animals found, it's likely general content, so include it
    return True


def strip_url_fragment(url):
    """Remove the fragment part of a URL (everything after the #)"""
    parsed = urlparse(url)
    # Create a new URL without the fragment
    clean_url = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, "")
    )
    return clean_url


def handle_cookie_consent(driver):
    """Handle cookie consent modals if they appear"""
    try:
        selectors = [
            "button.Accept.All.Cookies",
            ".Accept.All.Cookies",
            "button[aria-label*='Accept All Cookies']",
            "button:contains('Accept All')",
            "#onetrust-accept-btn-handler",
            ".accept-all-cookies",
            ".accept-cookies-button",
            "button.accept-cookies",
        ]

        for selector in selectors:
            try:
                cookie_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                print(f"Found cookie button with selector: {selector}")
                cookie_button.click()
                time.sleep(1)
                return True
            except:
                continue

        # Try looking for buttons with text
        cookie_button_texts = [
            "Accept All Cookies",
            "Accept All",
            "Accept",
            "I Agree",
            "OK",
            "Got it",
        ]

        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                button_text = button.text.strip()
                if button_text and any(
                    accept_text.lower() in button_text.lower()
                    for accept_text in cookie_button_texts
                ):
                    print(f"Found cookie button with text: {button_text}")
                    button.click()
                    time.sleep(1)
                    return True
        except:
            pass

        # JavaScript approach
        try:
            # Remove consent dialogs
            for consent_id in [
                "#cookie-consent",
                "#cookie-banner",
                ".cookie-banner",
                "#cookie-notice",
            ]:
                driver.execute_script(
                    f"var element = document.querySelector('{consent_id}'); if(element) element.remove();"
                )

            # Click accept button
            driver.execute_script(
                """
                var buttons = document.querySelectorAll('button');
                for(var i=0; i<buttons.length; i++) {
                    if(buttons[i].textContent.indexOf('Accept') !== -1 || 
                       buttons[i].textContent.indexOf('accept') !== -1 ||
                       buttons[i].textContent.indexOf('Allow') !== -1) {
                        buttons[i].click();
                        return;
                    }
                }
            """
            )

            # Set cookies directly
            driver.execute_script(
                """
                document.cookie = "cookieConsent=true; path=/;";
                document.cookie = "cookies_accepted=true; path=/;";
            """
            )

            return True
        except:
            print("JavaScript attempts to handle cookie consent failed")
            return False

    except Exception as e:
        print(f"Error handling cookie consent: {e}")
        return False


def save_page_as_pdf(driver, title, url, output_dir="pdfs"):
    """Save the current page as a PDF using Chrome's built-in print functionality"""
    try:
        Path(output_dir).mkdir(exist_ok=True)
        safe_title = clean_filename(title)
        filepath = os.path.join(output_dir, f"{safe_title}.pdf")

        print(f"Saving PDF for: {title}")

        # Navigate to the URL
        driver.get(url)

        # Handle cookie consent
        handle_cookie_consent(driver)

        # Wait for page to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            print("Timeout waiting for page to load. Continuing anyway...")

        # Additional time for JavaScript rendering
        time.sleep(2)

        # Generate PDF
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

        # Save the PDF
        with open(filepath, "wb") as file:
            file.write(base64.b64decode(pdf_data["data"]))

        print(f"PDF saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving PDF: {e}")
        try:
            screenshot_path = f"error_screenshot_{clean_filename(title)}.png"
            driver.save_screenshot(screenshot_path)
            print(f"Error screenshot saved to: {screenshot_path}")
        except:
            pass
        return None


def clean_filename(text):
    """Clean a string to be used as a filename"""
    if len(text) > 150:
        text = text[:150]
    clean = re.sub(r'[\\/*?:"<>|]', "_", text).strip()
    clean = re.sub(r"_+", "_", clean)
    return clean


def extract_content_from_page(driver, url, base_section_path):
    """Extract links from a page that match criteria for being content"""
    links = driver.find_elements(By.TAG_NAME, "a")
    content_links = []
    base_url = "https://www.merckvetmanual.com"

    # Keep track of URLs we've already seen (without fragments)
    seen_urls = set()

    for link in links:
        try:
            href = link.get_attribute("href")
            text = link.text.strip()

            # Skip if already processed this link (without the fragment)
            if href:
                clean_href = strip_url_fragment(href)
                if clean_href in seen_urls:
                    continue
                seen_urls.add(clean_href)

            # Filter links: internal, non-empty text, related to the section, not navigation
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
                # Check if the title is relevant (includes cats/dogs or is general)
                if is_relevant_title(text) and base_section_path in href:
                    # Store only the base URL without fragments
                    content_links.append(
                        {
                            "title": text,
                            "url": clean_href,
                            "original_url": href,  # Keep original for reference
                        }
                    )
        except Exception as e:
            print(f"Error processing link: {e}")
            continue

    return content_links


def download_pdfs_and_build_index():
    """Main function to download PDFs and build an index"""
    # Create output directories
    output_dir = "merck_data"
    pdf_dir = os.path.join(output_dir, "pdfs")
    Path(output_dir).mkdir(exist_ok=True)
    Path(pdf_dir).mkdir(exist_ok=True)

    # Initialize Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    print("Initializing Chrome WebDriver...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

    # PDF tracking data
    pdf_index = []

    try:
        # Check for existing index file
        index_path = os.path.join(output_dir, "pdf_index.json")
        if os.path.exists(index_path):
            print(f"Loading existing PDF index from {index_path}")
            with open(index_path, "r") as f:
                pdf_index = json.load(f)
            print(f"Loaded {len(pdf_index)} existing entries")

        # Load section data
        sections_path = "merck_sections.json"
        if not os.path.exists(sections_path):
            sections_path = os.path.join("merck", "clean_sections.json")
            if not os.path.exists(sections_path):
                print("Error: No sections file found")
                return

        with open(sections_path, "r") as f:
            sections = json.load(f)

        # Filter out ignored sections
        filtered_sections = [
            s for s in sections if s.get("title") not in IGNORED_SECTIONS
        ]
        ignored_count = len(sections) - len(filtered_sections)

        print(
            f"Starting the process with {len(filtered_sections)} sections (ignored {ignored_count} sections)"
        )
        print(f"Ignoring the following sections: {', '.join(IGNORED_SECTIONS)}")
        print(
            f"Filtering content to focus on cats and dogs, excluding: {', '.join(EXCLUDED_ANIMALS[:10])}..."
        )

        # Create sets of processed URLs to avoid duplicates
        # Remove fragments from existing URLs for comparison
        processed_urls = {strip_url_fragment(entry["url"]) for entry in pdf_index}

        # Statistics tracking
        stats = {
            "sections_processed": 0,
            "sections_downloaded": 0,
            "subsections_processed": 0,
            "subsections_downloaded": 0,
            "in_depth_processed": 0,
            "in_depth_downloaded": 0,
            "skipped_irrelevant": 0,
        }

        # Process each section
        total_sections = len(filtered_sections)
        for section_idx, section in enumerate(filtered_sections, 1):
            section_title = section.get("title", "Unknown Section")
            section_url = section.get("url")

            if not section_url:
                print(
                    f"Skipping section {section_idx}/{total_sections}: {section_title} - missing URL"
                )
                continue

            print(
                f"\n[{section_idx}/{total_sections}] Processing section: {section_title}"
            )
            stats["sections_processed"] += 1

            # Add section to index if not already processed
            clean_section_url = strip_url_fragment(section_url)
            if clean_section_url not in processed_urls:
                # Download section PDF
                section_pdf_path = save_page_as_pdf(
                    driver, section_title, section_url, pdf_dir
                )

                # Add to index
                if section_pdf_path:
                    section_entry = {
                        "title": section_title,
                        "url": clean_section_url,
                        "pdf_path": section_pdf_path,
                        "type": "section",
                    }
                    pdf_index.append(section_entry)
                    processed_urls.add(clean_section_url)
                    stats["sections_downloaded"] += 1

                    # Save index after each PDF to prevent data loss
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(pdf_index, f, indent=2, ensure_ascii=False)
            else:
                print(f"Section already processed: {section_title}")

            # Extract subsections
            section_path = section_url.split("merckvetmanual.com")[1]

            # Navigate to the section page
            driver.get(section_url)
            handle_cookie_consent(driver)

            # Wait for page to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                print("Timeout waiting for section page to load. Continuing anyway...")

            time.sleep(3)

            # Extract links
            print("Extracting subsections...")
            subsections = extract_content_from_page(driver, section_url, section_path)

            # Filter to valid subsections
            base_url = "https://www.merckvetmanual.com"
            filtered_subsections = []
            for item in subsections:
                relative_path = item["url"].replace(base_url, "")
                parts = relative_path.strip("/").split("/")

                if len(parts) > 1 and section_path.strip("/") == parts[0]:
                    filtered_subsections.append(item)

            print(
                f"Found {len(filtered_subsections)} relevant subsections for {section_title}"
            )

            # Process each subsection
            for sub_idx, subsection in enumerate(filtered_subsections, 1):
                subsection_title = subsection["title"]
                subsection_url = subsection["url"]

                # Check if the title is relevant for cats/dogs
                if not is_relevant_title(subsection_title):
                    print(f"Skipping irrelevant subsection: {subsection_title}")
                    stats["skipped_irrelevant"] += 1
                    continue

                print(
                    f"[{sub_idx}/{len(filtered_subsections)}] Processing subsection: {subsection_title}"
                )
                stats["subsections_processed"] += 1

                # Add subsection to index if not already processed
                clean_subsection_url = strip_url_fragment(subsection_url)
                if clean_subsection_url not in processed_urls:
                    # Download subsection PDF
                    subsection_pdf_path = save_page_as_pdf(
                        driver,
                        f"{section_title} - {subsection_title}",
                        subsection_url,
                        pdf_dir,
                    )

                    # Add to index
                    if subsection_pdf_path:
                        subsection_entry = {
                            "title": subsection_title,
                            "full_title": f"{section_title} - {subsection_title}",
                            "url": clean_subsection_url,
                            "pdf_path": subsection_pdf_path,
                            "parent_section": section_title,
                            "type": "subsection",
                        }
                        pdf_index.append(subsection_entry)
                        processed_urls.add(clean_subsection_url)
                        stats["subsections_downloaded"] += 1

                        # Save index after each PDF
                        with open(index_path, "w", encoding="utf-8") as f:
                            json.dump(pdf_index, f, indent=2, ensure_ascii=False)
                else:
                    print(f"Subsection already processed: {subsection_title}")

                # Find in-depth links in the subsection
                # Navigate to the subsection page
                driver.get(subsection_url)
                handle_cookie_consent(driver)

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except TimeoutException:
                    print(
                        "Timeout waiting for subsection page to load. Continuing anyway..."
                    )

                time.sleep(2)

                # Look for in-depth links
                print("Looking for in-depth content...")
                section_base_path = subsection_url.replace(base_url, "")
                section_base_path = strip_url_fragment(
                    section_base_path
                )  # Remove any fragments
                in_depth_links = extract_content_from_page(
                    driver, subsection_url, section_base_path
                )

                # Filter to valid in-depth links
                filtered_links = []
                seen_clean_urls = set()

                for link in in_depth_links:
                    # Skip if not relevant for cats/dogs
                    if not is_relevant_title(link["title"]):
                        stats["skipped_irrelevant"] += 1
                        continue

                    clean_link_url = strip_url_fragment(link["url"])

                    # Skip if we've already seen this base URL in the current subsection
                    if clean_link_url in seen_clean_urls:
                        continue

                    if (
                        section_base_path in clean_link_url
                        and clean_link_url != strip_url_fragment(subsection_url)
                    ):
                        filtered_links.append(link)
                        seen_clean_urls.add(clean_link_url)

                print(
                    f"Found {len(filtered_links)} relevant in-depth links for {subsection_title}"
                )

                # Process each in-depth link
                for link_idx, link in enumerate(filtered_links, 1):
                    link_title = link["title"]
                    link_url = link["url"]

                    print(
                        f"[{link_idx}/{len(filtered_links)}] Processing link: {link_title}"
                    )
                    stats["in_depth_processed"] += 1

                    # Add link to index if not already processed
                    clean_link_url = strip_url_fragment(link_url)
                    if clean_link_url not in processed_urls:
                        # Download in-depth link PDF
                        full_title = (
                            f"{section_title} - {subsection_title} - {link_title}"
                        )
                        link_pdf_path = save_page_as_pdf(
                            driver, full_title, link_url, pdf_dir
                        )

                        # Add to index
                        if link_pdf_path:
                            link_entry = {
                                "title": link_title,
                                "full_title": full_title,
                                "url": clean_link_url,
                                "original_url": link.get(
                                    "original_url", link_url
                                ),  # Keep original URL with fragment
                                "pdf_path": link_pdf_path,
                                "parent_section": section_title,
                                "parent_subsection": subsection_title,
                                "type": "in_depth",
                            }
                            pdf_index.append(link_entry)
                            processed_urls.add(clean_link_url)
                            stats["in_depth_downloaded"] += 1

                            # Save index after each PDF
                            with open(index_path, "w", encoding="utf-8") as f:
                                json.dump(pdf_index, f, indent=2, ensure_ascii=False)
                    else:
                        print(f"Link already processed: {link_title}")

                    # Rate limiting
                    time.sleep(1)

                # Rate limiting between subsections
                time.sleep(1)

            # Rate limiting between sections
            time.sleep(2)

        # Final save of the index
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(pdf_index, f, indent=2, ensure_ascii=False)

        print(f"\n=== Summary ===")
        print(f"Total PDFs downloaded: {len(pdf_index)}")
        print(
            f"Sections processed: {stats['sections_processed']}, downloaded: {stats['sections_downloaded']}"
        )
        print(
            f"Subsections processed: {stats['subsections_processed']}, downloaded: {stats['subsections_downloaded']}"
        )
        print(
            f"In-depth links processed: {stats['in_depth_processed']}, downloaded: {stats['in_depth_downloaded']}"
        )
        print(f"Content skipped (irrelevant animals): {stats['skipped_irrelevant']}")
        print(f"PDF index saved to: {os.path.abspath(index_path)}")
        print(f"All PDFs saved to: {os.path.abspath(pdf_dir)}")

    except Exception as e:
        print(f"Error during processing: {e}")

        # Save whatever we have in case of error
        if pdf_index:
            try:
                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(pdf_index, f, indent=2, ensure_ascii=False)
                print(f"Saved partial index with {len(pdf_index)} entries")
            except Exception as save_error:
                print(f"Error saving index: {save_error}")

    finally:
        # Clean up
        if "driver" in locals():
            driver.quit()
            print("WebDriver closed")


if __name__ == "__main__":
    download_pdfs_and_build_index()
