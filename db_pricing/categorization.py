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
    
    def categorize(self, product_name: str) -> str | None:
        if not product_name:
            return None
        
        normalized = product_name.lower().strip()
        
        has_keyword = any(keyword in normalized for keyword in self.STEEL_KEYWORDS)
        if has_keyword:
            return self.CATEGORY_STEEL
        
        has_pattern = any(re.search(pattern, normalized) for pattern in self.STEEL_PATTERNS)
        if has_pattern and ('besi' in normalized or 'baja' in normalized or 'wire' in normalized):
            return self.CATEGORY_STEEL
        
        return None
    
    def categorize_batch(self, product_names: list[str]) -> list[str | None]:
        return [self.categorize(name) for name in product_names]
