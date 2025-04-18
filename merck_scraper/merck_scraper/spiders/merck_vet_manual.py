import logging

import scrapy
from merck_scraper.items import TopicItem


class MerckVetManualSpider(scrapy.Spider):
    name = "merck_vet_manual"
    allowed_domains = ["www.merckvetmanual.com"]
    start_urls = ["https://www.merckvetmanual.com/veterinary-topics"]

    def parse(self, response):
        """
        Parse the main veterinary topics page to extract all sections and their topics.
        """
        self.logger.info(f"Parsing: {response.url}")

        # Updated selector to find all section links
        # Based on the screenshot, the sections are simple links in a two-column layout
        sections = response.css('div#bodyContent a[href*="/"]')
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
        # This needs to be adjusted based on the actual structure of section pages
        topics = response.css("div.topic-list a, ul.topic-list li a")

        if not topics:
            # Try alternative selectors if the above doesn't work
            topics = response.css('div#bodyContent a[href*="/"]')

        self.logger.info(f"Found {len(topics)} topics in section {section_title}")

        for topic in topics:
            topic_name = topic.css("::text").get().strip()
            topic_url = response.urljoin(topic.css("::attr(href)").get())

            # Skip if it's the same as the section page or if it's not a valid topic
            if topic_url == response.url or not topic_name:
                continue

            item = TopicItem()
            item["section"] = section_title
            item["topic_name"] = topic_name
            item["topic_url"] = topic_url

            self.logger.debug(f"Extracted topic: {topic_name} - {topic_url}")
            yield item
