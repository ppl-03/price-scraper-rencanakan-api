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
    
    def categorize(self, product_name: str) -> str | None:
        if not product_name:
            return None
        
        normalized = product_name.lower().strip()
        
        # Check for Tanah, Pasir, Batu, dan Semen first
        # Check exclusions first to avoid false positives
        has_exclusion = any(exclusion in normalized for exclusion in self.TANAH_PASIR_BATU_SEMEN_EXCLUSIONS)
        
        if not has_exclusion:
            # Check for specific patterns
            has_pattern = any(re.search(pattern, normalized) for pattern in self.TANAH_PASIR_BATU_SEMEN_PATTERNS)
            if has_pattern:
                return self.CATEGORY_TANAH_PASIR_BATU_SEMEN
            
            # Check for keywords
            has_keyword = any(keyword in normalized for keyword in self.TANAH_PASIR_BATU_SEMEN_KEYWORDS)
            if has_keyword:
                return self.CATEGORY_TANAH_PASIR_BATU_SEMEN
        
        # Check for Steel category
        has_keyword = any(keyword in normalized for keyword in self.STEEL_KEYWORDS)
        if has_keyword:
            return self.CATEGORY_STEEL
        
        has_pattern = any(re.search(pattern, normalized) for pattern in self.STEEL_PATTERNS)
        if has_pattern and ('besi' in normalized or 'baja' in normalized or 'wire' in normalized):
            return self.CATEGORY_STEEL
        
        return None
    
    def categorize_batch(self, product_names: list[str]) -> list[str | None]:
        return [self.categorize(name) for name in product_names]
