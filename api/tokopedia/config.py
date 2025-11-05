class TokopediaSelectors:
    """CSS selectors and HTML patterns for Tokopedia parsing"""
    
    # Product container selectors
    PRODUCT_CONTAINER = 'a[data-testid="lnkProductContainer"]'
    PRODUCT_WRAPPER = 'div[data-testid="divProductWrapper"]'
    
    # Product name selectors
    PRODUCT_NAME_PRIMARY = 'span.css-20kt3o'
    PRODUCT_NAME_FALLBACK = 'div[data-testid="divProductWrapper"] span'
    PRODUCT_IMAGE = 'img'
    
    # Price selectors
    PRICE_PRIMARY = 'span.css-o5uqv'
    
    # Location selectors
    LOCATION_PRIMARY = 'span.css-ywdpwd'
    LOCATION_WRAPPER = 'div.css-vbihp9'
    
    def __init__(self):
        """Initialize selectors (can be overridden in subclasses)"""
        pass


class TokopediaLocations:
    """Location keywords and validation rules for Tokopedia"""
    
    # Popular Indonesian cities and regencies
    POPULAR_LOCATIONS = {
        'jakarta', 'surabaya', 'bandung', 'medan', 'semarang', 'yogyakarta',
        'makassar', 'tangerang', 'depok', 'bekasi', 'bogor', 'malang',
        'sidoarjo', 'jombang', 'pasuruan', 'tasikmalaya', 'bandar lampung',
        'palembang', 'batam', 'pekanbaru', 'padang', 'banjarmasin',
        'samarinda', 'manado', 'pontianak', 'denpasar', 'lombok', 'jayapura',
        'serang', 'cilegon', 'pandeglang', 'rangkasbitung', 'purwakarta',
        'subang', 'karawang', 'cirebon', 'kudus', 'pati', 'rembang',
        'sleman', 'sukoharjo', 'wonogiri', 'klaten', 'demak', 'grobogan',
        'jakarta utara', 'jakarta selatan', 'jakarta timur', 'jakarta barat',
        'jakarta pusat', 'kota jakarta', 'kab bogor', 'kab bekasi',
        'kota tangerang', 'kota depok', 'kab tangerang'
    }
    
    # Location keywords for fallback extraction
    LOCATION_KEYWORDS = {
        'jakarta', 'bandung', 'surabaya', 'medan', 'semarang',
        'yogyakarta', 'makassar', 'tangerang', 'depok', 'bekasi',
        'bogor', 'malang', 'kab', 'kota', 'utara', 'selatan',
        'timur', 'barat', 'pusat', 'riau', 'sulawesi', 'bali',
        'sumatra', 'kalimantan', 'jawa', 'nusa', 'papua'
    }
    
    # UI text to skip during extraction
    SKIP_TEXTS = {
        'tambah ke wishlist', 'add to wishlist', 'beli', 'buy',
        'lihat semua', 'view all', 'gratis ongkir', 'free shipping',
        'terjual', 'sold', 'rating', 'komentar', 'comment', 'review'
    }
    
    # Location text validation rules
    MIN_LENGTH = 2
    MAX_LENGTH = 100
    DELIMITER_PATTERN = r'[\n\r•\|,]'
    
    def __init__(self):
        """Initialize location configuration"""
        pass


class TokopediaUrlConfig:
    """URL configuration for Tokopedia scraper"""
    
    BASE_URL = "https://www.tokopedia.com"
    PRODUCT_URL_PATTERN = "{base_url}/product/{slug}"
    UNKNOWN_PRODUCT_URL = "{base_url}/product/unknown"
    
    def __init__(self, url: str = BASE_URL):
        """
        Initialize URL configuration
        
        Args:
            url: Base URL for Tokopedia (default: production URL)
        """
        self.url = url
    
    def get_product_url(self, slug: str) -> str:
        """Get formatted product URL from slug"""
        return self.PRODUCT_URL_PATTERN.format(base_url=self.url, slug=slug)
    
    def get_unknown_url(self) -> str:
        """Get URL for products with unknown/invalid slug"""
        return self.UNKNOWN_PRODUCT_URL.format(base_url=self.url)


class TokopediaPriceConfig:
    """Price validation configuration"""
    
    # Price range validation (in rupiah)
    MIN_VALID_PRICE = 100
    MAX_VALID_PRICE = 100_000_000
    
    def __init__(self, min_price: int = MIN_VALID_PRICE, max_price: int = MAX_VALID_PRICE):
        """
        Initialize price configuration
        
        Args:
            min_price: Minimum valid price in rupiah
            max_price: Maximum valid price in rupiah
        """
        self.min_price = min_price
        self.max_price = max_price
    
    def is_valid(self, price: int) -> bool:
        """Check if price is within valid range"""
        return self.min_price <= price <= self.max_price
