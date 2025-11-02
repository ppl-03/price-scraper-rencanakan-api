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
    
    # Material Pipa Air (water pipes & fittings)
    PIPA_AIR_KEYWORDS = {
        'pipa', 'pipe', 'pvc', 'ppr', 'hdpe', 'upvc',
        'pipa air', 'water pipe', 'pipa pralon', 'pralon',
        'elbow', 'knee', 'tee', 'sambungan', 'fitting',
        'socket', 'drat', 'coupling', 'reducer', 'union',
        'ball valve', 'gate valve', 'check valve', 'valve',
        'flange', 'clamp', 'saddle', 'end cap', 'tutup pipa',
        'pipa tanam', 'pipa induk', 'pipa cabang',
        'pipa bersih', 'pipa kotor', 'pipa limbah',
        'lem pvc', 'pvc glue', 'teflon', 'seal tape'
    }
    
    PIPA_AIR_PATTERNS = [
        r'\bpipa\s+(pvc|ppr|hdpe|upvc|air|pralon)\b',
        r'\b(pvc|ppr|hdpe|upvc)\s+pipe\b',
        r'\b(elbow|tee|knee|socket|reducer)\s+\d+',
        r'\b\d+\s*(inch|"|mm)\s+(pipa|pipe|elbow|tee)\b',
        r'\bpipa\s+\d+\s*(inch|"|mm)\b',
        r'\b(ball|gate|check)\s+valve\b',
    ]
    
    CATEGORY_PIPA_AIR = "Material Pipa Air"
    
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
        
        # Check Pipa Air category
        if any(keyword in normalized for keyword in self.PIPA_AIR_KEYWORDS):
            return self.CATEGORY_PIPA_AIR
        if any(re.search(pattern, normalized) for pattern in self.PIPA_AIR_PATTERNS):
            return self.CATEGORY_PIPA_AIR
        
        return None
    
    def categorize_batch(self, product_names: list[str]) -> list[str | None]:
        return [self.categorize(name) for name in product_names]
