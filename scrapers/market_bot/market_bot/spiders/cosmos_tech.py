import re
import scrapy
from .base_spider import BaseMarketSpider


class CosmosTechSpider(BaseMarketSpider):
    name = "cosmos_tech"
    base_url = "https://cosmos-technologie.com"

    categories_urls = {
        'moniteur': 'https://cosmos-technologie.com/categorie-produit/ecran/',
        'laptop':   'https://cosmos-technologie.com/categorie-produit/pc-portable/',
    }

    KNOWN_BRANDS = [
        'HP', 'Dell', 'Lenovo', 'Asus', 'Acer', 'Apple', 'MSI',
        'Samsung', 'LG', 'Huawei', 'Toshiba', 'Gigabyte', 'Razer',
        'Microsoft', 'Sony', 'BenQ', 'ViewSonic', 'Philips', 'Aiwa',
        'AOC', 'Iiyama', 'Eizo', 'NEC', 'Alienware', 'Xiaomi',
    ]

    # Plain HTTP — no Playwright needed for this site
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

    # ------------------------------------------------------------------ #
    #  Requests                                                            #
    # ------------------------------------------------------------------ #

    async def start(self):
        for category, url in self.categories_urls.items():
            yield scrapy.Request(
                url,
                callback=self.parse_listing,
                errback=self.handle_error,
                cb_kwargs={'category': category, 'page': 1},
            )

    # ------------------------------------------------------------------ #
    #  Listing page                                                        #
    # ------------------------------------------------------------------ #

    def parse_listing(self, response, category, page):
        products = response.css('ul.products li.product')

        if not products:
            self.logger.warning(
                f"[cosmos_tech] No products found on {response.url} (page {page})"
            )
            return

        self.logger.info(
            f"[cosmos_tech] [{category}] page {page}: {len(products)} produits"
        )

        for product in products:
            item = self.parse_product(product, category)
            if item:
                yield item

        # Pagination
        next_page = (
            response.css('a.next.page-numbers::attr(href)').get()
            or response.css('a[rel="next"]::attr(href)').get()
        )
        if next_page:
            yield scrapy.Request(
                next_page,
                callback=self.parse_listing,
                errback=self.handle_error,
                cb_kwargs={'category': category, 'page': page + 1},
            )

    # ------------------------------------------------------------------ #
    #  Product parsing                                                     #
    # ------------------------------------------------------------------ #

    def parse_product(self, product, category):
        # Name
        name = (
            product.css('h5 a::text').get()
            or product.css('h2 a::text').get()
            or product.css('h3 a::text').get()
            or ''
        ).strip()

        if not name:
            return None

        name = self._clean_name(name)

        # Price — format WooCommerce: "864,00 د.م."
        # FIXED: utiliser getall() pour récupérer TOUS les noeuds texte de <bdi>
        # Le HTML WooCommerce sépare le symbole monétaire du montant en noeuds distincts
        raw_price = ' '.join(
            product.css('span.woocommerce-Price-amount bdi::text').getall()
        ).strip()

        price = self._parse_price(raw_price)

        # URL
        url = (
            product.css('a.woocommerce-loop-product__link::attr(href)').get()
            or product.css('h5 a::attr(href)').get()
            or ''
        )

        # Brand
        brand = 'Inconnue'
        for b in self.KNOWN_BRANDS:
            if b.upper() in name.upper():
                brand = b
                break

        return {
            'id':         self._make_unique_id('cosmos_tech', category, name),
            'site':       'cosmos_tech',
            'category':   category,
            'name':       name,
            'price':      price,
            'in_stock':   None,
            'brand':      brand,
            'url':        url,
            'scraped_at': self._now_utc(),
            'error':      None,
        }
