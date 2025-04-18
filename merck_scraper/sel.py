import argparse
import json
import logging
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("selenium_scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class MerckVetManualSeleniumScraper:
    """Selenium-based scraper for the Merck Veterinary Manual."""

    def __init__(self, headless=True):
        """Initialize the scraper with browser settings."""
        self.base_url = "https://www.merckvetmanual.com"
        self.sections_by_category = {}

        # Set up Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Add a standard user agent
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        # Initialize WebDriver
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)

        logger.info("Selenium WebDriver initialized")

    def scrape_main_categories(self):
        """Scrape main categories from the veterinary topics page."""
        url = f"{self.base_url}/veterinary-topics"
        logger.info(f"Navigating to: {url}")

        self.driver.get(url)
        time.sleep(5)  # Allow page to fully load

        # Save page source for debugging
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        logger.info("Saved page source to page_source.html")

        try:
            # Wait for the sections to load (adjust selector based on inspection)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.Sections, div.section-list, div#bodyContent")
                )
            )

            # Try multiple approaches to find sections
            sections = []

            # Try to find a heading that says "Sections"
            try:
                sections_heading = self.driver.find_element(
                    By.XPATH, "//h2[contains(text(), 'Sections')]"
                )
                logger.info("Found 'Sections' heading")

                # Look for links in the next div
                section_container = sections_heading.find_element(
                    By.XPATH, "./following-sibling::div"
                )
                sections = section_container.find_elements(By.TAG_NAME, "a")
                logger.info(
                    f"Found {len(sections)} sections under the 'Sections' heading"
                )
            except NoSuchElementException:
                logger.info(
                    "Could not find 'Sections' heading, trying alternative approaches"
                )

            # If we couldn't find sections that way, try a more general approach
            if not sections:
                # Try known section names from previous scraping attempts
                section_names = [
                    "Behavior",
                    "Circulatory System",
                    "Clinical Pathology",
                    "Digestive System",
                    "Ear Disorders",
                    "Emergency Medicine",
                ]

                for name in section_names:
                    try:
                        # Look for links containing these section names
                        link = self.driver.find_element(
                            By.XPATH, f"//a[contains(text(), '{name}')]"
                        )
                        sections.append(link)
                        logger.info(f"Found section by name: {name}")
                    except NoSuchElementException:
                        continue

            # If we still have no sections, try a broader approach
            if not sections:
                logger.info("Trying broader approach to find sections")

                # Get all links on the page
                all_links = self.driver.find_elements(By.TAG_NAME, "a")

                # Filter for links that look like section links
                for link in all_links:
                    href = link.get_attribute("href")
                    text = link.text.strip()

                    # Skip empty links, links to the current page, and non-section links
                    if (
                        not text
                        or not href
                        or href == url
                        or "#" in href
                        or "javascript:" in href
                        or text.lower() in ["login", "register", "home", "search"]
                    ):
                        continue

                    # Check if it's a direct child page (likely a section)
                    if href.startswith(self.base_url) and href.count("/") == 4:
                        sections.append(link)

            # Process the sections
            logger.info(f"Processing {len(sections)} sections")

            # Add sections to our data structure
            self.sections_by_category["Main Categories"] = []

            for section in sections:
                section_name = section.text.strip()
                section_url = section.get_attribute("href")

                if section_name and section_url:
                    logger.info(f"Found section: {section_name} - {section_url}")

                    # Add to our data structure
                    self.sections_by_category["Main Categories"].append(
                        {
                            "section": "Main Categories",
                            "topic_name": section_name,
                            "topic_url": section_url,
                        }
                    )

            return len(self.sections_by_category["Main Categories"]) > 0

        except TimeoutException:
            logger.error("Timed out waiting for sections to load")
            return False
        except Exception as e:
            logger.error(f"Error scraping main categories: {e}")
            return False

    def scrape_section_topics(self, full_content=False):
        """Scrape topics from each section."""
        if not self.sections_by_category.get("Main Categories"):
            logger.error("No main categories found. Run scrape_main_categories first.")
            return False

        # Process each section
        for section in self.sections_by_category["Main Categories"]:
            section_name = section["topic_name"]
            section_url = section["topic_url"]

            logger.info(f"Scraping topics for section: {section_name} at {section_url}")

            # Navigate to the section page
            self.driver.get(section_url)
            time.sleep(3)  # Allow page to load

            # Initialize list for this section's topics
            if section_name not in self.sections_by_category:
                self.sections_by_category[section_name] = []

            try:
                # Wait for the topic links to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "a"))
                )

                # Try different selectors to find topic links
                topic_links = []

                # Try to find a container for topics
                containers = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "div.topic-list, ul.topic-list, div#bodyContent, div.content",
                )

                for container in containers:
                    links = container.find_elements(By.TAG_NAME, "a")
                    if links:
                        logger.info(
                            f"Found {len(links)} potential topic links in container"
                        )
                        topic_links.extend(links)

                # If we didn't find topics in containers, try a more general approach
                if not topic_links:
                    # Get all links on the page
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")

                    # Filter for links that look like topic links
                    base_url_parts = section_url.strip("/").split("/")

                    for link in all_links:
                        href = link.get_attribute("href")
                        text = link.text.strip()

                        # Skip empty links, links to the current page, and non-topic links
                        if (
                            not text
                            or not href
                            or href == section_url
                            or "#" in href
                            or "javascript:" in href
                        ):
                            continue

                        # Check if it's a deeper path than the section (likely a topic)
                        href_parts = href.strip("/").split("/")
                        if href.startswith(section_url) or (
                            len(href_parts) > len(base_url_parts)
                            and all(a == b for a, b in zip(base_url_parts, href_parts))
                        ):
                            topic_links.append(link)

                # Process each topic
                logger.info(
                    f"Processing {len(topic_links)} topics in section {section_name}"
                )

                for topic in topic_links:
                    topic_name = topic.text.strip()
                    topic_url = topic.get_attribute("href")

                    if not topic_name or not topic_url:
                        continue

                    logger.info(f"Found topic: {topic_name} - {topic_url}")

                    # Create topic item
                    topic_item = {
                        "section": section_name,
                        "topic_name": topic_name,
                        "topic_url": topic_url,
                    }

                    # If we want full content, navigate to the topic page
                    if full_content:
                        topic_item["content"] = self.scrape_topic_content(topic_url)

                    # Add to our data structure
                    self.sections_by_category[section_name].append(topic_item)

            except TimeoutException:
                logger.error(
                    f"Timed out waiting for topics to load in section {section_name}"
                )
            except Exception as e:
                logger.error(f"Error scraping topics for section {section_name}: {e}")

        return True

    def scrape_topic_content(self, topic_url):
        """Scrape content from a topic page."""
        logger.info(f"Scraping content from: {topic_url}")

        # Navigate to the topic page
        self.driver.get(topic_url)
        time.sleep(3)  # Allow page to load

        content = {"paragraphs": [], "headings": [], "tables": [], "image_urls": []}

        try:
            # Wait for content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "p"))
            )

            # Find main content
            content_containers = self.driver.find_elements(
                By.CSS_SELECTOR, "div#bodyContent, div.topic-content, article, main"
            )

            if content_containers:
                main_content = content_containers[0]

                # Extract paragraphs
                paragraphs = main_content.find_elements(By.TAG_NAME, "p")
                content["paragraphs"] = [
                    p.text.strip() for p in paragraphs if p.text.strip()
                ]

                # Extract headings
                for level in range(1, 5):
                    headings = main_content.find_elements(By.TAG_NAME, f"h{level}")
                    content["headings"].extend(
                        [h.text.strip() for h in headings if h.text.strip()]
                    )

                # Extract tables
                tables = main_content.find_elements(By.TAG_NAME, "table")
                content["tables"] = [
                    table.get_attribute("outerHTML") for table in tables
                ]

                # Extract images
                images = main_content.find_elements(By.TAG_NAME, "img")
                content["image_urls"] = [
                    img.get_attribute("src")
                    for img in images
                    if img.get_attribute("src")
                ]

                logger.info(
                    f"Extracted {len(content['paragraphs'])} paragraphs, {len(content['headings'])} headings, "
                    f"{len(content['tables'])} tables, and {len(content['image_urls'])} images"
                )
            else:
                logger.warning("Could not find main content container")

        except TimeoutException:
            logger.error("Timed out waiting for content to load")
        except Exception as e:
            logger.error(f"Error scraping topic content: {e}")

        return content

    def save_results(self, output_file="selenium_topics.json"):
        """Save the scraped data to a JSON file."""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / output_file

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.sections_by_category, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved results to {output_path}")

    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")


def main():
    parser = argparse.ArgumentParser(
        description="Selenium-based scraper for Merck Veterinary Manual"
    )
    parser.add_argument(
        "--full", action="store_true", help="Scrape full content from topic pages"
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run in visible browser mode (not headless)",
    )
    parser.add_argument(
        "--output", default="selenium_topics.json", help="Output file name"
    )
    args = parser.parse_args()

    logger.info("Starting Selenium-based scraper")

    scraper = MerckVetManualSeleniumScraper(headless=not args.visible)

    try:
        # Scrape main categories
        if scraper.scrape_main_categories():
            logger.info("Successfully scraped main categories")

            # Scrape section topics
            if scraper.scrape_section_topics(full_content=args.full):
                logger.info("Successfully scraped section topics")
            else:
                logger.error("Failed to scrape section topics")
        else:
            logger.error("Failed to scrape main categories")

        # Save results
        scraper.save_results(output_file=args.output)

    finally:
        # Close the browser
        scraper.close()


if __name__ == "__main__":
    main()
