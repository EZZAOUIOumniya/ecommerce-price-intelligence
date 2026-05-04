import scrapy
import re
from datetime import datetime


class JumiaSpider(scrapy.Spider):
    name = "jumia"

    categories = {
        'laptop':     'https://www.jumia.ma/pc-portables/',
        'smartphone': 'https://www.jumia.ma/smartphones/',
        'tablet':     'https://www.jumia.ma/tablettes/',
    }

    custom_settings = {
        'DOWNLOAD_HANDLERS': {},
        'PLAYWRIGHT_BROWSER_TYPE': None,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'DOWNLOAD_DELAY': 1.0,
    }

    # ------------------------------------------------------------------ #
    #  Requests                                                            #
    # ------------------------------------------------------------------ #

    async def start(self):
        for cat, url in self.categories.items():
            yield scrapy.Request(
                url,
                callback=self.parse,
                headers={
                    'User-Agent': (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/124.0.0.0 Safari/537.36'
                    ),
                    'Referer': 'https://www.google.com/',
                },
                cb_kwargs={'category': cat},
                errback=self.handle_error,
            )

    # ------------------------------------------------------------------ #
    #  Listing page                                                        #
    # ------------------------------------------------------------------ #

    def parse(self, response, category):
        products = response.css('article.prd')

        if not products:
            self.logger.warning(
                f"[jumia] No products found on {response.url} (category: {category})"
            )
            return

        self.logger.info(
            f"[jumia] [{category}] {len(products)} produits sur {response.url}"
        )

        for product in products:
            item = self.parse_product(product, category, response)
            if item:
                yield item

        # Pagination
        next_page = response.css('a[aria-label="Page suivante"]::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse,
                cb_kwargs={'category': category},
                errback=self.handle_error,
            )

    # ------------------------------------------------------------------ #
    #  Product parsing                                                     #
    # ------------------------------------------------------------------ #

    def parse_product(self, product, category, response):
        # Name
        raw_name = product.css('h3.name::text').get()
        if not raw_name:
            return None
        name = raw_name.strip()

        # Price
        # HTML: <div class="prc" data-oprc="6,199.00 Dhs">5,899.00 Dhs</div>
        # Format: virgule = séparateur milliers, point = décimal
        # On prend le texte direct (prix actuel), pas data-oprc (prix barré)
        price_text = product.css('div.prc::text').get() or ''
        price = self._parse_jumia_price(price_text)

        # Prix barré (optionnel, pour comparaison)
        old_price_text = product.css('div.prc::attr(data-oprc)').get() or ''
        old_price = self._parse_jumia_price(old_price_text) if old_price_text else None

        # IDs & metadata
        p_id  = product.attrib.get('data-id') or name.replace(' ', '_').lower()[:25]
        brand = product.attrib.get('data-brand') or 'Inconnue'
        url   = response.urljoin(product.css('a.core::attr(href)').get() or '')

        return {
            'id':         p_id,
            'site':       'jumia',
            'category':   category,
            'name':       name,
            'price':      price,
            'old_price':  old_price,
            'brand':      brand,
            'url':        url,
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error':      None,
        }

    # ------------------------------------------------------------------ #
    #  Price parser                                                        #
    # ------------------------------------------------------------------ #

    def _parse_jumia_price(self, price_text: str) -> int:
        """
        Parse le prix Jumia.ma correctement.

        Formats observés :
          "5,899.00 Dhs"  -> 5899
          "1,200.00 Dhs"  -> 1200
          "449.00 Dhs"    -> 449
          "6,199.00 Dhs"  -> 6199

        Regle : virgule = separateur de milliers (pas decimal)
                point   = separateur decimal -> on prend la partie entiere
        """
        if not price_text:
            return 0

        # Supprimer la virgule (séparateur milliers) et tout sauf chiffres et point
        cleaned = re.sub(r'[^\d.]', '', price_text.replace(',', ''))

        if not cleaned:
            return 0

        try:
            return int(float(cleaned))
        except ValueError:
            self.logger.warning(f"[jumia] Price parse failed: '{price_text}' -> '{cleaned}'")
            return 0

    # ------------------------------------------------------------------ #
    #  Error handling                                                      #
    # ------------------------------------------------------------------ #

    def handle_error(self, failure):
        url      = failure.request.url
        category = failure.request.cb_kwargs.get('category', 'unknown')
        self.logger.error(f"[jumia] Network error [{category}] {url}: {repr(failure)}")
