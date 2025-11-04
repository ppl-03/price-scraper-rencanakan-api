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
        'vinyl', 'laminate', 'laminasi', 'klist',
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
    
    def _check_sanitair(self, normalized: str) -> bool:
        """Check if product matches Sanitair category."""
        if any(keyword in normalized for keyword in self.SANITAIR_KEYWORDS):
            return True
        if any(re.search(pattern, normalized) for pattern in self.SANITAIR_PATTERNS):
            # Avoid misclassifying construction pipes as sanitair
            if not any(term in normalized for term in ('pipa', 'pipe', 'conduit')):
                return True
        return False
    
    def _check_peralatan_kerja(self, normalized: str) -> bool:
        """Check if product matches Peralatan Kerja category."""
        if any(exclusion in normalized for exclusion in self.PERALATAN_KERJA_EXCLUSIONS):
            return False
        
        if any(re.search(pattern, normalized) for pattern in self.PERALATAN_KERJA_PATTERNS):
            return True
        
        if any(keyword in normalized for keyword in self.PERALATAN_KERJA_KEYWORDS):
            return True
        
        return False
    
    def _check_tanah_pasir_batu_semen(self, normalized: str) -> bool:
        """Check if product matches Tanah, Pasir, Batu, dan Semen category."""
        if any(exclusion in normalized for exclusion in self.TANAH_PASIR_BATU_SEMEN_EXCLUSIONS):
            return False
        
        if any(re.search(pattern, normalized) for pattern in self.TANAH_PASIR_BATU_SEMEN_PATTERNS):
            return True
        
        if any(keyword in normalized for keyword in self.TANAH_PASIR_BATU_SEMEN_KEYWORDS):
            return True
        
        return False
    
    def _check_steel(self, normalized: str) -> bool:
        """Check if product matches Steel category."""
        if any(exclusion in normalized for exclusion in self.STEEL_EXCLUSIONS):
            return False
        
        if any(keyword in normalized for keyword in self.STEEL_KEYWORDS):
            return True
        
        steel_terms = ('besi', 'baja', 'wire', 'metal', 'logam')
        if any(re.search(pattern, normalized) for pattern in self.STEEL_PATTERNS):
            if any(term in normalized for term in steel_terms):
                return True
        
        return False
    
    def _check_interior(self, normalized: str) -> bool:
        """Check if product matches Interior category."""
        if any(keyword in normalized for keyword in self.INTERIOR_KEYWORDS):
            return True
        
        if any(re.search(pattern, normalized) for pattern in self.INTERIOR_PATTERNS):
            return True
        
        return False
    
    def _check_pipa_air(self, normalized: str) -> bool:
        """Check if product matches Pipa Air category."""
        if any(keyword in normalized for keyword in self.PIPA_AIR_KEYWORDS):
            return True
        
        if any(re.search(pattern, normalized) for pattern in self.PIPA_AIR_PATTERNS):
            return True
        
        return False
    
    def categorize(self, product_name: str) -> str | None:
        if not product_name:
            return None
        
        normalized = product_name.lower().strip()
        
        # Check categories in priority order
        if self._check_sanitair(normalized):
            return self.CATEGORY_SANITAIR
        
        if self._check_peralatan_kerja(normalized):
            return self.CATEGORY_PERALATAN_KERJA
        
        if self._check_tanah_pasir_batu_semen(normalized):
            return self.CATEGORY_TANAH_PASIR_BATU_SEMEN
        
        if self._check_steel(normalized):
            return self.CATEGORY_STEEL
        
        if self._check_interior(normalized):
            return self.CATEGORY_INTERIOR
        
        if self._check_pipa_air(normalized):
            return self.CATEGORY_PIPA_AIR
        
        return None
    
    def categorize_batch(self, product_names: list[str]) -> list[str | None]:
        return [self.categorize(name) for name in product_names]

