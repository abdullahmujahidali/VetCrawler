BOT_NAME = "merck_scraper"

SPIDER_MODULES = ["merck_scraper.spiders"]
NEWSPIDER_MODULE = "merck_scraper.spiders"

# Obey robots.txt rules - important for ethical scraping
ROBOTSTXT_OBEY = True

# Configure a reasonable delay to avoid overloading the server (in seconds)
DOWNLOAD_DELAY = 2

# Set concurrent requests to a polite level
CONCURRENT_REQUESTS = 8

# Configure item pipelines
ITEM_PIPELINES = {
    "merck_scraper.pipelines.MerckScraperPipeline": 300,
}

# Enable logging
LOG_LEVEL = "INFO"

# Set default encoding for exports
FEED_EXPORT_ENCODING = "utf-8"

# Configure User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Enable cache for faster development (optional)
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
