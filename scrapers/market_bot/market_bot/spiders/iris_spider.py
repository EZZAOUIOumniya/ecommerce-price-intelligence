from typing import Optional
import re
import scrapy
from scrapy import Selector
from scrapy_playwright.page import PageMethod
from .base_spider import BaseMarketSpider


class IrisSpider(BaseMarketSpider):
    name = "iris"
    base_url = "https://www.iris.ma"

    categories_urls = {
        'moniteur': 'https://www.iris.ma/55-ecran-moniteur',
        'laptop':   'https://www.iris.ma/44-ordinateur-portable',
    }

    KNOWN_BRANDS = [
        'HP', 'Dell', 'Lenovo', 'Asus', 'Acer', 'Apple', 'MSI',
        'Samsung', 'LG', 'Huawei', 'Toshiba', 'Gigabyte', 'Razer',
        'Microsoft', 'Sony', 'BenQ', 'ViewSonic', 'Philips',
        'AOC', 'Iiyama', 'Eizo', 'NEC', 'Alienware', 'Xiaomi',
        'Wacom', 'Dahua', 'Hikvision',
    ]

    LAPTOP_CATEGORY_BLOCKLIST = [
        'imprimante', 'projecteur', 'vidéoprojecteur', 'onduleur',
        'tablette graphique', 'kaspersky', 'microsoft 365', 'office 365',
        'ecotank', 'epson co-', 'epson eh-',
    ]

    custom_settings = {
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 120000,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_DELAY': 3.0,
        'AUTOTHROTTLE_ENABLED': False,
        'ROBOTSTXT_OBEY': False,
        'LOG_LEVEL': 'INFO',
        'PLAYWRIGHT_CONTEXTS': {
            'default': {
                'user_agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                'viewport': {'width': 1366, 'height': 768},
                'locale': 'fr-MA',
                'timezone_id': 'Africa/Casablanca',
            }
        },
        'PLAYWRIGHT_MAX_CONTEXTS': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen_ids: dict[str, set] = {
            cat: set() for cat in self.categories_urls
        }

    def _iris_meta(self, referer: str = 'https://www.iris.ma/'):
        return {
            "playwright": True,
            "playwright_include_page": True,
            "playwright_context": "default",
            "playwright_page_methods": [
                PageMethod("set_extra_http_headers", {"Referer": referer}),
                PageMethod(
                    "wait_for_selector",
                    "#js-product-list .js-product-miniature",
                    state="attached",
                    timeout=45000,
                ),
                PageMethod("evaluate", "window.scrollBy(0, 2000)"),
                PageMethod("wait_for_timeout", 2000),
            ],
        }

    def _clean_url(self, base_url: str, page: int) -> str:
        if page == 1:
            return base_url
        return f"{base_url}?page={page}"

    def _parse_pagination(self, html: str) -> Optional[int]:
        page_nums = re.findall(r'js-search-link[^>]*>\s*(\d+)\s*<', html)
        if page_nums:
            return max(int(n) for n in page_nums)
        m = re.search(r'(\d+)-(\d+)\s+sur\s+(\d+)', html)
        if m:
            per_page = int(m.group(2)) - int(m.group(1)) + 1
            total = int(m.group(3))
            if per_page > 0:
                return (total + per_page - 1) // per_page
        return None

    async def start(self):
        yield scrapy.Request(
            'https://www.iris.ma/',
            callback=self.after_warmup,
            errback=self.handle_error,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context": "default",
                "playwright_page_methods": [
                    PageMethod("wait_for_timeout", 3000),
                ],
            },
        )

    async def after_warmup(self, response):
        pw_page = response.meta.get("playwright_page")
        if pw_page:
            await pw_page.close()
        self.logger.info("[iris] Homepage warmed up — starting category crawl")

        for category, url in self.categories_urls.items():
            yield scrapy.Request(
                url,
                callback=self.parse_listing,
                errback=self.handle_error,
                meta=self._iris_meta(referer='https://www.iris.ma/'),
                cb_kwargs={'category': category, 'page': 1, 'base_url': url},
            )

    async def parse_listing(self, response, category, page, base_url):
        pw_page = response.meta.get("playwright_page")
        if pw_page:
            live_html = await pw_page.content()
            title = await pw_page.title()
            await pw_page.close()
        else:
            live_html = response.text
            title = ''

        if 'just a moment' in title.lower() or 'just a moment' in live_html[:500].lower():
            self.logger.warning(
                f"[iris] [{category}] page {page} — Cloudflare block, retrying..."
            )
            yield scrapy.Request(
                response.url,
                callback=self.parse_listing,
                errback=self.handle_error,
                meta=self._iris_meta(referer=self._clean_url(base_url, max(1, page - 1))),
                cb_kwargs={'category': category, 'page': page, 'base_url': base_url},
                dont_filter=True,
            )
            return

        sel = Selector(text=live_html)
        product_list = sel.css('#js-product-list')

        if not product_list:
            self.logger.warning(
                f"[iris] [{category}] page {page} — #js-product-list missing"
            )
            return

        raw_products = product_list.css('.js-product-miniature')
        seen_on_page: set = set()
        unique_products = []
        for p in raw_products:
            pid = p.attrib.get('data-id-product', '')
            if pid and pid not in seen_on_page:
                seen_on_page.add(pid)
                unique_products.append(p)

        total_pages = self._parse_pagination(live_html)
        seen = self._seen_ids[category]
        new_items = 0

        for product in unique_products:
            item = self.parse_product(product, category)
            if not item:
                continue
            if item['id'] in seen:
                continue
            seen.add(item['id'])
            new_items += 1
            yield item

        self.logger.info(
            f"[iris] [{category}] page {page}/{total_pages or '?'}: "
            f"{len(raw_products)} bruts, {len(unique_products)} uniques, "
            f"{new_items} nouveaux"
        )

        if total_pages and page < total_pages:
            yield scrapy.Request(
                self._clean_url(base_url, page + 1),
                callback=self.parse_listing,
                errback=self.handle_error,
                meta=self._iris_meta(referer=response.url),
                cb_kwargs={'category': category, 'page': page + 1, 'base_url': base_url},
            )
        else:
            self.logger.info(f"[iris] [{category}] fin de pagination à la page {page}")

    def _is_off_category(self, name: str, category: str) -> bool:
        if category != 'laptop':
            return False
        return any(kw in name.lower() for kw in self.LAPTOP_CATEGORY_BLOCKLIST)

    def parse_product(self, product, category):
        name = (
            product.css('h2.product-title a::text').get()
            or product.css('h3.product-title a::text').get()
            or product.css('.product-title a::text').get()
            or product.css('.product-title::text').get()
            or ''
        ).strip()

        if not name:
            return None

        name = self._clean_name(name)

        if self._is_off_category(name, category):
            return None

        price = 0.0
        price_content = product.css('[itemprop="price"]::attr(content)').get()
        if price_content:
            try:
                price = float(price_content)
            except ValueError:
                pass
        if price == 0.0:
            price_text = (
                product.css('span.price::text').get()
                or product.css('.price::text').get()
                or ''
            )
            price = self._parse_price(price_text)

        url = (
            product.css('a.product-thumbnail::attr(href)').get()
            or product.css('h2.product-title a::attr(href)').get()
            or product.css('h3.product-title a::attr(href)').get()
            or product.css('.product-title a::attr(href)').get()
            or ''
        )

        in_stock = bool(product.css('.product-availability.available'))

        brand = 'Inconnue'
        for b in self.KNOWN_BRANDS:
            if b.upper() in name.upper():
                brand = b
                break

        return {
            'id':         self._make_unique_id('iris', category, name),
            'site':       'iris',
            'category':   category,
            'name':       name,
            'price':      price,
            'in_stock':   in_stock,
            'brand':      brand,
            'url':        url,
            'scraped_at': self._now_utc(),
            'error':      None,
        }
