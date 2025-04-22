import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class MerckvetmanualSpider(scrapy.Spider):
    name = "merckvetmanual"
    allowed_domains = ["merckvetmanual.com"]
    base_url = "https://www.merckvetmanual.com"

    custom_settings = {
        "FEED_FORMAT": "json",
        "FEED_URI": "merck_manual_complete.json",
        "FEED_EXPORT_ENCODING": "utf-8",
        "DOWNLOAD_TIMEOUT": 30,
        "DOWNLOAD_DELAY": 2,
        "SELENIUM_DRIVER_ARGUMENTS": [
            "--headless",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    def __init__(self, *args, **kwargs):
        super(MerckvetmanualSpider, self).__init__(*args, **kwargs)
        self.nav_patterns = [
            "veterinary professionals",
            "pet owners",
            "resources",
            "quizzes",
            "about",
            "login",
            "register",
            "search",
            "home",
            "contact",
            "legal",
            "privacy",
            "advertise",
            "careers",
            "help",
            "terms",
            "support",
            "faq",
            "feedback",
            "menu",
            "share",
            "print",
            "cookie preferences",
            "cookie",
        ]

        self.all_sections = {}
        self.test_mode = kwargs.get("test", False)

    def start_requests(self):
        yield SeleniumRequest(
            url="https://www.merckvetmanual.com/veterinary-topics",
            callback=self.parse_main_page,
            wait_time=10,
            screenshot=False,
            dont_filter=True,
        )

    def parse_main_page(self, response):
        self.log("Parsing main veterinary topics page")
        sections = self.extract_from_next_data(response)
        if not sections:
            self.log("Trying fallback extraction method using CSS selectors")
            sections = self.extract_from_css(response)

        if not sections:
            self.log("No sections found using any method!")
            return

        self.log(f"Found {len(sections)} total sections")
        if self.test_mode:
            sections = sections[:3]
            self.log(f"TEST MODE: Only processing {len(sections)} sections")

        for section in sections:
            self.all_sections[section["url"]] = {
                "title": section["title"],
                "url": section["url"],
                "subsections": [],
            }

            yield SeleniumRequest(
                url=section["url"],
                callback=self.parse_section,
                wait_time=8,
                meta={"section_url": section["url"]},
                dont_filter=True,
            )

    def extract_from_next_data(self, response):
        """Extract sections from __NEXT_DATA__ script"""
        try:
            script_data = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
            if not script_data:
                return []

            data = json.loads(script_data)
            section_data = (
                data.get("props", {})
                .get("pageProps", {})
                .get("componentProps", {})
                .get("eb190e7b-5914-4f3d-91a8-3fa8542b6178", {})
                .get("data", [])
            )
            sections = []
            for item in section_data:
                title = item.get("titlecomputed_t", "")
                path = item.get("relativeurlcomputed_s", "")

                if title and path:
                    url = f"{self.base_url}{path}"
                    sections.append({"title": title, "url": url})
                    self.log(f"Found section from JSON: {title}")

            return sections

        except Exception as e:
            self.log(f"Error extracting from __NEXT_DATA__: {e}")
            return []

    def extract_from_css(self, response):
        """Extract sections using CSS selectors as fallback"""
        sections = []
        section_items = response.css(
            "div.SectionList_sectionListItem__NNP4c a, a.SectionList_sectionListItem__NNP4c"
        )

        if not section_items:
            section_items = response.css(
                "div[class*='section'] > a, a[href^='/'][class*='section']"
            )

        for link in section_items:
            text = link.css("::text").get()
            href = link.css("::attr(href)").get()

            if text and href:
                text = text.strip()
                url = response.urljoin(href)
                sections.append({"title": text, "url": url})
                self.log(f"Found section from CSS: {text}")

        return sections

    def parse_section(self, response):
        section_url = response.meta.get("section_url")
        if section_url not in self.all_sections:
            self.log(f"Section URL not found in data structure: {section_url}")
            return

        section = self.all_sections[section_url]
        section_title = section["title"]
        self.log(f"Parsing section: {section_title} - {section_url}")
        subsections = self.extract_subsections(response, section_url)
        self.all_sections[section_url]["subsections"] = subsections

        self.log(f"Found {len(subsections)} subsections for {section_title}")
        for subsection in subsections:
            yield SeleniumRequest(
                url=subsection["url"],
                callback=self.parse_subsection,
                wait_time=5,
                meta={"section_url": section_url, "subsection_url": subsection["url"]},
                dont_filter=True,
            )
            time.sleep(0.5)

    def get_path_from_url(self, url):
        """Safely extract path from URL"""
        try:
            if "merckvetmanual.com" in url:
                parsed = urlparse(url)
                return parsed.path.strip("/")
            return ""
        except Exception:
            return ""

    def extract_subsections(self, response, section_url):
        """Extract subsections from a section page"""
        section_path = self.get_path_from_url(section_url)
        subsections = []
        subsection_headers = response.css(
            "div.SectionLayout_subsectionExpanded__SJT_i h2 a, "
            "h2.SectionLayout_subsectionTitle__Lrw_e a, "
            "div[class*='subsection'] h2 a, "
            "h2[class*='subsection'] a"
        )

        for link in subsection_headers:
            text = link.css("::text").get()
            href = link.css("::attr(href)").get()

            if text and href:
                text = text.strip()
                url = response.urljoin(href)
                if url != section_url and text.lower() not in self.nav_patterns:
                    url_path = self.get_path_from_url(url)
                    if (
                        section_path
                        and section_path in url_path
                        and section_path != url_path
                    ):
                        subsections.append(
                            {"title": text, "url": url, "in_depth_links": []}
                        )
                        self.log(f"Found subsection from headers: {text}")
        list_links = response.css("ul li a, ol li a")

        for link in list_links:
            text = link.css("::text").get()
            href = link.css("::attr(href)").get()

            if text and href:
                text = text.strip()
                url = response.urljoin(href)
                if url != section_url and text.lower() not in self.nav_patterns:
                    url_path = self.get_path_from_url(url)
                    if (
                        section_path
                        and section_path in url_path
                        and section_path != url_path
                    ):
                        if not any(s["url"] == url for s in subsections):
                            subsections.append(
                                {"title": text, "url": url, "in_depth_links": []}
                            )
                            self.log(f"Found subsection from lists: {text}")
        script_data = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()

        if script_data:
            try:
                data = json.loads(script_data)
                component_props = (
                    data.get("props", {}).get("pageProps", {}).get("componentProps", {})
                )

                for key, value in component_props.items():
                    if isinstance(value, dict) and "data" in value:
                        items = value.get("data", [])

                        for item in items:
                            title = item.get("titlecomputed_t", "")
                            path = item.get("relativeurlcomputed_s", "")

                            if title and path:
                                url = f"{self.base_url}{path}"
                                if url != section_url:
                                    url_path = path.strip("/")
                                    if (
                                        section_path
                                        and section_path in url_path
                                        and section_path != url_path
                                    ):
                                        if not any(
                                            s["url"] == url for s in subsections
                                        ):
                                            subsections.append(
                                                {
                                                    "title": title,
                                                    "url": url,
                                                    "in_depth_links": [],
                                                }
                                            )
                                            self.log(
                                                f"Found subsection from JSON: {title}"
                                            )
            except Exception as e:
                self.log(f"Error extracting subsections from JSON: {e}")
        if not subsections:
            self.log("Trying more general link extraction for subsections")
            general_links = response.css("a[href^='/']")

            for link in general_links:
                text = link.css("::text").get()
                href = link.css("::attr(href)").get()

                if text and href and len(text.strip()) > 3:
                    text = text.strip()
                    url = response.urljoin(href)

                    if url != section_url and text.lower() not in self.nav_patterns:
                        url_path = self.get_path_from_url(url)
                        if (
                            section_path
                            and section_path in url_path
                            and section_path != url_path
                        ):
                            if not any(s["url"] == url for s in subsections):
                                subsections.append(
                                    {"title": text, "url": url, "in_depth_links": []}
                                )
                                self.log(f"Found subsection from general links: {text}")
        clean_subsections = []
        seen_urls = set()

        for subsection in subsections:
            if subsection["url"] not in seen_urls:
                seen_urls.add(subsection["url"])
                if subsection["url"] != section_url:
                    clean_subsections.append(subsection)

        return clean_subsections

    def parse_subsection(self, response):
        section_url = response.meta.get("section_url")
        subsection_url = response.meta.get("subsection_url")
        if section_url not in self.all_sections:
            self.log(f"Section URL not found in data: {section_url}")
            return
        section = self.all_sections[section_url]
        subsection_index = next(
            (
                i
                for i, s in enumerate(section["subsections"])
                if s["url"] == subsection_url
            ),
            None,
        )

        if subsection_index is None:
            self.log(f"Subsection URL not found in data: {subsection_url}")
            return

        subsection = section["subsections"][subsection_index]

        self.log(f"Parsing in-depth links for: {subsection['title']}")
        in_depth_links = self.extract_in_depth_links(
            response, section_url, subsection_url
        )
        self.all_sections[section_url]["subsections"][subsection_index][
            "in_depth_links"
        ] = in_depth_links

        self.log(
            f"Found {len(in_depth_links)} in-depth links for {subsection['title']}"
        )

    def extract_in_depth_links(self, response, section_url, subsection_url):
        """Extract in-depth links from a subsection page"""
        section_path = self.get_path_from_url(section_url)
        in_depth_links = []
        content_links = response.css(
            "ul li a, ol li a, div[class*='content'] a, "
            "div[class*='topic'] a, div[class*='subsection'] a"
        )

        for link in content_links:
            text = link.css("::text").get()
            href = link.css("::attr(href)").get()

            if text and href:
                text = text.strip()
                url = response.urljoin(href)
                link_path = self.get_path_from_url(url)
                if (
                    url != section_url
                    and url != subsection_url
                    and text.lower() not in self.nav_patterns
                    and len(text) > 3
                ):
                    if (
                        section_path
                        and section_path in link_path
                        and link_path != section_path
                    ):
                        in_depth_links.append({"title": text, "url": url})
                        self.log(f"Found in-depth link: {text}")
        clean_links = []
        seen_urls = set()

        for link in in_depth_links:
            if link["url"] not in seen_urls:
                seen_urls.add(link["url"])
                clean_links.append(link)

        return clean_links

    def closed(self, reason):
        """Called when the spider is closed"""
        sections_list = list(self.all_sections.values())
        non_empty_sections = [
            section for section in sections_list if section.get("subsections")
        ]

        output_path = "merck_manual_final.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(non_empty_sections, f, indent=2, ensure_ascii=False)
        total_sections = len(sections_list)
        non_empty_section_count = len(non_empty_sections)
        total_subsections = sum(
            len(section.get("subsections", [])) for section in sections_list
        )
        total_in_depth = sum(
            sum(
                len(subsection.get("in_depth_links", []))
                for subsection in section.get("subsections", [])
            )
            for section in sections_list
        )

        self.log(f"\n==== Crawling Complete ====")
        self.log(f"Total sections: {total_sections}")
        self.log(f"Sections with subsections: {non_empty_section_count}")
        self.log(f"Total subsections: {total_subsections}")
        self.log(f"Total in-depth links: {total_in_depth}")
        self.log(f"Final data saved to: {output_path}")
        self.log(f"Reason for closing: {reason}")
