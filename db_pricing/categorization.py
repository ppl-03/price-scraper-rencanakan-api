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
    
    LISTRIK_KEYWORDS = {
        # Cable types
        'kabel', 'cable', 'nyyhy', 'nyaf', 'nymhy', 'nymhyo', 
        'nyy', 'nyfgby', 'kawat', 'wire',
        
        # Switches and sockets
        'saklar', 'switch', 'broco', 'stop kontak', 'stopkontak',
        'socket', 'colokan', 'outlet', 'steker',
        
        # Circuit breakers
        'mcb', 'mccb', 'elcb', 'rccb', 'circuit breaker',
        'sekering', 'fuse', 'breaker', 'schneider',
        
        # Lighting fixtures
        'fitting', 'fitting lampu', 'dudukan lampu', 'socket lampu',
        'lampu holder', 'e27', 'e14', 'fatting',
        
        # Electrical conduits
        'pipa elektrik', 'conduit', 'pipa kabel', 'pipa pvc listrik',
        'clipsal', 'pipa fleksibel', 'flexible conduit',
        
        # Installation boxes
        'junction box', 'outlet box', 'box mcb', 'panel box',
        'instalasi box', 'kabel box', 'kotak sambungan',
        
        # Cable management
        'cable tie', 'kabel ties', 'cable clip', 'pengikat kabel',
        'tali kabel', 'tie wrap',
        
        # Insulation
        'isolasi', 'isolatip', 'lakban listrik', 'electrical tape',
        'insulation tape', 'tape listrik',
        
        # Electrical units (helps identify electrical products)
        'watt', 'volt', 'ampere', 'kwh', 'kva',
        
        # General electrical terms
        'listrik', 'electric', 'elektrik', 'lampu', 'lamp',
        'instalasi listrik', 'electrical installation'
    }
    
    LISTRIK_PATTERNS = [
        r'\b\d+x\d+(\.\d+)?\s*(mm|meter)\b',
        r'\b\d+\s*(v|volt|kv|kilovolt)\b',
        r'\b\d+\s*(w|watt|kw|kilowatt)\b',
        r'\b\d+\s*(a|amp|ampere)\b',
        
        # MCB/MCCB ratings (e.g., "MCB 10A", "MCCB 63A")
        r'\b(mcb|mccb|elcb|rccb)\s*\d+a?\b',
        
        # Cable size patterns (e.g., "NYY 3x2.5", "NYYHY 2x1.5")
        r'\b(nyy|nya|nymhy|nyyhy|nyfgby)\s*\d+x\d+(\.\d+)?\b',
        
        # Fitting types (e.g., "E27", "E14", "G9")
        r'\be\d{2}\b',
        
        r'\bconduit\b',
        r'\bjunction\b',
    ]
    
    CATEGORY_LISTRIK = "Material Listrik"
    
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
        
        if any(keyword in normalized for keyword in self.LISTRIK_KEYWORDS):
            # Extra validation: avoid false positives
            # Only categorize as electrical if it has electrical-specific terms
            electrical_indicators = {
                'kabel', 'cable', 'saklar', 'switch', 'mcb', 'listrik', 
                'electric', 'lampu', 'lamp', 'fitting', 'volt', 'watt', 
                'ampere', 'stop kontak', 'outlet', 'colokan'
            }
            if any(indicator in normalized for indicator in electrical_indicators):
                return self.CATEGORY_LISTRIK
        
        # Check listrik patterns
        if any(re.search(pattern, normalized) for pattern in self.LISTRIK_PATTERNS):
            return self.CATEGORY_LISTRIK
        
        return None

    def categorize_batch(self, product_names: list[str]) -> list[str | None]:
        return [self.categorize(name) for name in product_names]
