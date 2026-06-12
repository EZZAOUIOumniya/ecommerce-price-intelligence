from typing import Optional
import urllib.parse
import scrapy
from .base_spider import BaseMarketSpider


class ElectroplanetSpider(BaseMarketSpider):
    name = "electroplanet"

    # Doofinder search API — no Playwright needed, pure JSON
    _HASH_ID  = "c33f31f658775a14c970fef6d935bd25"
    _API_BASE = "https://eu1-search.doofinder.com/5/search"
    _RPP      = 100  # results per page (max)

    _HEADERS = {
        'Origin':  'https://www.electroplanet.ma',
        'Referer': 'https://www.electroplanet.ma/',
    }

    # Brands to query — Doofinder returns all products matching brand name
    brands = [
        'apple', 'samsung', 'hp', 'lenovo', 'asus',
        'dell', 'xiaomi', 'oppo', 'acer', 'msi',
    ]

    # URL slug keywords → category (checked first)
    _URL_CATEGORY_MAP = [
        (['ordinateur-portable', 'macbook', 'pc-portable'], 'laptop'),
        (['smartphone', 'iphone'],                          'smartphone'),
        (['tablette', 'ipad'],                              'tablet'),
        (['imprimante'],                                     'imprimante'),
        (['ecran', 'moniteur'],                             'moniteur'),
        (['watch'],                                         'smartwatch'),
    ]

    # Product name keywords → category (fallback for generic /pNNNNNNN slugs)
    _NAME_CATEGORY_MAP = [
        (['macbook', 'pc portable', 'laptop', 'notebook',
          'vivobook', 'zenbook', 'ideapad', 'thinkpad',
          'inspiron', 'pavilion', 'elitebook', 'nitro',
          'thin ', 'cyborg', 'modern ', 'prestige'],        'laptop'),
        (['iphone', 'galaxy s', 'galaxy a', 'galaxy m',
          'reno', 'find x', 'smart a', 'redmi', 'poco',
          'smartphone'],                                     'smartphone'),
        (['ipad', 'tab s', 'tab a', 'tablette'],            'tablet'),
        (['apple watch', 'galaxy watch', 'watch ultra',
          'watch se', 'watch serie'],                        'smartwatch'),
        (['imprimante', 'printer'],                          'imprimante'),
        (['ecran', 'moniteur', 'monitor', 'display'],       'moniteur'),
    ]

    custom_settings = {
        **BaseMarketSpider.custom_settings,
        'CONCURRENT_REQUESTS':              4,   # API can handle more concurrency
        'CONCURRENT_REQUESTS_PER_DOMAIN':   4,
        'DOWNLOAD_DELAY':                   0.5,
        'AUTOTHROTTLE_ENABLED':             True,
        'ROBOTSTXT_OBEY':                   False,  # API endpoint, no robots.txt
        'HTTPERROR_ALLOW_ALL':              True,
    }

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _api_url(self, brand: str, page: int) -> str:
        params = {
            'hashid': self._HASH_ID,
            'query':  brand,
            'page':   page,
            'rpp':    self._RPP,
        }
        return f"{self._API_BASE}?{urllib.parse.urlencode(params)}"

    def _classify(self, link: str, name: str = '') -> Optional[str]:
        link_lower = link.lower()
        # Try URL slug first — most reliable signal
        for keywords, category in self._URL_CATEGORY_MAP:
            if any(kw in link_lower for kw in keywords):
                return category
        # Fallback: classify by product name (handles generic /pNNNNNN slugs)
        name_lower = name.lower()
        for keywords, category in self._NAME_CATEGORY_MAP:
            if any(kw in name_lower for kw in keywords):
                return category
        return None

    def _infer_brand(self, name: str, query_brand: str) -> str:
        known = [
            'Apple', 'Samsung', 'HP', 'Lenovo', 'Asus', 'Dell',
            'Xiaomi', 'Oppo', 'Acer', 'MSI', 'Huawei', 'LG',
        ]
        name_lower = name.lower()
        for b in known:
            if b.lower() in name_lower:
                return b
        return query_brand.capitalize()

    # ------------------------------------------------------------------ #
    #  Entry point                                                         #
    # ------------------------------------------------------------------ #

    async def start(self):
        for brand in self.brands:
            yield scrapy.Request(
                self._api_url(brand, 1),
                callback=self.parse_api,
                errback=self.handle_error,
                headers=self._HEADERS,
                cb_kwargs={'brand': brand, 'page': 1},
            )

    # ------------------------------------------------------------------ #
    #  Parsing                                                             #
    # ------------------------------------------------------------------ #

    def parse_api(self, response, brand, page):
        if response.status != 200:
            self.logger.error(
                f"[electroplanet] HTTP {response.status} brand={brand} page={page}"
            )
            yield self._error_item(response.url, brand, f"HTTP {response.status}")
            return

        try:
            data = response.json()
        except Exception as e:
            self.logger.error(f"[electroplanet] JSON parse error brand={brand} page={page}: {e}")
            yield self._error_item(response.url, brand, str(e))
            return

        results = data.get('results', [])
        total_pages = data.get('total_pages', 1)

        self.logger.info(
            f"[electroplanet] brand={brand} page={page}/{total_pages} "
            f"— {len(results)} results"
        )

        seen_ids = set()
        for item in results:
            product = self._build_item(item, brand)
            if product and product['id'] not in seen_ids:
                seen_ids.add(product['id'])
                yield product

        # Pagination
        if page < total_pages:
            yield scrapy.Request(
                self._api_url(brand, page + 1),
                callback=self.parse_api,
                errback=self.handle_error,
                headers=self._HEADERS,
                cb_kwargs={'brand': brand, 'page': page + 1},
            )

    def _build_item(self, item: dict, query_brand: str) -> Optional[dict]:
        link     = item.get('link', '')
        name_raw = (item.get('title') or '').strip()
        category = self._classify(link, name_raw)
        if not category:
            return None

        name = name_raw
        if not name:
            return None

        # Doofinder returns price as float or int — normalize to int (MAD)
        try:
            price = int(float(item.get('price', 0)))
        except (TypeError, ValueError):
            price = 0

        item_id = str(item.get('id', '')) or self._make_unique_id(
            'electroplanet', category, name
        )

        return {
            'id':         item_id,
            'site':       'electroplanet',
            'category':   category,
            'name':       name,
            'price':      price,
            'in_stock':   None,   # Doofinder API doesn't expose stock status
            'brand':      self._infer_brand(name, query_brand),
            'url':        link,
            'scraped_at': self._now_utc(),
            'error':      None,
        }
