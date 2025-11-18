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
    
    # Alat Berat (Heavy Equipment)
    ALAT_BERAT_KEYWORDS = {
        'crane', 'bulldozer', 'drilling rig', 'truck', 'excavator',
        'compactor', 'roller', 'diesel', 'backhoe', 'loader',
        'grader', 'vibrator', 'jackhammer', 'pneumatic',
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
    
    def _check_alat_berat(self, normalized: str) -> bool:
        """Check if product matches Alat Berat (Heavy Equipment) category."""
        if any(re.search(pattern, normalized) for pattern in self.ALAT_BERAT_PATTERNS):
            return True

        if any(keyword in normalized for keyword in self.ALAT_BERAT_KEYWORDS):
            return True
        
        return False
    
    def _check_sanitair(self, normalized: str) -> bool:
        """Check if product matches Sanitair category."""
        # Sanitair has priority over Interior for bathroom fixtures
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
        
        # Exclude pipe-related products (e.g., "saddle clamp" is a pipe fitting, not a tool)
        pipe_indicators = {'pipa', 'pipe', 'pvc', 'ppr', 'hdpe', 'pralon', 'saddle'}
        if any(indicator in normalized for indicator in pipe_indicators):
            return False
        
        if any(re.search(pattern, normalized) for pattern in self.PERALATAN_KERJA_PATTERNS):
            return True
        
        if any(keyword in normalized for keyword in self.PERALATAN_KERJA_KEYWORDS):
            return True
        
        return False
    
    def _check_tanah_pasir_batu_semen(self, normalized: str) -> bool:
        """Check if product matches Tanah, Pasir, Batu, dan Semen category.
        
        This category requires specific pattern matches (not just bare keywords)
        to avoid false positives.
        """
        if any(exclusion in normalized for exclusion in self.TANAH_PASIR_BATU_SEMEN_EXCLUSIONS):
            return False
        
        if any(re.search(pattern, normalized) for pattern in self.TANAH_PASIR_BATU_SEMEN_PATTERNS):
            return True
        
        # Also accept standalone specific terms that are unambiguous
        standalone_terms = {'semen', 'kerikil', 'sirtu', 'agregat'}
        if any(term in normalized for term in standalone_terms):
            return True
        
        return False
    
    def _check_steel(self, normalized: str) -> bool:
        """Check if product matches Steel category."""
        if any(exclusion in normalized for exclusion in self.STEEL_EXCLUSIONS):
            return False
        
        # If this product has Peralatan Kerja keywords, don't match as steel
        # This prevents "Palu Besi" from being categorized as steel
        tool_indicators = {'palu', 'obeng', 'tang', 'gergaji', 'sekop', 'linggis', 'siku tukang', 'kikir', 'bor', 'gerinda', 'kunci'}
        if any(tool in normalized for tool in tool_indicators):
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
        # Special handling for "lem"/"glue": only Interior if NOT pipe-related
        # Check this BEFORE general keyword matching to avoid false positives
        if 'lem' in normalized or 'glue' in normalized:
            # If it has pipe context (pvc, pipa, pralon), NOT Interior
            if any(pipe_term in normalized for pipe_term in ('pvc', 'pipa', 'pralon')):
                return False
            # Otherwise, it's an interior glue
            return True
        
        interior_keywords_excluding_glue = self.INTERIOR_KEYWORDS - {'lem', 'glue'}
        if any(keyword in normalized for keyword in interior_keywords_excluding_glue):
            return True
        
        if any(re.search(pattern, normalized) for pattern in self.INTERIOR_PATTERNS):
            return True
        
        return False
    
    def _check_pipa_air(self, normalized: str) -> bool:
        """Check if product matches Pipa Air category."""
        # Special handling for "fitting": electrical fitting vs pipe fitting
        # Check this BEFORE general keyword matching
        if 'fitting' in normalized:
            # If it has electrical context (lampu, listrik), NOT Pipa Air
            if 'lampu' in normalized or 'listrik' in normalized:
                return False
            # Otherwise, it's a pipe fitting
            return True
        
        if any(re.search(pattern, normalized) for pattern in self.PIPA_AIR_PATTERNS):
            return True
        
        # Check keywords (excluding fitting which we already handled)
        pipa_keywords_excluding_fitting = self.PIPA_AIR_KEYWORDS - {'fitting'}
        if any(keyword in normalized for keyword in pipa_keywords_excluding_fitting):
            return True
        
        # "saddle" in pipe context (or standalone)
        if 'saddle' in normalized:
            return True
        
        # "lem" with pipe context (lem pvc, lem pipa)
        if 'lem' in normalized and ('pvc' in normalized or 'pipa' in normalized or 'pralon' in normalized):
            return True
        
        return False
    

    def _check_listrik(self, normalized: str) -> bool:
        """Check if product matches Material Listrik category."""
        
        if any(re.search(pattern, normalized) for pattern in self.LISTRIK_PATTERNS):
            return True
        
        
        electrical_indicators = {
            'kabel', 'cable', 'saklar', 'switch', 'mcb', 'listrik', 
            'electric', 'elektrik', 'lampu', 'lamp', 'volt', 'watt', 
            'ampere', 'stop kontak', 'outlet', 'colokan'
        }
        
        # "pipa conduit" or "conduit elektrik" -> Listrik
        if 'conduit' in normalized and ('elektrik' in normalized or 'listrik' in normalized or 'kabel' in normalized):
            return True
        
        # "fitting lampu" -> Listrik
        if 'fitting' in normalized and ('lampu' in normalized or 'listrik' in normalized or 'e27' in normalized or 'e14' in normalized):
            return True
        
        # "isolasi listrik" -> Listrik
        if 'isolasi' in normalized and 'listrik' in normalized:
            return True
        
        # Check keywords with indicators
        if any(keyword in normalized for keyword in self.LISTRIK_KEYWORDS):
            if any(indicator in normalized for indicator in electrical_indicators):
                return True
        
        return False

    def categorize(self, product_name: str) -> str | None:
        """Categorize a single product name.

        Uses strict priority-based categorization:
        1. Sanitair (highest priority - bathroom fixtures)
        2. Alat Berat (heavy equipment/machinery)
        3. Peralatan Kerja (hand/power tools)
        4. Tanah, Pasir, Batu, Semen (construction bulk materials)
        5. Steel (structural materials)
        6. Interior (finishing materials)
        7. Pipa Air (plumbing)
        8. Listrik (electrical - lowest priority)

        Special override: Electrical conduit/isolasi with explicit electrical context
        overrides Pipa Air/Interior even though they have "pipa"/"isolasi" keywords.

        Returns the first matching category or None.
        """
        if not product_name:
            return None

        normalized = product_name.lower().strip()

        # Override check: Electrical conduit/isolasi with explicit electrical context
        # should be categorized as Listrik, not Pipa Air or Interior
        electrical_override = (
            ('conduit' in normalized and ('elektrik' in normalized or 'listrik' in normalized)) or
            ('isolasi' in normalized and 'listrik' in normalized)
        )

        # Return first match (strict priority)
        # But check electrical override first
        if electrical_override and self._check_listrik(normalized):
            return self.CATEGORY_LISTRIK
        
        if self._check_sanitair(normalized):
            return self.CATEGORY_SANITAIR
        if self._check_alat_berat(normalized):
            return self.CATEGORY_ALAT_BERAT
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
        if self._check_listrik(normalized):
            return self.CATEGORY_LISTRIK
        
        return None

    def categorize_batch(self, product_names: list[str]) -> list[str | None]:
        return [self.categorize(name) for name in product_names]

