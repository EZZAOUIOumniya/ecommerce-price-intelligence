import os

BOT_NAME = "market_bot"
SPIDER_MODULES = ["market_bot.spiders"]
NEWSPIDER_MODULE = "market_bot.spiders"

# --- KAFKA ---
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'market_data')
KAFKA_PRODUCER_CONFIG = {
    'queue.buffering.max.messages': 100000,
    'queue.buffering.max.ms':       100,
    'socket.timeout.ms':            10000,
    'message.timeout.ms':           30000,
}

# --- LIMITS ---
CLOSESPIDER_ITEMCOUNT = 50000
CLOSESPIDER_PAGECOUNT = 5000

# --- PERFORMANCE ---
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_TIMEOUT = 90
AUTOTHROTTLE_ENABLED = False  # incompatible with Playwright timing

# --- RETRIES ---
RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# --- PIPELINES ---
ITEM_PIPELINES = {
    'market_bot.pipelines.KafkaPipeline': 300,
}

# --- ANTI-BAN ---
ROBOTSTXT_OBEY = False
COOKIES_ENABLED = True
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

# --- PLAYWRIGHT ---
DOWNLOAD_HANDLERS = {
    "http":  "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 90000
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 4
PLAYWRIGHT_CLOSE_BROWSER_ON_DISCONNECT = True

PLAYWRIGHT_CONTEXTS = {
    "default": {
        "user_agent": USER_AGENT,
        "viewport": {"width": 1366, "height": 768},
        "ignore_https_errors": True,
        "java_script_enabled": True,
        "locale": "fr-MA",
    }
}

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ],
}

# --- TECHNICAL ---
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = 'INFO'
