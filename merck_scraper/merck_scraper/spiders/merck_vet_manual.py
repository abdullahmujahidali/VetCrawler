import logging

import scrapy
from merck_scraper.items import TopicItem


class MerckVetManualSpider(scrapy.Spider):
    name = "merck_vet_manual"
    allowed_domains = ["www.merckvetmanual.com"]
    start_urls = ["https://www.merckvetmanual.com/veterinary-topics"]

    def parse(self, response):
        """
        Parse the main veterinary topics page to extract all sections.
        """
        self.logger.info(f"Parsing: {response.url}")

        # Based on the HTML structure from the screenshot:
        # Target the section items directly
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
        """
        Parse individual section pages to extract topics.
        """
        section_title = response.meta["section"]
        self.logger.info(f"Parsing section page: {section_title} at {response.url}")

        # Extract topics on the section page
        # This will need to be adjusted based on the structure of section pages
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
