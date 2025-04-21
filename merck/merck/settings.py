# Scrapy settings for merck project

BOT_NAME = "merck"
from shutil import which

SELENIUM_DRIVER_NAME = "chrome"
SELENIUM_DRIVER_EXECUTABLE_PATH = which("chromedriver")
SELENIUM_DRIVER_ARGUMENTS = ["--headless"]

# Add the Selenium middleware
DOWNLOADER_MIDDLEWARES = {"scrapy_selenium.SeleniumMiddleware": 800}

SPIDER_MODULES = ["merck.spiders"]
NEWSPIDER_MODULE = "merck.spiders"

# Use a realistic User-Agent to avoid getting blocked
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Obey robots.txt rules (optional - set False to ignore scraping restrictions)
ROBOTSTXT_OBEY = True

# Set a download delay to avoid hitting the server too hard
DOWNLOAD_DELAY = 2

# Disable cookies (some sites track sessions)
COOKIES_ENABLED = False

# Override the default request headers
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

# Enable AutoThrottle to dynamically manage request rates
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Retry on failures (e.g., 503 errors)
RETRY_ENABLED = True
RETRY_TIMES = 3  # Number of retries
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408]

# Optional: use rotating proxies or user-agents via middleware later

# Set future-proof default values
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
