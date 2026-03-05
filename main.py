import json
import time
import requests
import re

class ProductScraper:
    def __init__(self):
        # Initialize a requests session to reuse connections (better performance)
        self.session = requests.Session()
        
    def log(self, message: str, level: str = 'INFO'):
        """Placeholder for your logging mechanism."""
        print(f"[{level}] {message}")
        
    def get_json_url(self, page: int) -> str:
        """Placeholder for your URL generation logic."""
        return f"https://www.firstcry.com/svcs/SearchResult.svc/GetSearchResultProductsPaging?PageNo=1&PageSize=20&SortExpression=popularity&OnSale=5&SearchString=brand&SubCatId=&BrandId=&Price=&Age=&Color=&OptionalFilter=&OutOfStock=&Type1=&Type2=&Type3=&Type4=&Type5=&Type6=&Type7=&Type8=&Type9=&Type10=&Type11=&Type12=&Type13=&Type14=&Type15=&combo=&discount=&searchwithincat=&ProductidQstr=&searchrank=&pmonths=&cgen=&PriceQstr=&DiscountQstr=&sorting=&MasterBrand=113&Rating=&Offer=&skills=&material=&curatedcollections=&measurement=&gender=&exclude=&premium=&pcode=380008&isclub=0&deliverytype=&author=&booktype=&character=&collection=&format=&genre=&booklanguage=&publication=&skill="

    def slugify(self, text: str) -> str:
        if not text:
            return ""
            
        # 1. Lowercase
        text = text.lower()
        
        # 2. Handle special characters
        replacements = {
            '&': 'and',
            '/': '-',
            '(': '',
            ')': '',
            ',': ''
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # 3. Remove any other unwanted characters (keep letters, numbers, spaces, hyphens)
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        
        # 4. Replace spaces and multiple hyphens with single hyphen
        text = re.sub(r'[\s-]+', '-', text)
        
        # 5. Trim hyphens
        return text.strip('-')

    def parse_json_products(self, json_data: str) -> dict:
        if not json_data:
            return {}
            
        try:
            response = json.loads(json_data)
        except json.JSONDecodeError:
            self.log("Invalid JSON format", "ERR")
            return {}

        if not response or 'ProductResponse' not in response:
            return {}

        # DOUBLE DECODE: ProductResponse is a string containing JSON
        try:
            product_response = json.loads(response['ProductResponse'])
        except json.JSONDecodeError:
            return {}

        if not product_response or 'Products' not in product_response:
            return {}

        products = {}
        for item in product_response.get('Products', []):
            pid = item.get('PId')
            title = item.get('PNm')
            
            if not pid or not title:
                continue
            
            # Price logic: use discprice if available, else MRP
            price_val = item.get('discprice')
            if price_val is None:
                price_val = item.get('MRP', 0)
            price = float(price_val)
            
            # Stock logic
            stock_count = int(item.get('CrntStock', 0))
            status = 'IN_STOCK' if stock_count > 0 else 'OUT_OF_STOCK'
            
            # Image logic
            image = ''
            images_str = item.get('Images', '')
            if images_str:
                images_list = images_str.split(';')
                if images_list and images_list[0]:
                    image = f"https://cdn.fcglcdn.com/brainbees/images/products/438x531/{images_list[0]}"
            
            # Link logic
            slug = self.slugify(title)
            link = f"https://www.firstcry.com/hot-wheels/{slug}/{pid}/product-detail"
            
            products[pid] = {
                'id': pid,
                'title': title,
                'price': price,
                'display_price': f"₹{price}",
                'image': image,
                'link': link,
                'status': status,
                'stock_count': stock_count,
                'is_new': item.get('newdays') == '1',
                'rating': float(item.get('rating', 0)),
                'reviews': int(item.get('review', 0)),
                'age_min': int(item.get('AgeF')) if item.get('AgeF') is not None else None,
                'age_max': int(item.get('AgeT')) if item.get('AgeT') is not None else None,
                'last_scanned': int(time.time()),
                'source': 'JSON'
            }
            
        return products

    def fetch_json(self, page: int) -> str | None:
        url = self.get_json_url(page)
        
        try:
            # Using the class session handles connection pooling automatically
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 429:
                self.log(f"⚠️ RATE LIMITED (429) P{page} (JSON)", 'WARN')
                return None
                
            if response.status_code != 200:
                self.log(f"HTTP {response.status_code} on P{page} (JSON)", 'ERR')
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            self.log(f"Request Error P{page} (JSON): {str(e)}", 'ERR')

            return None
