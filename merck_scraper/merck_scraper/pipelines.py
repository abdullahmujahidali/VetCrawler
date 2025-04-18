import json
from pathlib import Path

from itemadapter import ItemAdapter


class MerckScraperPipeline:
    """Pipeline for processing and storing scraped items."""

    def open_spider(self, spider):
        """Initialize the pipeline when the spider starts."""
        self.items_by_section = {}

    def process_item(self, item, spider):
        """Process each scraped item."""
        adapter = ItemAdapter(item)

        # Clean data if needed
        adapter["topic_name"] = adapter["topic_name"].strip()

        # Group items by section
        section = adapter["section"]
        if section not in self.items_by_section:
            self.items_by_section[section] = []

        self.items_by_section[section].append(dict(adapter))

        return item

    def close_spider(self, spider):
        """Create an organized JSON file when the spider finishes."""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Save organized structure
        with open(output_dir / "organized_topics.json", "w", encoding="utf-8") as f:
            json.dump(self.items_by_section, f, ensure_ascii=False, indent=2)

        spider.logger.info(
            f"Saved organized data with {len(self.items_by_section)} sections"
        )
