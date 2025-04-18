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
        sections = response.css("div.topic-container")
        self.logger.info(f"Found {len(sections)} sections")

        for section in sections:
            section_title = section.css("h2::text").get().strip()
            self.logger.info(f"Processing section: {section_title}")
            topics = section.css("ul.topic-list li")
            self.logger.info(f"Found {len(topics)} topics in section {section_title}")

            for topic in topics:
                item = TopicItem()
                item["section"] = section_title
                item["topic_name"] = topic.css("a::text").get().strip()
                item["topic_url"] = response.urljoin(topic.css("a::attr(href)").get())

                self.logger.debug(
                    f'Extracted topic: {item["topic_name"]} - {item["topic_url"]}'
                )
                yield item

                # If you want to follow each topic link and extract content:
                # yield scrapy.Request(
                #     url=item['topic_url'],
                #     callback=self.parse_topic_page,
                #     meta={'item': item}
                # )

    def parse_topic_page(self, response):
        """
        Parse individual topic pages to extract content.
        Uncomment this method if you want to crawl deeper into each topic.
        """
        item = response.meta["item"]

        # Extract content from the topic page
        # main_content = response.css('div.topic-content').get()
        # item['content'] = main_content

        # You could extract more detailed information here like:
        # - Subtopics
        # - Images
        # - Tables
        # - Related topics

        yield item
