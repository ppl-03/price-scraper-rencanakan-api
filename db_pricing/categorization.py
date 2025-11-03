import re


class ProductCategorizer:
    
    STEEL_KEYWORDS = {
        'besi', 'baja', 'tulangan', 'wiremesh', 'wire mesh',
        'hollow', 'siku', 'cnp', 'wf', 'h-beam', 'h beam',
        'i-beam', 'i beam', 'polos', 'ulir',
        'galvanis', 'galvanized', 'steel', 'iron', 'rebar'
    }
    
    STEEL_EXCLUSIONS = {
        'pasir', 'sand', 'semen', 'cement'
    }
    
    STEEL_PATTERNS = [
        r'\b\d+mm\b',
        r'\b\d+x\d+\b',
        r'\bm\d+\b',
        r'\b\d+\.\d+mm\b',
        r'\b\d+x\d+x\d+\b',
    ]
    
    INTERIOR_KEYWORDS = {
        'plafon', 'plafond', 'ceiling', 'gypsum', 'gipsum',
        'wallpaper', 'wall paper', 'dinding', 'keramik', 'ceramic',
        'granit', 'granite', 'marmer', 'marble', 'parket', 'parquet',
        'vinyl', 'laminate', 'laminasi', 'klist', 'klist', 
        'skirting', 'list', 'lantai', 'flooring', 'floor',
        'tile', 'tiles', 'ubin', 'cat', 'paint', 'lem', 'glue'
    }
    
    INTERIOR_PATTERNS = [
        r'\bplafon\b',
        r'\bgypsum\b',
        r'\bkeramik\b',
        r'\bgranit\b',
        r'\bmarmer\b',
        r'\bparket\b',
        r'\bvinyl\b',
        r'\blaminate\b',
        r'\btapeta\b',
    ]
    
    CATEGORY_STEEL = "Baja dan Besi Tulangan"
    CATEGORY_INTERIOR = "Material Interior"
    
    def categorize(self, product_name: str) -> str | None:
        if not product_name:
            return None
        
        normalized = product_name.lower().strip()
        
        has_exclusion = any(exclusion in normalized for exclusion in self.STEEL_EXCLUSIONS)
        if has_exclusion:
            has_interior_keyword = any(keyword in normalized for keyword in self.INTERIOR_KEYWORDS)
            if has_interior_keyword:
                return self.CATEGORY_INTERIOR
            return None
        
        has_steel_keyword = any(keyword in normalized for keyword in self.STEEL_KEYWORDS)
        if has_steel_keyword:
            return self.CATEGORY_STEEL
        
        has_steel_pattern = any(re.search(pattern, normalized) for pattern in self.STEEL_PATTERNS)
        if has_steel_pattern and ('metal' in normalized or 'logam' in normalized):
            return self.CATEGORY_STEEL
        
        has_interior_keyword = any(keyword in normalized for keyword in self.INTERIOR_KEYWORDS)
        if has_interior_keyword:
            return self.CATEGORY_INTERIOR
        
        has_interior_pattern = any(re.search(pattern, normalized) for pattern in self.INTERIOR_PATTERNS)
        if has_interior_pattern:
            return self.CATEGORY_INTERIOR
        
        return None
    
    def categorize_batch(self, product_names: list[str]) -> list[str | None]:
        return [self.categorize(name) for name in product_names]
