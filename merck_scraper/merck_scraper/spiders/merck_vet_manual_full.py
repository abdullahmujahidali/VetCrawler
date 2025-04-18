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

        # Extract all sections
        sections = response.css("div.topic-container")
        self.logger.info(f"Found {len(sections)} sections")

        for section in sections:
            section_title = section.css("h2::text").get().strip()
            self.logger.info(f"Processing section: {section_title}")

            # Extract all topics under this section
            topics = section.css("ul.topic-list li")

            for topic in topics:
                topic_name = topic.css("a::text").get().strip()
                topic_url = response.urljoin(topic.css("a::attr(href)").get())

                # Create a base item
                item = TopicItem()
                item["section"] = section_title
                item["topic_name"] = topic_name
                item["topic_url"] = topic_url

                # Follow the link to get content
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
        content_section = response.css("div.topic-content")
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

            # Find subtopic links and follow them if needed
            subtopic_links = response.css(
                'div.topic-content a[href*="/veterinary-topics/"]::attr(href)'
            ).getall()
            if subtopic_links:
                self.logger.info(
                    f'Found {len(subtopic_links)} subtopics for {item["topic_name"]}'
                )
                # You could follow these links with another request if needed

        yield item
