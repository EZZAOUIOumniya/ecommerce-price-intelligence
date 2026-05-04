from typing import Optional
import re
import scrapy
from collections import Counter
from .base_spider import BaseMarketSpider


class UnoSpider(BaseMarketSpider):
    name = "uno"
    base_url = "https://uno.ma"

    categories_queries = {
        'laptop':   ['macbook', 'imac', 'mac mini', 'mac studio', 'mac pro'],
        'moniteur': ['studio display', 'pro display'],
    }

    custom_settings = {
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_DELAY': 2.0,
        'AUTOTHROTTLE_ENABLED': False,
        'ROBOTSTXT_OBEY': False,
        'LOG_LEVEL': 'INFO',
    }

    SEARCH_URL = 'https://uno.ma/catalogsearch/result/'

    _HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Referer': 'https://uno.ma/',
        'Accept-Language': 'fr-MA,fr;q=0.9',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dedup by (site, name) regardless of which query surfaced the product.
        # Category is intentionally excluded: the same physical product can appear
        # under multiple queries within the same category (e.g. "MacBook Pro" in
        # both the 'macbook' and 'mac pro' result sets). Using name alone avoids
        # double-counting while still preserving products that genuinely differ.
        self._seen_names: set[str] = set()

    # ------------------------------------------------------------------ #
    #  URL helpers                                                         #
    # ------------------------------------------------------------------ #

    def _search_url(self, query: str, page: int = 1) -> str:
        url = f"{self.SEARCH_URL}?q={query.replace(' ', '+')}&limit=48"
        if page > 1:
            url += f"&p={page}"
        return url

    # ------------------------------------------------------------------ #
    #  Entry point                                                         #
    # ------------------------------------------------------------------ #

    async def start(self):
        for category, queries in self.categories_queries.items():
            for query in queries:
                yield scrapy.Request(
                    self._search_url(query),
                    callback=self.parse_listing,
                    errback=self.handle_error,
                    headers=self._HEADERS,
                    cb_kwargs={'category': category, 'query': query, 'page': 1},
                )

    # ------------------------------------------------------------------ #
    #  Listing page                                                        #
    # ------------------------------------------------------------------ #

    def parse_listing(self, response, category, query, page):
        products = (
            response.css('li.item.product.product-item')
            or response.css('li.product-item')
            or response.css('.item.product')
        )

        if not products:
            self.logger.warning(
                f"[uno] [{category}] q={query!r} page={page} — no products found "
                f"(status={response.status})"
            )
            # Debug: log class names that contain product/item/price to help
            # identify the correct CSS selector for this site layout.
            classes = re.findall(
                r'class="([^"]*(?:product|item|price)[^"]*)"', response.text
            )
            for cls, cnt in Counter(classes).most_common(8):
                self.logger.info(f"  [css-hint] {cnt}x  {cls[:80]}")
            return

        new_items = 0
        for product in products:
            item = self.parse_product(product, category)
            if not item:
                continue
            dedup_key = item['name'].lower().strip()
            if dedup_key in self._seen_names:
                continue
            self._seen_names.add(dedup_key)
            new_items += 1
            yield item

        # ── Pagination ──────────────────────────────────────────────────
        total_pages = self._parse_total_pages(response.text)

        self.logger.info(
            f"[uno] [{category}] q={query!r} page {page}/{total_pages or '?'}: "
            f"{len(products)} produits, {new_items} nouveaux"
        )

        # Primary path: we know the total page count — request next page directly.
        if total_pages and page < total_pages:
            yield scrapy.Request(
                self._search_url(query, page + 1),
                callback=self.parse_listing,
                errback=self.handle_error,
                headers={**self._HEADERS, 'Referer': self._search_url(query, page)},
                cb_kwargs={'category': category, 'query': query, 'page': page + 1},
            )
            return

        # Fallback: total page count unknown — follow rel="next" link if present.
        # This handles Magento configs that render paginator links but not a count.
        # NOTE: Magento also emits <link rel="next"> SEO canonical tags that point
        # to unrelated product pages — we guard against those by requiring the URL
        # to be a search results page with a ?p=N parameter.
        if total_pages is None:
            next_href = (
                response.css('a[rel="next"]::attr(href)').get()
                or response.css('a.next::attr(href)').get()
                or response.css('li.next a::attr(href)').get()
            )
            if next_href:
                next_url = response.urljoin(next_href)
                is_search_page = (
                    'catalogsearch/result' in next_url
                    and bool(re.search(r'[?&]p=\d+', next_url))
                )
                if is_search_page:
                    self.logger.info(
                        f"[uno] [{category}] q={query!r} — total pages unknown, "
                        f"following rel=next → {next_url}"
                    )
                    yield scrapy.Request(
                        next_url,
                        callback=self.parse_listing,
                        errback=self.handle_error,
                        headers={**self._HEADERS, 'Referer': response.url},
                        cb_kwargs={'category': category, 'query': query, 'page': page + 1},
                    )
                else:
                    self.logger.debug(
                        f"[uno] [{category}] q={query!r} — rel=next rejected "
                        f"(not a search results page): {next_url}"
                    )

    # ------------------------------------------------------------------ #
    #  Pagination detection                                                #
    # ------------------------------------------------------------------ #

    def _parse_total_pages(self, html: str) -> Optional[int]:
        # Pattern A: Magento toolbar "1-12 of 47" / "1-12 sur 47"
        m = re.search(r'(\d+)\s*[-–]\s*(\d+)\s+(?:of|sur)\s+(\d+)', html)
        if m:
            per_page = int(m.group(2)) - int(m.group(1)) + 1
            total = int(m.group(3))
            if per_page > 0:
                return (total + per_page - 1) // per_page

        # Pattern B: Magento 2 JSON config blob {"pages_count": 4}
        m = re.search(r'"pages_count"\s*:\s*(\d+)', html)
        if m:
            return int(m.group(1))

        # Pattern C: highest ?p=N or &p=N value in paginator anchor hrefs
        nums = re.findall(r'[?&]p=(\d+)', html)
        if nums:
            return max(int(n) for n in nums)

        # Pattern D: explicit numbered page links inside paginator
        nums = re.findall(
            r'class="page[^"]*"[^>]*>\s*<span[^>]*>\s*(\d+)\s*</span>', html
        )
        if nums:
            return max(int(n) for n in nums if int(n) > 0)

        return None

    # ------------------------------------------------------------------ #
    #  Product parsing                                                     #
    # ------------------------------------------------------------------ #

    def parse_product(self, product, category):
        name = (
            product.css('.product-item-name a::text').get()
            or product.css('.product-item-link::text').get()
            or product.css('a.product-item-link::text').get()
            or ''
        ).strip()

        if not name:
            return None

        name = self._clean_name(name)

        price_text = (
            product.css('.price-box .price::text').get()
            or product.css('span.price::text').get()
            or product.css('.special-price .price::text').get()
            or product.css('.regular-price .price::text').get()
            or ''
        )
        price = self._parse_price(price_text) if price_text else 0.0

        url = (
            product.css('.product-item-name a::attr(href)').get()
            or product.css('a.product-item-link::attr(href)').get()
            or ''
        )

        # Explicit unavailability markers take priority; default to True only
        # when neither available nor unavailable marker is present, to avoid
        # false positives on unlisted products.
        if product.css('.out-of-stock, .unavailable'):
            in_stock = False
        elif product.css('.stock.available'):
            in_stock = True
        else:
            in_stock = None  # unknown — let downstream decide

        return {
            'id':         self._make_unique_id('uno', category, name),
            'site':       'uno',
            'category':   category,
            'name':       name,
            'price':      price,
            'in_stock':   in_stock,
            'brand':      'Apple',
            'url':        url,
            'scraped_at': self._now_utc(),
            'error':      None,
        }
