import re
import scrapy
from .base_spider import BaseMarketSpider


class MicromagmaSpider(BaseMarketSpider):
    name = "micromagma"

    categories_urls = {
        'laptop':   'https://micromagma.ma/laptops',
        'moniteur': 'https://micromagma.ma/informatique/moniteurs',
    }

    product_selector = 'a[href*="/item/"]'
    name_selector    = None
    price_selector   = None

    _HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'fr-MA,fr;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://micromagma.ma/',
    }

    custom_settings = {
        **BaseMarketSpider.custom_settings,
        'RETRY_HTTP_CODES':                 [500, 502, 503, 504, 408, 429],
        'CONCURRENT_REQUESTS':              2,
        'CONCURRENT_REQUESTS_PER_DOMAIN':   1,
        'DOWNLOAD_DELAY':                   2.0,
        'AUTOTHROTTLE_ENABLED':             True,
        'AUTOTHROTTLE_START_DELAY':         1,
        'AUTOTHROTTLE_MAX_DELAY':           10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY':  1.0,
        'ROBOTSTXT_OBEY':                   True,
        'HTTPERROR_ALLOW_ALL':              True,
    }

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _page_url(self, base_url: str, page: int) -> str:
        if page <= 1:
            return base_url
        return f"{base_url}?page={page}"

    # ------------------------------------------------------------------ #
    #  Entry point                                                         #
    # ------------------------------------------------------------------ #

    async def start(self):
        for cat, url in self.categories_urls.items():
            yield scrapy.Request(
                url,
                callback=self.parse,
                errback=self.handle_error,
                headers=self._HEADERS,
                cb_kwargs={'category': cat, 'page': 1, 'base_url': url},
            )

    # ------------------------------------------------------------------ #
    #  Page parsing & pagination                                           #
    # ------------------------------------------------------------------ #

    async def parse(self, response, category, page, base_url):
        self.logger.info(
            f"[micromagma] [{category}] HTTP {response.status} page {page} → {response.url}"
        )

        if response.status == 403:
            self.logger.error(f"403 Forbidden: {response.url} (category: {category})")
            yield self._error_item(response.url, category, "HTTP 403 Forbidden")
            return

        products = [
            a for a in response.css(self.product_selector)
            if '/item/' in (a.attrib.get('href') or '')
        ]

        if not products:
            self.logger.warning(
                f"[micromagma] [{category}] No products found on page {page}"
            )
        else:
            self.logger.info(
                f"[micromagma] [{category}] {len(products)} products on page {page}"
            )

        for product in products:
            item = self.parse_product(product, category)
            if item:
                if item.get('url') and not item['url'].startswith('http'):
                    item['url'] = response.urljoin(item['url'])
                yield item

        # Pagination — keep fetching next pages as long as products are found.
        # Simpler and more robust than parsing a total count from the HTML,
        # since the count format may vary or change without notice.
        if products:
            next_page = page + 1
            yield scrapy.Request(
                self._page_url(base_url, next_page),
                callback=self.parse,
                errback=self.handle_error,
                headers={**self._HEADERS, 'Referer': response.url},
                cb_kwargs={
                    'category': category,
                    'page':     next_page,
                    'base_url': base_url,
                },
            )

    # ------------------------------------------------------------------ #
    #  Product parsing                                                     #
    # ------------------------------------------------------------------ #

    def parse_product(self, product, category):
        url = product.attrib.get('href', '')

        # Name: text nodes that aren't prices, percentages, or too short
        texts = [
            t.strip() for t in product.css('::text').getall()
            if t.strip()
            and 'DHs' not in t and 'dhs' not in t
            and not re.match(r'^[\d\s%\-]+$', t.strip())
            and len(t.strip()) > 4
        ]
        name = self._clean_name(texts[0]) if texts else None
        if not name:
            return None

        # Price: first text node matching NNN DHs pattern
        price = 0.0
        for text in product.css('::text').getall():
            text = text.strip()
            if 'DHs' in text or 'dhs' in text:
                price = self._parse_price(text)
                break

        # Brand: infer from name
        brand = 'Inconnue'
        for b in ['Apple', 'HP', 'Dell', 'Asus', 'Lenovo', 'Samsung',
                  'Microsoft', 'Huawei', 'Acer', 'MSI', 'LG', 'Philips',
                  'AOC', 'Alienware', 'Corsair', 'Xiaomi']:
            if b.lower() in name.lower():
                brand = b
                break

        return {
            'id':         self._make_unique_id('micromagma', category, name),
            'site':       'micromagma',
            'category':   category,
            'name':       name,
            'price':      price,
            'in_stock':   None,
            'brand':      brand,
            'url':        url,
            'scraped_at': self._now_utc(),
            'error':      None,
        }
