# Using Scrapy-Selenium
import json
import re
import os
from pathlib import Path

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
        # First run: Scrape the main sections
        if not hasattr(self, 'scrape_subsections') or not self.scrape_subsections:
            yield SeleniumRequest(
                url="https://www.merckvetmanual.com/veterinary-topics", 
                callback=self.parse
            )
        # Second run: Scrape subsections from each section
        else:
            try:
                # Read the sections JSON file
                json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'merck_sections.json')
                with open(json_path, 'r', encoding='utf-8') as f:
                    sections = json.load(f)
                
                # Create output directory if it doesn't exist
                output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'section_data')
                Path(output_dir).mkdir(exist_ok=True)
                
                # Visit each section URL
                for section in sections:
                    title = section.get('title')
                    url = section.get('url')
                    if title and url:
                        yield SeleniumRequest(
                            url=url,
                            callback=self.parse_section,
                            meta={'section_title': title}
                        )
            except Exception as e:
                self.log(f"Error loading sections: {e}")

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
    
    def parse_section(self, response):
        section_title = response.meta.get('section_title')
        self.log(f"Parsing subsections for: {section_title}")
        
        subsections = []
        section_path = response.url.split("merckvetmanual.com")[1]
        self.log(f"Processing URL: {response.url}, section path: {section_path}")
        
        # List of navigation text patterns to exclude
        nav_patterns = ['veterinary professionals', 'pet owners', 'resources', 'quizzes', 'about', 
                        'login', 'register', 'search', 'home', 'contact', 'legal', 'privacy', 
                        'advertise', 'careers', 'help', 'terms', 'support', 'faq', 'feedback',
                        'menu', 'share', 'print']
        
        # Based on the screenshot, we can see that subsections are structured as part of a list/tree
        # First, try to get subsections from the main content area
        
        # 1. First approach - based on the screenshot structure
        self.log("Method 1: Looking for subsection elements matching the screenshot structure")
        
        # Look for specific patterns like the ones in the screenshot
        # These are the main sections like "Hematopoietic System Introduction", "Anemia", etc.
        main_topic_links = response.css("div.SectionLayout_subsectionExpanded__SJT_i h2 a, h2.SectionLayout_subsectionTitle__Lrw_e a")
        if not main_topic_links:
            main_topic_links = response.css('[class*="section"] > h2 a, [class*="Section"] > h2 a')
        
        self.log(f"Found {len(main_topic_links)} main topic links")
        for link in main_topic_links:
            text = link.css("::text").get()
            href = link.css("::attr(href)").get()
            
            if text and href:
                text = text.strip()
                url = response.urljoin(href)
                # Only add if it's not a navigation link and contains the section path or is a related subsection
                if (text.lower() not in nav_patterns and 
                    len(text) > 3 and
                    (section_path in href or href.startswith(f"/{section_path.lstrip('/')}"))):
                    subsections.append({"title": text, "url": url})
                    self.log(f"Method 1 - Found main subsection: {text}")
        
        # 2. Look for subsection links like "Overview of Hematopoietic System in Animals"
        # These are usually under the main sections
        self.log("Method 2: Looking for specific subsection links")
        
        # The subsections are often items in a list or have specific CSS classes
        subtopic_links = response.css('[class*="subsection"] a, li a, ul a, ol a')
        
        for link in subtopic_links:
            text = link.css("::text").get()
            href = link.css("::attr(href)").get()
            
            if text and href:
                text = text.strip()
                url = response.urljoin(href)
                
                # Include only if:
                # 1. It's not a navigation link
                # 2. Contains the current section's path in the URL
                # 3. Text length is reasonable for a topic (not too short)
                is_nav = any(pattern in text.lower() for pattern in nav_patterns)
                is_related = (section_path in href or 
                             href.startswith(f"/{section_path.lstrip('/')}") or
                             section_title.lower() in text.lower())
                
                if not is_nav and is_related and len(text) > 3:
                    subsections.append({"title": text, "url": url})
                    self.log(f"Method 2 - Found subsection: {text}")
        
        # 3. Use the __NEXT_DATA__ script - this might have structured data
        if not subsections:
            self.log("Method 3: Checking for __NEXT_DATA__ structured data")
            script_data = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
            
            if script_data:
                try:
                    data = json.loads(script_data)
                    self.log("Found __NEXT_DATA__ script")
                    
                    # Look for section data in the page props
                    page_props = data.get("props", {}).get("pageProps", {})
                    component_props = page_props.get("componentProps", {})
                    
                    # Iterate through the componentProps to find subsection data
                    for key, value in component_props.items():
                        if isinstance(value, dict) and "data" in value:
                            data_items = value.get("data", [])
                            for item in data_items:
                                title = item.get("titlecomputed_t", "")
                                path = item.get("relativeurlcomputed_s", "")
                                
                                # Make sure the path is related to this section
                                if title and path and section_path in path:
                                    url = f"https://www.merckvetmanual.com{path}"
                                    subsections.append({"title": title, "url": url})
                                    self.log(f"Method 3 - Found subsection from JSON: {title}")
                except Exception as e:
                    self.log(f"Failed to parse JSON data: {e}")
        
        # 4. As a fallback, look for all links within the main content area
        # that might be subsections based on URL pattern
        if not subsections:
            self.log("Method 4: Fallback to find links with specific subsection patterns")
            
            # Look for links that have a URL pattern suggesting they're subsections
            # Example: /circulatory-system/anemia
            all_links = response.css("a[href^='/']")
            section_pattern = section_path.strip("/")
            
            for link in all_links:
                text = link.css("::text").get()
                href = link.css("::attr(href)").get()
                
                if (text and href and 
                    len(text) > 3 and 
                    section_pattern in href and 
                    href != section_path and
                    not any(pattern in text.lower() for pattern in nav_patterns)):
                    
                    # Check if this is likely a subsection URL (contains more path segments)
                    href_parts = href.strip("/").split("/")
                    if len(href_parts) > 1:
                        text = text.strip()
                        url = response.urljoin(href)
                        subsections.append({"title": text, "url": url})
                        self.log(f"Method 4 - Found subsection by URL pattern: {text}")
        
        # Remove duplicates while preserving order
        unique_subsections = []
        seen_urls = set()
        for item in subsections:
            if item['url'] not in seen_urls:
                # Final validation check to exclude navigation items
                if not any(pattern in item['title'].lower() for pattern in nav_patterns):
                    unique_subsections.append(item)
                    seen_urls.add(item['url'])
        
        self.log(f"Found {len(unique_subsections)} unique subsections for {section_title}")
        
        # Save subsections to a JSON file named after the section
        if unique_subsections:
            try:
                # Sanitize the title for use as a filename
                safe_title = re.sub(r'[\\/*?:"<>|]', "_", section_title)
                
                # Ensure section_data directory exists
                output_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'section_data'
                )
                os.makedirs(output_dir, exist_ok=True)
                
                output_path = os.path.join(output_dir, f"{safe_title}.json")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(unique_subsections, f, indent=2, ensure_ascii=False)
                
                self.log(f"Successfully saved {len(unique_subsections)} subsections for {section_title} to {output_path}")
            except Exception as e:
                self.log(f"Error saving subsections for {section_title}: {e}")
        else:
            self.log(f"No subsections found for {section_title}")
