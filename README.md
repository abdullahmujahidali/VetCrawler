# Merck Veterinary Manual Crawler

A web crawler for extracting veterinary information from the Merck Veterinary Manual website. The crawler is designed to extract all main sections and their subsections, and save them as JSON files.

## Features

- Extracts all main sections from the Merck Veterinary Manual
- Uses Selenium to handle JavaScript-rendered content
- Extracts subsections for each main section
- Saves data in well-structured JSON format
- Implements respectful crawling with rate limiting
- Handles dynamic content loading

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/abdullahmujahidali/VetCrawler.git
   cd crawler
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

The crawler works in two steps:

### Step 1: Extract Main Sections

First, run Scrapy to extract the main sections from the Merck Veterinary Manual:

```bash
cd merck
scrapy crawl merckvetmanual
```

This will create a `merck_sections.json` file containing all main sections with their URLs.

### Step 2: Extract Subsections

After extracting the main sections, use the Selenium-based crawler to extract subsections:

```bash
python selenium_solution.py
```

This will:
1. Read the `merck_sections.json` file
2. Visit each URL with Selenium to render JavaScript content
3. Extract all subsections for each main section
4. Create a separate JSON file for each main section in the `merck/subsections/` directory

#### Test Mode

To test the subsection crawler on just one section (Circulatory System):

```bash
python selenium_solution.py --test
```

This will only process the Circulatory System section, allowing you to verify the crawler works properly before running it on all sections.

## Output Structure

### Main Sections (merck_sections.json)

The initial crawler saves main sections to `merck_sections.json`:

```json
[
  {
    "title": "Circulatory System",
    "url": "https://www.merckvetmanual.com/circulatory-system"
  },
  {
    "title": "Behavior",
    "url": "https://www.merckvetmanual.com/behavior"
  },
  ...
]
```

### Subsections (e.g., Circulatory_System.json)

Each subsection file contains the subsections for a specific main section:

```json
[
  {
    "title": "Hematopoietic System Introduction",
    "url": "https://www.merckvetmanual.com/circulatory-system/hematopoietic-system-introduction"
  },
  {
    "title": "Anemia",
    "url": "https://www.merckvetmanual.com/circulatory-system/anemia"
  },
  {
    "title": "Blood Groups and Blood Transfusions in Dogs and Cats",
    "url": "https://www.merckvetmanual.com/circulatory-system/blood-groups-and-blood-transfusions-in-dogs-and-cats"
  },
  ...
]
```

## Troubleshooting

If you encounter issues with the crawler:

1. **No items scraped**: The website structure might have changed. Try using the debug tool to identify the correct CSS selectors.

2. **Rate limiting**: You might be hitting the site too fast. Increase the `DOWNLOAD_DELAY` in settings.py.

3. **Blocked by the site**: Ensure you're respecting `robots.txt` and using an appropriate user agent.

## Ethical Considerations

This scraper is designed for educational and research purposes only. Please be respectful of the website's resources by:

- Keeping the crawl rate slow (default settings are already conservative)
- Respecting the robots.txt
- Not overloading their servers with too many requests
