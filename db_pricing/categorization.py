import re


class ProductCategorizer:
    
    STEEL_KEYWORDS = {
        'besi', 'baja', 'tulangan', 'wiremesh', 'wire mesh',
        'hollow', 'siku', 'cnp', 'wf', 'h-beam', 'h beam',
        'i-beam', 'i beam', 'beton', 'polos', 'ulir',
        'galvanis', 'galvanized', 'steel', 'iron', 'rebar'
    }
    
    STEEL_PATTERNS = [
        r'\b\d+mm\b',
        r'\b\d+x\d+\b',
        r'\bm\d+\b',
        r'\b\d+\.\d+mm\b',
        r'\b\d+x\d+x\d+\b',
    ]
    
    CATEGORY_STEEL = "Baja dan Besi Tulangan"
    
    # Tanah, Pasir, Batu, dan Semen Keywords
    TANAH_PASIR_BATU_SEMEN_KEYWORDS = {
        # Semen
        'semen', 'cement', 'portland', 'mortar', 'instan',
        # Pasir
        'pasir', 'sand', 'silika',
        # Batu
        'batu split', 'split', 'koral', 'kerikil', 'batu kali',
        'batu belah', 'agregat', 'abu batu', 'sirtu',
        # Tanah
        'tanah urug', 'tanah merah', 'tanah hitam', 'tanah liat',
        'tanah subur', 'urug'
    }
    
    # Specific patterns for this category
    TANAH_PASIR_BATU_SEMEN_PATTERNS = [
        r'\bsemen\s+(portland|putih|gresik|tiga\s*roda|baturaja|holcim|tonasa)',
        r'\bpasir\s+(pasang|beton|urug|cor|curah|bangka|silika)',
        r'\bbatu\s+(split|kali|belah|koral)',
        r'\btanah\s+(urug|merah|hitam|liat|subur)',
        r'\bsplit\s+\d+/\d+',
        r'\bkerikil\b',
        r'\babu\s+batu\b',
        r'\bsirtu\b',
        r'\bagregat\s+(halus|kasar)',
    ]
    
    # Exclusion patterns to avoid false positives
    TANAH_PASIR_BATU_SEMEN_EXCLUSIONS = {
        'keramik', 'ceramic', 'granit', 'granite', 'marmer', 'marble',
        'batu baterai', 'baterai', 'battery', 'tanaman', 'pot',
        'batu alam', # keramik batu alam should not match
        'cat pasir', 'cat ' # cat products should not match
    }
    
    CATEGORY_TANAH_PASIR_BATU_SEMEN = "Tanah, Pasir, Batu, dan Semen"
    
    # Peralatan Kerja Keywords
    PERALATAN_KERJA_KEYWORDS = {
        # Hand tools
        'palu', 'obeng', 'tang', 'gergaji', 'pahat', 'tatah', 'kikir',
        'kunci inggris', 'kunci ring', 'kunci pas', 'kunci sok',
        'linggis', 'sekop', 'cangkul', 'garpu', 'sabit',
        # Measuring tools
        'meteran', 'waterpass', 'siku tukang', 'penggaris', 'jangka',
        # Power tools
        'bor', 'drill', 'gerinda', 'grinder', 'mesin potong',
        'circular saw', 'jigsaw', 'router', 'planer', 'sander',
        # Clamping tools
        'ragum', 'klem', 'clamp',
        # Construction tools
        'roskam', 'sendok semen', 'cetok', 'jidar', 'unting-unting',
        'benang tukang', 'timba cor', 'ember cat', 'trowel',
        # Cutting tools
        'gunting seng', 'pemotong', 'cutter', 'pisau roti',
        # Other tools
        'amplas tangan', 'gerinda tangan', 'hammer', 'wrench', 'pliers',
        'saw', 'chisel', 'file', 'screwdriver', 'spanner',
    }
    
    PERALATAN_KERJA_PATTERNS = [
        r'\b(palu|hammer)\s+(besi|kayu|konde|godam)',
        r'\b(obeng|screwdriver)\s+(plus|minus|set|ketok)',
        r'\b(tang|pliers)\s+(potong|kombinasi|buaya|lancip)',
        r'\b(gergaji|saw)\s+(kayu|besi|mesin|manual)',
        r'\b(meteran|measure)\s+(gulung|dorong|laser|digital)',
        r'\b(bor|drill)\s+(tangan|listrik|beton|kayu|impact|hammer)',
        r'\b(gerinda|grinder)\s+(tangan|potong|poles)',
        r'\b(pahat|chisel)\s+(kayu|beton|besi)',
        r'\bkunci\s+(inggris|ring|pas|sok|l)',
        r'\b(waterpass|level)\s+(aluminium|digital)',
        r'\b(ragum|vice|vise)\s+meja',
        r'\b(klem|clamp)\s+[fcg]',
        r'\b(roskam|trowel|cetok)\s+(kayu|plastik|stainless)',
        r'\b(gunting|scissors)\s+(seng|besi|kain)',
        r'\b(sekop|cangkul|linggis)\s+(besi|taman|tanah)',
        r'\bsendok\s+semen',  # sendok semen is a tool, not cement
    ]
    
    # Exclusions to avoid false positives
    PERALATAN_KERJA_EXCLUSIONS = {
        'paku', 'mur', 'baut', 'sekrup', 'screw', 'nail', 'bolt', 'nut',
        'besi beton', 'besi tulangan', 'pipa', 'kabel',
        'cat tembok', 'keramik', 'closet', 'kran', 'pintu', 'engsel',
    }
    
    CATEGORY_PERALATAN_KERJA = "Peralatan Kerja"
    
    def _check_category_match(self, normalized: str, keywords: set, patterns: list, exclusions: set = None) -> bool:
        """Helper method to check if a product matches a category."""
        if exclusions and any(exclusion in normalized for exclusion in exclusions):
            return False
        
        # Check patterns first (more specific)
        if any(re.search(pattern, normalized) for pattern in patterns):
            return True
        
        # Check keywords
        return any(keyword in normalized for keyword in keywords)
    
    def categorize(self, product_name: str) -> str | None:
        if not product_name:
            return None
        
        normalized = product_name.lower().strip()
        
        # Check for Peralatan Kerja first
        if self._check_category_match(normalized, self.PERALATAN_KERJA_KEYWORDS, 
                                      self.PERALATAN_KERJA_PATTERNS, 
                                      self.PERALATAN_KERJA_EXCLUSIONS):
            return self.CATEGORY_PERALATAN_KERJA
        
        # Check for Tanah, Pasir, Batu, dan Semen
        if self._check_category_match(normalized, self.TANAH_PASIR_BATU_SEMEN_KEYWORDS,
                                      self.TANAH_PASIR_BATU_SEMEN_PATTERNS,
                                      self.TANAH_PASIR_BATU_SEMEN_EXCLUSIONS):
            return self.CATEGORY_TANAH_PASIR_BATU_SEMEN
        
        # Check for Steel category
        if self._check_category_match(normalized, self.STEEL_KEYWORDS, self.STEEL_PATTERNS):
            return self.CATEGORY_STEEL
        
        return None
    
    def categorize_batch(self, product_names: list[str]) -> list[str | None]:
        return [self.categorize(name) for name in product_names]
