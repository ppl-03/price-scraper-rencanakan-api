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
    
    # Material Sanitair (bathroom/sanitary fixtures & accessories)
    SANITAIR_KEYWORDS = {
        'sanitair', 'sanitary',
        'closet', 'toilet', 'wc', 'bidet', 'urinoir', 'urinal',
        'wastafel', 'sink', 'lavatory', 'bathtub', 'bathup',
        'kran', 'keran', 'faucet', 'mixer', 'stop kran', 'stopkeran',
        'shower', 'jet shower', 'hand shower', 'shower set',
        'floor drain', 'floortrap', 'floor trap', 'drain',
        'siphon', 'p-trap', 'ptrap', 'trap',
        'selang flexible', 'flexible hose', 'selang shower', 'selang wc',
        'handuk', 'towel bar', 'towel holder', 'tissue', 'paper holder',
        'dispenser sabun', 'soap dispenser', 'cermin kamar mandi', 'cermin bathroom', 'kaca kamar mandi',
        'spray jet', 'jet washer', 'bidet spray'
    }
    
    SANITAIR_PATTERNS = [
        r'\bcloset (duduk|jongkok)\b',
        r'\b(shower|wastafel|urinoir|toilet)\b',
        r'\b(hand\s*shower|jet\s*shower|shower\s*set)\b',
        r'\bfloor\s*(drain|trap)\b',
        r'\b(stop\s*kran|keran|kran|faucet|mixer)\b',
        r'\b(p-?trap|siphon)\b',
    ]
    
    CATEGORY_SANITAIR = "Material Sanitair"
    
    # Alat Berat (Heavy Equipment)
    ALAT_BERAT_KEYWORDS = {
        'crane', 'bulldozer', 'drilling rig', 'truck', 'excavator',
        'compactor', 'roller', 'diesel', 'backhoe', 'loader',
        'grader', 'vibrator', 'palu', 'jackhammer', 'pneumatic',
        'genset', 'alat berat', 'heavy equipment', 'mesin berat'
    }
    
    ALAT_BERAT_PATTERNS = [
        r'\bcrane\b',
        r'\bbulldozer\b',
        r'\bdrilling\s*rig\b',
        r'\btrucking\b|\btruck\b',
        r'\bexcavator\b',
        r'\bcompactor\b',
        r'\broller\b',
        r'\bdiesel\b',
        r'\bbackhoe\b',
        r'\bloader\b',
    ]
    
    CATEGORY_ALAT_BERAT = "Alat Berat"
    
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

        # Sanitair detection
        if any(keyword in normalized for keyword in self.SANITAIR_KEYWORDS):
            return self.CATEGORY_SANITAIR
        if any(re.search(pattern, normalized) for pattern in self.SANITAIR_PATTERNS):
            # Avoid misclassifying construction pipes as sanitair; rely on explicit sanitair terms
            if not any(term in normalized for term in ('pipa', 'pipe', 'conduit')):
                return self.CATEGORY_SANITAIR
        
        # Alat Berat detection
        if any(keyword in normalized for keyword in self.ALAT_BERAT_KEYWORDS):
            return self.CATEGORY_ALAT_BERAT
        if any(re.search(pattern, normalized) for pattern in self.ALAT_BERAT_PATTERNS):
            return self.CATEGORY_ALAT_BERAT
        
        return None
    
    def categorize_batch(self, product_names: list[str]) -> list[str | None]:
        return [self.categorize(name) for name in product_names]
