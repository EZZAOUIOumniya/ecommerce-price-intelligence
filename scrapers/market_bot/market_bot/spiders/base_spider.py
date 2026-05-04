import scrapy
import re
import hashlib
from abc import ABC
from datetime import datetime, timezone
from scrapy_playwright.page import PageMethod


class BaseMarketSpider(scrapy.Spider, ABC):
    """Modèle de base pour tous les scrapers de la plateforme."""

    product_selector = None
    name_selector    = None
    price_selector   = None
    categories_urls  = {}

    custom_settings = {
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 120000,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_DELAY': 2.0,
        'AUTOTHROTTLE_ENABLED': False,  # incompatible with Playwright timing
        'ROBOTSTXT_OBEY': True,
        'HTTPERROR_ALLOWED_CODES': [403],
    }

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _playwright_meta(self, include_page: bool = False) -> dict:
        return {
            "playwright": True,
            "playwright_include_page": include_page,
            "playwright_page_methods": [
                PageMethod("wait_for_load_state", "networkidle", timeout=90000),
                PageMethod("evaluate", "window.scrollBy(0, 2000)"),
                PageMethod("wait_for_timeout", 3000),
            ],
        }

    def _now_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_now_str(self) -> str:
        return self._now_utc()

    def _parse_price(self, price_raw: str) -> float:
        if not price_raw:
            return 0.0

        # Supprimer tout sauf chiffres, virgule, point
        digits = re.sub(r'[^\d,.]', '', price_raw.strip())
        if not digits:
            return 0.0

        # Supprimer les points/virgules parasites en fin de chaîne
        # ex: "864,00." → "864,00"
        digits = digits.rstrip('.,')
        if not digits:
            return 0.0

        if ',' in digits and '.' in digits:
            if digits.rindex(',') > digits.rindex('.'):
                # Format européen : 1.234,56 → 1234.56
                digits = digits.replace('.', '').replace(',', '.')
            else:
                # Format anglais : 1,234.56 → 1234.56
                digits = digits.replace(',', '')

        elif ',' in digits:
            parts = digits.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Format décimal : 864,00 → 864.00
                digits = digits.replace(',', '.')
            else:
                # Séparateur de milliers : 1,234 → 1234
                digits = digits.replace(',', '')

        try:
            return float(digits)
        except ValueError:
            self.logger.warning(f"Price parse failed: '{price_raw}' → '{digits}'")
            return 0.0

    def _make_unique_id(self, site: str, category: str, name: str) -> str:
        slug = re.sub(r'[^a-z0-9]', '_', name.lower()[:30]).strip('_')
        name_hash = hashlib.md5(name.encode('utf-8')).hexdigest()[:6]
        return f"{site}_{category}_{slug}_{name_hash}"

    def _clean_name(self, raw: str) -> str:
        return re.sub(r'[\u00a0\u200b\u2009\u202f]+', ' ', raw).strip()

    def _error_item(self, url: str, category: str, reason: str) -> dict:
        return {
            'id':         f"error_{hashlib.md5(url.encode()).hexdigest()[:10]}",
            'site':       self.name,
            'category':   category,
            'name':       None,
            'price':      None,
            'in_stock':   None,
            'brand':      None,
            'url':        url,
            'scraped_at': self._now_utc(),
            'error':      reason,
        }

    # ------------------------------------------------------------------ #
    #  Requests                                                            #
    # ------------------------------------------------------------------ #

    async def start(self):
        for cat, url in self.categories_urls.items():
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta=self._playwright_meta(include_page=True),
                cb_kwargs={'category': cat},
                errback=self.handle_error,
            )

    # ------------------------------------------------------------------ #
    #  Parsing                                                             #
    # ------------------------------------------------------------------ #

    async def parse(self, response, category):
        page = response.meta.get("playwright_page")
        if page:
            await page.close()

        if response.url != response.request.url:
            self.logger.warning(
                f"Redirect: {response.request.url} → {response.url} "
                f"(category: {category})"
            )

        if response.status == 403:
            self.logger.error(f"403 Forbidden: {response.url} (category: {category})")
            yield self._error_item(response.url, category, "HTTP 403 Forbidden")
            return

        products = response.css(self.product_selector)
        if not products:
            self.logger.warning(
                f"⚠️ Aucun produit trouvé sur {response.url} (category: {category})"
            )
        else:
            self.logger.info(
                f"[{self.name}] [{category}]: {len(products)} produits sur {response.url}"
            )

        for product in products:
            item = self.parse_product(product, category)
            if item:
                if item.get('url') and not item['url'].startswith('http'):
                    item['url'] = response.urljoin(item['url'])
                yield item

        next_page = (
            response.css('a[rel="next"]::attr(href)').get()
            or response.css('a.next::attr(href)').get()
            or response.css('li.next a::attr(href)').get()
        )
        if next_page:
            yield scrapy.Request(
                response.urljoin(next_page),
                callback=self.parse,
                meta=self._playwright_meta(include_page=False),
                cb_kwargs={'category': category},
                errback=self.handle_error,
            )

    # ------------------------------------------------------------------ #
    #  Base parse_product                                                  #
    # ------------------------------------------------------------------ #

    def parse_product(self, product, category):
        name_raw = product.css(self.name_selector).get() if self.name_selector else None
        if not name_raw:
            return None
        name = self._clean_name(name_raw)

        price_raw = (
            product.css(self.price_selector).xpath('string()').get()
            if self.price_selector else None
        )
        price = self._parse_price(price_raw)
        url = product.css('a::attr(href)').get() or ''

        return {
            'id':         self._make_unique_id(self.name, category, name),
            'site':       self.name,
            'category':   category,
            'name':       name,
            'price':      price,
            'in_stock':   None,
            'brand':      None,
            'url':        url,
            'scraped_at': self._now_utc(),
            'error':      None,
        }

    # ------------------------------------------------------------------ #
    #  Error handling                                                      #
    # ------------------------------------------------------------------ #

    def handle_error(self, failure):
        url      = failure.request.url
        category = failure.request.cb_kwargs.get('category', 'unknown')
        reason   = repr(failure)
        self.logger.error(f"❌ Network error [{category}] {url}: {reason}")
        yield self._error_item(url, category, reason)
