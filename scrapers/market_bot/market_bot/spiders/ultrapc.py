import re
import scrapy
from .base_spider import BaseMarketSpider


class UltraPcSpider(BaseMarketSpider):
    name = "ultrapc"
    base_url = "https://www.ultrapc.ma"

    categories_urls = {
        'moniteur': 'https://www.ultrapc.ma/62-moniteurs',
        'laptop':   'https://www.ultrapc.ma/19-pc-portables',
    }

    KNOWN_BRANDS = [
        'HP', 'Dell', 'Lenovo', 'Asus', 'Acer', 'Apple', 'MSI',
        'Samsung', 'LG', 'Huawei', 'Toshiba', 'Gigabyte', 'Razer',
        'Microsoft', 'Sony', 'BenQ', 'ViewSonic', 'Philips', 'Aiwa',
        'AOC', 'Iiyama', 'Eizo', 'NEC', 'Alienware', 'Xiaomi',
        'Redragon', 'Corsair', 'HKC', 'Koorui', 'Dahua',
    ]

    custom_settings = {
        'DOWNLOAD_HANDLERS': {},
        'PLAYWRIGHT_BROWSER_TYPE': None,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'DOWNLOAD_DELAY': 1.0,
    }

    async def start(self):
        for category, url in self.categories_urls.items():
            yield scrapy.Request(
                url,
                callback=self.parse_listing,
                errback=self.handle_error,
                cb_kwargs={'category': category, 'page': 1},
            )

    def parse_listing(self, response, category, page):
        products = response.css('article.product-miniature')

        if not products:
            self.logger.warning(
                f"[ultrapc] No products on {response.url} (page {page})"
            )
            return

        self.logger.info(
            f"[ultrapc] [{category}] page {page}: {len(products)} produits"
        )

        for product in products:
            item = self.parse_product(product, category)
            if item:
                yield item

        # Pagination — PrestaShop uses ?p=N
        next_page = response.css('a[rel="next"]::attr(href)').get()
        if next_page:
            yield scrapy.Request(
                next_page,
                callback=self.parse_listing,
                errback=self.handle_error,
                cb_kwargs={'category': category, 'page': page + 1},
            )

    def parse_product(self, product, category):
        # Name
        name = (product.css('h3.product-title a::text').get() or '').strip()
        if not name:
            return None
        name = self._clean_name(name)

        # Price — content attribute has clean number e.g. content="1349"
        price_content = product.css('span.price::attr(content)').get() or '0'
        try:
            price = float(price_content)
        except ValueError:
            price = self._parse_price(
                product.css('span.price::text').get() or ''
            )

        # URL
        url = (
            product.css('a.product-thumbnail::attr(href)').get()
            or product.css('h3.product-title a::attr(href)').get()
            or ''
        )

        # Stock
        in_stock = bool(product.css('div.product-availability.available'))

        # Brand
        brand = 'Inconnue'
        for b in self.KNOWN_BRANDS:
            if b.upper() in name.upper():
                brand = b
                break

        return {
            'id':         self._make_unique_id('ultrapc', category, name),
            'site':       'ultrapc',
            'category':   category,
            'name':       name,
            'price':      price,
            'in_stock':   in_stock,
            'brand':      brand,
            'url':        url,
            'scraped_at': self._now_utc(),
            'error':      None,
        }
