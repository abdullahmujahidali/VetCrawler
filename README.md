# Merck Vet Manual Scraper

A Scrapy-based web scraper for extracting veterinary information from the Merck Veterinary Manual website.

## Features

- Extracts all sections and topics from the Merck Veterinary Manual
- Two scraper options:
  - Basic scraper (`merck_vet_manual`): Extracts section and topic names with URLs
  - Full scraper (`merck_vet_manual_full`): Also extracts content from each topic page
- Organized output in JSON format
- Respectful crawling with built-in delays and rate limiting

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/abdullahmujahidali/VetCrawler.git
   cd merck-vet-scraper
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Scraper

To run the basic scraper that extracts sections and topics:

```bash
cd merck_scraper
scrapy crawl merck_vet_manual -o topics.json
```

### Full Scraper

To run the full scraper that also extracts content from topic pages:

```bash
cd merck_scraper
scrapy crawl merck_vet_manual_full -o full_topics.json
```

### Using the Run Script

For more options, use the included run script:

```bash
cd merck_scraper
python merck_scraper/run_scraper.py --full --format json --output custom_output.json
```

Options:
- `--full`: Use the full scraper instead of the basic one
- `--format`: Output format (json, csv, xml)
- `--output`: Custom output file path
- `--limit`: Limit the number of items to scrape

## Debug Tool

To help debug CSS selectors, use the included debug tool:

```bash
python debug_selector.py --url "https://www.merckvetmanual.com/veterinary-topics" --selector "div#bodyContent a[href*='/']"
```

Options:
- `--url`: URL to test selectors against
- `--selector`: CSS selector to test
- `--limit`: Limit the number of results to display
- `--output`: Output file for full results

## Output Structure

The scraped data is saved in the following format:

```json
{
  "Main Categories": [
    {
      "section": "Main Categories",
      "topic_name": "Behavior",
      "topic_url": "https://www.merckvetmanual.com/behavior"
    },
    ...
  ],
  "Behavior": [
    {
      "section": "Behavior",
      "topic_name": "Normal Social Behavior",
      "topic_url": "https://www.merckvetmanual.com/behavior/normal-social-behavior"
    },
    ...
  ],
  ...
}
```

## Troubleshooting

If you encounter issues:

1. **No items scraped**: The website structure might have changed. Try using the debug tool to identify the correct CSS selectors.

2. **Rate limiting**: You might be hitting the site too fast. Increase the `DOWNLOAD_DELAY` in settings.py.

3. **Blocked by the site**: Ensure you're respecting `robots.txt` and using an appropriate user agent.

## Ethical Considerations

This scraper is designed for educational and research purposes only. Please be respectful of the website's resources by:

- Keeping the crawl rate slow (default settings are already conservative)
- Respecting the robots.txt
- Not overloading their servers with too many requests
