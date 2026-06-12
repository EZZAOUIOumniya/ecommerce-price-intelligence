import scrapy
import re
from datetime import datetime

class JumiaSpider(scrapy.Spider):
    name = "jumia"
    
    categories = {
        'laptop': 'https://www.jumia.ma/pc-portables/',
        'smartphone': 'https://www.jumia.ma/smartphones/',
        'tablet': 'https://www.jumia.ma/tablettes/'
    }

    def start_requests(self):
        for cat, url in self.categories.items():
            yield scrapy.Request(
                url, 
                callback=self.parse,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    'Referer': 'https://www.google.com/'
                },
                cb_kwargs={'category': cat}
            )

    def parse(self, response, category):
        products = response.css('article.prd')
        
        for product in products:
            raw_name = product.css('h3.name::text').get()
            # MODIFICATION : On récupère tout le texte dans .prc, incluant les balises enfants
            # Puis on nettoie proprement
            price_text = product.css('div.prc').xpath('string()').get()
            p_id = product.attrib.get('data-id')
            brand = product.attrib.get('data-brand')

            # --- NETTOYAGE ROBUSTE DU PRIX ---
            clean_price = 0
            if price_text:
                # On enlève tout sauf les chiffres
                digits = re.sub(r'[^\d]', '', price_text)
                # Jumia affiche souvent des prix comme 120000 au lieu de 1200.00
                # Si le prix semble trop petit, c'est probablement un mauvais sélecteur
                if digits and len(digits) > 2:
                    clean_price = int(digits[:-2]) # On tronque les deux derniers chiffres si centimes
                elif digits:
                    clean_price = int(digits)

            if raw_name:
                yield {
                    'id': p_id if p_id else raw_name.strip().replace(" ", "_").lower()[:25],
                    'site': 'jumia',
                    'category': category,
                    'name': raw_name.strip(),
                    'price': clean_price,
                    'brand': brand if brand else "Inconnue",
                    'url': response.urljoin(product.css('a.core::attr(href)').get()),
                    'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

        # --- PAGINATION ---
        next_page = response.css('a[aria-label="Page suivante"]::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse, cb_kwargs={'category': category})
