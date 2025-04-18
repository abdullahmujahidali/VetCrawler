import logging

import scrapy
from merck_scraper.items import TopicItem
from scrapy.utils.log import configure_logging


class MerckVetManualFullSpider(scrapy.Spider):
    name = "merck_vet_manual_full"
    allowed_domains = ["www.merckvetmanual.com"]
    start_urls = ["https://www.merckvetmanual.com/veterinary-topics"]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,  # Be more conservative when crawling deeper
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "ITEM_PIPELINES": {
            "merck_scraper.pipelines.MerckScraperPipeline": 300,
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configure_logging(install_root_handler=False)
        logging.basicConfig(
            filename="merck_scraper.log",
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            level=logging.INFO,
        )

    def parse(self, response):
        """Parse the main veterinary topics page."""
        self.logger.info(f"Parsing main page: {response.url}")

        # Based on the HTML structure from the screenshot:
        # Target the section items directly with the specific class
        sections = response.css("div.SectionList_sectionListItem__NNP4c a")

        self.logger.info(f"Found {len(sections)} sections")

        for section in sections:
            section_title = section.css("::text").get().strip()
            section_url = response.urljoin(section.css("::attr(href)").get())
            self.logger.info(f"Processing section: {section_title}")

            # Create an item for each section
            item = TopicItem()
            item["section"] = "Main Categories"
            item["topic_name"] = section_title
            item["topic_url"] = section_url

            yield item

            # Follow the section link to extract topics within that section
            yield scrapy.Request(
                url=section_url,
                callback=self.parse_section_page,
                meta={"section": section_title},
            )

    def parse_section_page(self, response):
        """Parse individual section pages to extract topics."""
        section_title = response.meta["section"]
        self.logger.info(f"Parsing section page: {section_title} at {response.url}")

        # Extract topics on the section page
        # Try multiple selectors to catch different page structures
        topics = response.css("div.topic-list a, ul.topic-list li a")

        if not topics:
            # Try alternative selectors based on common patterns
            topics = response.css('a[href*="/"]')

            # Filter to links that are likely topics (not navigation, footer, etc.)
            filtered_topics = []
            base_path = response.url.rstrip("/")

            for topic in topics:
                href = topic.css("::attr(href)").get()
                if href and not href.startswith(("#", "javascript:", "http")):
                    # Convert to absolute URL
                    topic_url = response.urljoin(href)

                    # Skip if it's the same as the section page
                    if topic_url == response.url:
                        continue

                    # Check if it's a deeper path (likely a topic)
                    if topic_url.startswith(base_path + "/"):
                        filtered_topics.append(topic)

            topics = filtered_topics

        self.logger.info(f"Found {len(topics)} topics in section {section_title}")

        for topic in topics:
            topic_name = topic.css("::text").get()
            if not topic_name:
                continue

            topic_name = topic_name.strip()
            topic_url = response.urljoin(topic.css("::attr(href)").get())

            # Skip if it's not a valid topic
            if not topic_name:
                continue

            item = TopicItem()
            item["section"] = section_title
            item["topic_name"] = topic_name
            item["topic_url"] = topic_url

            self.logger.debug(f"Extracted topic: {topic_name} - {topic_url}")
            yield item

            # Follow the link to get content for full spider
            yield scrapy.Request(
                url=topic_url,
                callback=self.parse_topic_page,
                meta={"item": item},
                priority=1,  # Higher priority for initial topics
            )

    def parse_topic_page(self, response):
        """Parse individual topic pages to extract content."""
        item = response.meta["item"]
        self.logger.info(f'Parsing topic page: {item["topic_name"]} at {response.url}')

        # Extract main content
        content_section = response.css("div#bodyContent, div.topic-content, article")
        if content_section:
            # Extract text content
            paragraphs = content_section.css("p::text, p *::text").getall()
            clean_paragraphs = [p.strip() for p in paragraphs if p.strip()]

            # Extract headings
            headings = content_section.css(
                "h1::text, h2::text, h3::text, h4::text"
            ).getall()
            clean_headings = [h.strip() for h in headings if h.strip()]

            # Extract tables (if any)
            tables = content_section.css("table").getall()

            # Extract images (if any)
            images = content_section.css("img::attr(src)").getall()
            image_urls = [response.urljoin(img) for img in images]

            # Store everything in our item
            item["content"] = {
                "paragraphs": clean_paragraphs,
                "headings": clean_headings,
                "tables": tables,
                "image_urls": image_urls,
            }

        yield item
