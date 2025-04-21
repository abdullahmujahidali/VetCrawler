# Using Scrapy-Selenium
import json
import re

import scrapy
from scrapy_selenium import SeleniumRequest


class MerckvetmanualSpider(scrapy.Spider):
    name = "merckvetmanual"

    # Define custom settings for this spider
    custom_settings = {
        "FEED_FORMAT": "json",
        "FEED_URI": "merck_sections.json",
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def start_requests(self):
        yield SeleniumRequest(
            url="https://www.merckvetmanual.com/veterinary-topics", callback=self.parse
        )

    def parse(self, response):
        # Look for the data in the __NEXT_DATA__ script tag
        script_data = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()

        if script_data:
            try:
                data = json.loads(script_data)
                # Navigate to the section data in the JSON structure
                section_data = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("componentProps", {})
                    .get("eb190e7b-5914-4f3d-91a8-3fa8542b6178", {})
                    .get("data", [])
                )

                # Extract the sections
                for item in section_data:
                    title = item.get("titlecomputed_t", "")
                    path = item.get("relativeurlcomputed_s", "")

                    if title and path:
                        url = f"https://www.merckvetmanual.com{path}"
                        yield {"title": title, "url": url}
                        self.log(f"Found section: {title} - {url}")

            except json.JSONDecodeError as e:
                self.log(f"Failed to parse JSON data: {e}")
            except Exception as e:
                self.log(f"An error occurred: {e}")

        else:
            self.log("Could not find __NEXT_DATA__ script")

            # Fallback: Try to extract using CSS selectors
            self.log("Trying fallback extraction method...")
            section_items = response.css("div.SectionList_sectionListItem__NNP4c a")

            if section_items:
                for link in section_items:
                    text = link.css("::text").get()
                    href = link.css("::attr(href)").get()

                    if text and href:
                        text = text.strip()
                        url = response.urljoin(href)
                        yield {"title": text, "url": url}
                        self.log(f"Found section (fallback): {text} - {url}")
