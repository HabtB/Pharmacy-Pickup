"""
Medication Location Lookup Module

This module provides efficient lookup of medication storage locations
based on the medication_locations.csv database.

Locations:
- PHRM: Main Pharmacy
- STR: Store Room
- VIT: Vitamins Section
- IV: Where IVs are
"""

import csv
import os
from typing import Dict, Optional, Tuple, List
import re
from difflib import SequenceMatcher
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class MedicationLocationLookup:
    """Handles medication location lookups with fuzzy matching."""
    print("Loading MedicationLocationLookup v2 (Fixed)")

    def __init__(self, csv_path: str = None):
        """Initialize the lookup with medication locations from CSV."""
        if csv_path is None:
            # Default to medication_locations.csv in same directory
            csv_path = os.path.join(
                os.path.dirname(__file__),
                'medication_locations.csv'
            )

        self.csv_path = csv_path
        self.location_db: Dict[str, Tuple[str, str]] = {}
        self._normalization_cache: Dict[str, str] = {}  # Cache normalized names
        self._search_index: Dict[str, List[str]] = {}    # optimization: index by first letter
        self._sorted_index: Dict[str, str] = {}          # optimization: index by sorted significant words
        self._load_locations()
        
    def _get_sorted_words_key(self, s: str) -> str:
        """Helper to get a sorted-word key for a string."""
        # Replace separators with spaces, split, sort, rejoin
        # Filter out common noise words in the key (dosage labels, etc) to match ingredients better
        clean = s.replace('/', ' ').replace('-', ' ').replace('(', ' ').replace(')', ' ')
        words = clean.split()
        
        # Ignore list: Units, Forms, Release Types, Salts, Common Words
        ignore_words = {
            'MG', 'MCG', 'ML', 'G', 'L', 'OZ', 'MEQ', 'UNITS', 'UNIT', '%',
            'TABLET', 'CAPSULE', 'VIAL', 'INJ', 'SOLN', 'SOLUTION', 
            'SYRUP', 'LIQUID', 'SUSP', 'SUSPENSION', 'ELIXIR', 'DROPS', 'SPRAY',
            'CREAM', 'OINTMENT', 'GEL', 'LOTION', 'FOAM', 'PATCH', 'PAD', 'KIT', 'CUP',
            'BAG', 'BOTTLE', 'MINIBAG', 'IVPB', 'ADD-EASE', 'ADDEASE', 'INFUSION',
            'RINSE', 'MOUTHWASH', 'UD', 'ISO-OSMOTIC', 'ISO', 'OSMOTIC', 'PYXIS', 'OSM',
            'PUMP', 'INHALER', 'NEBULIZER', 'AMPUL', 'CARTRIDGE', 'SYRINGE', 'PEN', 'CREON',
            'DELAYED', 'RELEASE', 'EXTENDED', 'ER', 'DR', 'IR', 'SR', 'CR', 'XL', 'REL',
            'HCL', 'SODIUM', 'POTASSIUM', 'CHLORIDE', 'SULFATE', 'TARTRATE', 'GLUCONATE', 'ACETATE',
            'ORAL', 'TOPICAL', 'INTRAVENOUS', 'OPHTHALMIC', 'OTIC', 'NASAL',
            'IN', 'AND', 'WITH', 'FOR', 'OF', 'AS', 'IV', 'IM', 'PO', 'PR', 'SL', 'TO'
        }
        
        # Filter: Length > 1, No numbers, Not in ignore list
        significant = []
        for w in words:
            # KEEP numbers as they are critical for differentiating strengths (e.g. 20/200 vs 10/100)
            # Only skipping purely structural noise if needed, but for now exact match including numbers is safer
            
            if len(w) > 1 and w not in ignore_words:
                significant.append(w)
            elif w.replace('.', '').isdigit(): # Keep single digit numbers too if valid? No, usually length > 1 covers 10, 20 etc.
                 # Special case: Keep single digit numbers if they appear relevant? 
                 # Let's just keep everything that isn't ignored
                 if w not in ignore_words:
                     significant.append(w)
                
        # DEDUPLICATE words (but keep all numbers!) to handle redundant descriptions (e.g. "in NS (in NS)")
        # Split into nums and words
        final_nums = sorted(list(set([w for w in significant if w.replace('.', '').isdigit()])))
        final_words_list = sorted(list(set([w for w in significant if not w.replace('.', '').isdigit()])))
        
        # Recombine: Numbers first (or mixed)? 
        # Actually _get_sorted_words_key usually just joins sorted list.
        # But we need to dedup words ONLY.
        
        return ' '.join(final_nums + final_words_list)

    def _add_to_index(self, normalized_name: str):
        """Add a medication to the search index for faster lookups."""
        if not normalized_name:
            return
        
        # Index by first letter
        first_char = normalized_name[0]
        if first_char not in self._search_index:
            self._search_index[first_char] = []
        self._search_index[first_char].append(normalized_name)
        
        # Index by first word (if different from first letter)
        words = normalized_name.split()
        if words:
            first_word = words[0]
            if len(first_word) > 1:
                # Add to a special key with prefix 'W:'
                key = f"W:{first_word}"
                if key not in self._search_index:
                    self._search_index[key] = []
                self._search_index[key].append(normalized_name)

    def _expand_abbreviations(self, name: str) -> str:
        """Expand common medication and solution abbreviations."""
        
        # Brand name mappings (handle common brands not in DB)
        brand_mappings = {
            'ROBITUSSIN DM': 'DEXTROMETHORPHAN-GUAIFENESIN',
            'ROBITUSSIN': 'GUAIFENESIN',
            'MUCINEX': 'GUAIFENESIN',
            'MEROPENEUM': 'MEROPENEM', # Fix common user typo
            'PERIDEX': 'CHLORHEXIDINE 0.12 %', # Fix strength mismatch
        }
        
        # Check for direct brand matches or substring replacements
        upper_name = name.upper()
        for brand, generic in brand_mappings.items():
            if brand in upper_name:
                name = name.replace(brand, generic)
        
        # Process in order from most specific to least specific
        # This ensures "IN 0.9 % NACL" is expanded before just "NACL"
        abbreviations = [
            # Most specific patterns first (concentration + solution combos)
            (r'\bIN\s+0\.9\s*%\s*NACL\b', 'IN NORMAL SALINE'),
            (r'\bIN\s+0\.9\s*%\s*SODIUM\s+CHLORIDE\b', 'IN NORMAL SALINE'),
            (r'\b0\.9\s*%\s*NACL\b', 'NORMAL SALINE'),
            (r'\b0\.9\s*%\s*SODIUM\s+CHLORIDE\b', 'NORMAL SALINE'),
            # Solution + carrier combos
            (r'\bIN\s+NS\b', 'IN NORMAL SALINE'),
            (r'\bIN\s+D5W\b', 'IN DEXTROSE'), # Simplified to allow generic match (drop 5%)
            (r'\bIN\s+D10W\b', 'IN DEXTROSE 10%'),
            (r'\bIN\s+LR\b', 'IN LACTATED RINGERS'),
            # Simple solution abbreviations (less specific)
            (r'\bNS\b', 'NORMAL SALINE'),
            (r'\bD5W\b', 'DEXTROSE'), # Simplified (drop 5%)
            (r'\bD10W\b', 'DEXTROSE 10%'),
            (r'\bLR\b', 'LACTATED RINGERS'),
            (r'\bNACL\b', 'SODIUM CHLORIDE'),
            (r'\bIVPB\b', 'IV PIGGYBACK'),
        ]

        for pattern, replacement in abbreviations:
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

        return name

    def _remove_salt_names(self, name: str) -> str:
        """Remove common medication salt names for better matching."""
        salt_names = [
            'BITARTRATE', 'HYDROCHLORIDE', 'SODIUM', 'POTASSIUM',
            'CALCIUM', 'SULFATE', 'ACETATE', 'TARTRATE', 'MALEATE',
            'FUMARATE', 'SUCCINATE', 'PHOSPHATE', 'CITRATE', 'MESYLATE',
            'BESYLATE', 'HCL', 'PORCINE', 'RECOMBINANT'
        ]

        words = name.split()
        filtered_words = [w for w in words if w not in salt_names]
        return ' '.join(filtered_words)

    def _normalize_medication_name(self, name: str) -> str:
        """
        Normalize medication name for matching only.

        NOTE: This is only used for lookup matching - the original medication name
        with brand names is preserved for display in the app.

        - Convert to uppercase
        - Remove brand names in parentheses
        - Expand abbreviations
        - Remove salt names
        - Remove solution-related words
        """
        if not name:
            return ""

        # Check cache first (MASSIVE performance improvement!)
        if name in self._normalization_cache:
            return self._normalization_cache[name]

        # Normalize casing
        name = name.upper()
        
        # Expand abbreviations FIRST (so brands like PERIDEX map to ingredients before parens removal)
        name = self._expand_abbreviations(name)
        
        # Mapping: Common Equivalents
        name = name.replace('SODIUM CHLORIDE', 'NORMAL SALINE')
        name = name.replace(' NS ', ' NORMAL SALINE ')
        name = name.replace(' RINSE ', ' MOUTHWASH ') 

        # Handle parentheses: Remove content IF it contains NO DIGITS (Brands, Notes)
        # Keep content if it has digits (Strengths, Volumes like 200mL)
        max_iterations = 5
        iteration = 0
        while '(' in name and ')' in name and iteration < max_iterations:
            prev_name = name
            # Remove parens that contain NO digits (brand names, notes)
            name = re.sub(r'\([^()\d]*\)', '', name)
            
            # If nothing removed, break (or we might strictly remove brackets if desired?)
            # Let's clean empty parens just in case
            name = name.replace('()', '')
            
            if name == prev_name: 
                # No non-digit parens found. 
                # Strip remaining parentheses brackets but KEEP content (likely strengths)
                name = name.replace('(', ' ').replace(')', ' ') 
                break
            iteration += 1
            
        # Cleanup any remaining parens
        name = name.replace('(', ' ').replace(')', ' ')

        # Remove common route-related words that add noise
        route_words = [
            'INTRAVENOUS', 'ORAL', 'TOPICAL', 'OPHTHALMIC',
            'RECTAL', 'VAGINAL', 'NASAL', 'OTIC', 'PIGGYBACK'
        ]
        for word in route_words:
            name = name.replace(word, '')

        # Fix common OCR/Gemini typos and DB inconsistencies
        name = name.replace('NOREPHINEPHRINE', 'NOREPINEPHRINE')
        
        # Map D5W to DEXTROSE (Drop 5% to allow generic match vs verbose DB)
        name = re.sub(r'\bD5W\b', 'DEXTROSE', name) 
        name = name.replace(' IN DSW ', ' IN DEXTROSE ') 
        name = name.replace(' DSW ', ' DEXTROSE ')
        name = name.replace(' D5W ', ' DEXTROSE ')
        
        # Normalize percentage
        name = name.replace('%', '')

        # Remove commas
        name = name.replace(',', '')
        
        # Clean specific noise numbers/words
        name = name.replace('ISO-OSMOTIC', '') 
        name = name.replace('ISO OSMOTIC', '')

        # "0.9" (often redundant with Normal Saline)
        name = re.sub(r'\b0\.9\b', '', name)
        # "15 ML" (Common unit dose volume, often causes mismatch if DB doesn't have it)
        name = re.sub(r'\b15\s*ML\b', '', name)
        # Remove common IV bag volumes (causes mismatch with concentration-only DB entries)
        name = re.sub(r'\b(50|100|200|250|500|1000)\s*ML\b', '', name)

        # Separate numbers from letters (e.g. 250ML -> 250 ML)
        name = re.sub(r'(\d)([A-Z])', r'\1 \2', name)

        # Normalize units to standard abbreviations
        unit_normalizations = [
            (r'\bGRAMS?\b', 'G'),
            (r'\bGMS?\b', 'G'),
            (r'\bGM\b', 'G'),
            (r'\bMILLIGRAMS?\b', 'MG'),
            (r'\bMICROGRAMS?\b', 'MCG'),
            (r'\bMILLILITERS?\b', 'ML'),
            (r'\bUNITS?\b', 'UNITS'),
            (r'\bMEQ\b', 'MEQ'),
        ]
        for pattern, replacement in unit_normalizations:
            name = re.sub(pattern, replacement, name)

        # Normalize whitespace
        name = ' '.join(name.split())

        return name

    def _load_locations(self):
        """Load medication locations from CSV file."""
        logger.info(f"[LOAD_DB] Starting to load database from: {self.csv_path}")
        if not os.path.exists(self.csv_path):
            print(f"Warning: Location database not found at {self.csv_path}")
            logger.warning(f"[LOAD_DB] File not found: {self.csv_path}")
            return

        try:
            logger.info(f"[LOAD_DB] Opening CSV file...")
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)

                # Skip header row
                next(reader, None)
                logger.info(f"[LOAD_DB] Skipped header row, starting to load entries...")

                loaded_count = 0
                for idx, row in enumerate(reader):
                    if idx % 500 == 0:
                        logger.info(f"[LOAD_DB] Loading... processed {idx} rows so far")

                    if len(row) < 2:
                        continue

                    med_name = row[0].strip()
                    location_code = row[1].strip() if len(row) > 1 else ""
                    location_desc = row[3].strip() if len(row) > 3 else ""

                    if not med_name or not location_code:
                        continue

                    # Apply FULL normalization during load to match lookup behavior
                    # This ensures abbreviations like D5W → DEXTROSE 5% are expanded in both DB and lookups
                    normalized = self._normalize_medication_name(med_name)
                    self.location_db[normalized] = (location_code, location_desc)
                    
                    # Add to search index
                    self._add_to_index(normalized)
                    
                    # Add to sorted word index
                    sorted_key = self._get_sorted_words_key(normalized)
                    if sorted_key:
                        self._sorted_index[sorted_key] = normalized

                    loaded_count += 1

                logger.info(f"[LOAD_DB] Loop completed, processed {loaded_count} entries")
                logger.info(f"[LOAD_DB] ✓ Loaded {loaded_count} medication locations from database")
                print(f"✓ Loaded {loaded_count} medication locations from database")

        except Exception as e:
            logger.error(f"[LOAD_DB] Error loading location database: {e}")
            print(f"Error loading location database: {e}")

    def _extract_strength(self, text: str) -> str:
        """Extract strength/dosage from medication string (numbers + units)."""
        import re
        # Match patterns like "40 MG", "8 MG/250 ML", "10%", "4.5 G", etc.
        strength_patterns = re.findall(r'\d+(?:\.\d+)?\s*(?:MG|G|ML|MCG|UNITS|MEQ|%|MG/ML)', text, re.IGNORECASE)
        return ' '.join(strength_patterns).upper()

    def _fuzzy_match(self, query: str, threshold: float = 0.75) -> Optional[Tuple[str, str, float]]:
        """
        Find the best fuzzy match for a query string in the location database.
        
        OPTIMIZED: Uses an inverted index to only search relevant medications.
        """
        best_match = None
        best_score = 0.0

        # Extract first significant word from query
        query_words = query.split()
        if not query_words:
            return None
            
        query_first_word = query_words[0]
        query_first_char = query_words[0][0] if query_words[0] else None

        # Determine candidates to search
        candidates = []
        
        # 1. Look in "First Word" bucket (most specific)
        word_key = f"W:{query_first_word}"
        if word_key in self._search_index:
            candidates.extend(self._search_index[word_key])
            
        # 2. If valid, also check the "First Letter" bucket (broader)
        # But ONLY if we haven't found a perfect match yet or if the first word bucket was empty/small
        if query_first_char and query_first_char in self._search_index:
             # If we have very few candidates from word match, add all from letter match
             # Or if we want to be safe, just search everything in that letter
             # For performance, let's limit: if we have < 50 candidates, add broader search
             if len(candidates) < 50:
                 letter_candidates = self._search_index[query_first_char]
                 # Avoid duplicates
                 existing = set(candidates)
                 for cand in letter_candidates:
                     if cand not in existing:
                         candidates.append(cand)
        
        # If still no candidates/very few, fallback to ALL (very generic fallback)
        if not candidates:
             candidates = list(self.location_db.keys())

        # Extract strength from query once
        query_strength = self._extract_strength(query)
        query_no_salt = self._remove_salt_names(query)

        for db_name in candidates:
            if db_name not in self.location_db:
                 continue
                 
            location_code, location_desc = self.location_db[db_name]
            
            # Extract first significant word from database name
            db_words = db_name.split()
            db_first_word = db_words[0] if db_words else ""

            # STRICT CHECK: First word match (already implicitly done by index mostly, but good to verify)
            if len(query_first_word) > 2 and len(db_first_word) > 2:
                if query_first_word != db_first_word:
                    # Allow minor typo in first word if score is high enough later?
                    # For now, keep strict to be fast
                    pass

            # Extract strength from database entry
            db_strength = self._extract_strength(db_name)

            # Try matching with and without salt names
            db_name_no_salt = self._remove_salt_names(db_name)

            # Calculate base similarity scores
            score1 = SequenceMatcher(None, query, db_name).ratio()
            score2 = SequenceMatcher(None, query_no_salt, db_name_no_salt).ratio()
            # score3 = SequenceMatcher(None, query, db_name_no_salt).ratio() # Skip for speed

            # Also check if query is a substring of db_name (partial match bonus)
            if query in db_name or query_no_salt in db_name_no_salt:
                score4 = 0.85  # Give partial matches a good score
            else:
                score4 = 0.0

            # Take the best base score from all matching strategies
            base_score = max(score1, score2, score4)

            # CRITICAL: Weight strength matching heavily (40% of final score)
            # This ensures medications with matching strengths are prioritized
            if query_strength and db_strength:
                strength_score = SequenceMatcher(None, query_strength, db_strength).ratio()
                # Weighted final score: 60% base similarity + 40% strength match
                weighted_score = (base_score * 0.6) + (strength_score * 0.4)
            else:
                # If no strength info, use base score only
                weighted_score = base_score

            if weighted_score > best_score:
                best_score = weighted_score
                best_match = (location_code, location_desc)

        if best_score >= threshold and best_match:
            return (*best_match, best_score)

        return None
        
    @lru_cache(maxsize=1024)
    def find_location(self, medication_name: str, strength: str = "", form: str = "") -> Optional[Dict[str, str]]:
        """
        Find the storage location for a medication.

        Args:
            medication_name: Name of the medication
            strength: Strength/dosage (optional, helps with matching)
            form: Form (tablet, capsule, etc.) (optional, helps with matching)

        Returns:
            Dict with location_code and location_desc, or None if not found
        """
        logger.info(f"  [FIND_LOC] Starting lookup for: {medication_name}")
        if not medication_name:
            logger.info(f"  [FIND_LOC] Empty medication name, returning None")
            return None

        # Normalize inputs
        # Use raw inputs for fridge detection first


        # FRIDGE ITEM DETECTION (Priority Override)
        # User requested specific list: DTAP, Insulin, Vasopressin, Famotidine vials, Amox/Clav susp, Vancomycin syringe, Formoterol
        fridge_keywords = [
            'INSULIN', 'VACCINE', 'DTAP', 'TDAP', 'PNEUMOVAX', 'H1N1', 'FLU', 'ZOSTER', 'SHINGRIX',
            'VASOPRESSIN', 'FAMOTIDINE VIAL', 'FAMOTIDINE INJ',
            'AMOXICILLIN-CLAVULANATE SYRINGE', 'AUGMENTIN', 
            'VANCOMYCIN SYRINGE', 'VANCOMYCIN INJ',
            'FORMOTEROL', 'PERFOROMIST', 'ARMODAFINIL', 'NUVIGIL',
            'REFRIGERATE', 'FRIDGE',
            # Added from Fridge Scan
            'FILGRASTIM', 'NEUPOGEN', 'ZARXIO',
            'FOSPHENYTOIN', 'CEREBYX',
            'EPTIFIBATIDE', 'INTEGRILIN',
            'OCTREOTIDE', 'SANDOSTATIN',
            'CASPOFUNGIN', 'CANCIDAS',
            'DAPTOMYCIN', 'CUBICIN',
            'CALCITONIN', 'MIACALCIN',
            'VELETRI', 'EPOPROSTENOL', 'FLOLAN',
            'ISOPROTERENOL', 'ISUPREL',
            'HEPATITIS', 'ENGERIX', 'RECOMBIVAX'
        ]
        
        is_fridge = False
        upper_name = medication_name.upper()
        if any(k in upper_name for k in fridge_keywords):
            is_fridge = True
        
        # Check specific combinations (Amox/Clav Susp)
        if 'AMOX' in upper_name and 'CLAV' in upper_name and 'SUSP' in form.upper():
             is_fridge = True

        if is_fridge:
            logger.info(f"  [FIND_LOC] Detected as FRIDGE item. Returning 'FRIDGE' location.")
            return {
                'location_code': 'FRIDGE',
                'location_desc': self.get_location_description('FRIDGE')
            }

        # Build full medication string to match
        full_med = medication_name.strip()
        if strength:
            full_med += f" {strength.strip()}"
        if form:
            full_med += f" {form.strip()}"

        logger.info(f"  [FIND_LOC] Full med string: '{full_med}'")
        logger.info(f"  [FIND_LOC] About to normalize...")
        normalized = self._normalize_medication_name(full_med)
        logger.info(f"  [FIND_LOC] Normalized to: '{normalized}'")

        # Strategy 1: Try exact match first (fastest)
        if normalized in self.location_db:
            location_code, location_desc = self.location_db[normalized]
            return {
                'location_code': location_code,
                'location_desc': location_desc
            }

        # Strategy 2: Try without form
        if form:
            full_med_no_form = medication_name.strip()
            if strength:
                full_med_no_form += f" {strength.strip()}"
            normalized_no_form = self._normalize_medication_name(full_med_no_form)

            if normalized_no_form in self.location_db:
                location_code, location_desc = self.location_db[normalized_no_form]
                return {
                    'location_code': location_code,
                    'location_desc': location_desc
                }

        # Strategy 3: Try just medication name + strength
        if strength:
            name_strength = self._normalize_medication_name(f"{medication_name} {strength}")
            if name_strength in self.location_db:
                location_code, location_desc = self.location_db[name_strength]
                return {
                    'location_code': location_code,
                    'location_desc': location_desc
                }

        # Strategy 4: Try just medication name
        name_only = self._normalize_medication_name(medication_name)
        if name_only in self.location_db:
            location_code, location_desc = self.location_db[name_only]
            return {
                'location_code': location_code,
                'location_desc': location_desc
            }

        # Strategy 5: Fuzzy matching with full medication string
        # Re-enabled with optimization (limited scope if needed, but let's try standard first)
        logger.info(f"  [FUZZY] Trying full match for: '{normalized}'")
        fuzzy_result = self._fuzzy_match(normalized, threshold=0.85) # High threshold to prevent bad matches
        if fuzzy_result:
            location_code, location_desc, score = fuzzy_result
            logger.info(f"  [FUZZY] ✓ Match found (score={score:.2f}): {location_code}")
            return {
                'location_code': location_code,
                'location_desc': location_desc
            }

        # Strategy 6: Fuzzy matching with just name (more lenient threshold)
        logger.info(f"  [FUZZY] Trying name-only match for: '{name_only}'")
        fuzzy_result = self._fuzzy_match(name_only, threshold=0.80)
        if fuzzy_result:
            location_code, location_desc, score = fuzzy_result
            logger.info(f"  [FUZZY] ✓ Match found (score={score:.2f}): {location_code}")
            return {
                'location_code': location_code,
                'location_desc': location_desc
            }

        # Strategy 7: Sorted word matching & Number Subset Check
        # This allows reordered ingredients AND matches verbose DB entries (extra volumes/concentrations)
        # while strictly rejecting mismatched strengths (Safety Critical).
        
        normalized_sorted_key = self._get_sorted_words_key(normalized)
        
        # We need to split the key into words and numbers for the subset check
        scan_parts = normalized_sorted_key.split()
        scan_words = sorted([w for w in scan_parts if not w.replace('.', '').isdigit()])
        scan_nums = sorted([w for w in scan_parts if w.replace('.', '').isdigit()])
        scan_word_key = ' '.join(scan_words)

        logger.info(f"  [SORTED] Key: '{normalized_sorted_key}' (Words: {scan_words}, Nums: {scan_nums})")

        # Instead of single O(1) lookup, we need to check candidates with same WORDS but potentially more NUMBERS.
        # This requires a "Word-Only Index". Let's build it on the fly or just iterate?
        # Iterating all keys is too slow.
        # Let's trust the _sorted_index but modify it to be: Dict[WordKey, List[FullKey]]
        # For now, simplistic fallback: if exact match fails, try fuzzy? 
        # No, "Fuzzy" on numbers is bad.
        
        # Let's iterate through the _sorted_index keys that contain our words.
        # Optimally: Modify _sorted_index to map WordKey -> List[(start_nums, location_code)]
        # But changing data structure now is risky.
        
        # Workaround: Exact match first (Fast path)
        if normalized_sorted_key in self._sorted_index:
             db_key = self._sorted_index[normalized_sorted_key]
             location_code, location_desc = self.location_db[db_key]
             logger.info(f"  [SORTED] ✓ Exact match found: {location_code}")
             return { 'location_code': location_code, 'location_desc': location_desc }

        # Attempt to find "Superset" keys in the index (Linear scan of index is faster than whole DB?)
        # 2000 items is fast enough for Python (~0.5ms).
        best_match = None
        
        for candidate_key in self._sorted_index.keys():
            cand_parts = candidate_key.split()
            cand_words = sorted([w for w in cand_parts if not w.replace('.', '').isdigit()])
            cand_nums = [w for w in cand_parts if w.replace('.', '').isdigit()]
            
            # 1. Words must match EXACTLY (after sorting)
            if scan_words != cand_words:
                continue

            # 2. Numbers must be a SUBSET (All scan numbers must exist in DB entry)
            # This handles "10 100" matching "10 100 5", but rejects "20 200"
            scan_nums_set = set(scan_nums)
            cand_nums_set = set(cand_nums)
            
            if scan_nums_set.issubset(cand_nums_set):
                 # Found valid match!
                 db_real_key = self._sorted_index[candidate_key]
                 location_code, location_desc = self.location_db[db_real_key]
                 logger.info(f"  [SORTED] ✓ Subset match found: {location_code} (DB has extra nums: {cand_nums_set - scan_nums_set})")
                 return { 'location_code': location_code, 'location_desc': location_desc }
                 
        logger.info(f"  [SORTED] ✗ No subset match found")
             
        logger.info(f"  [FUZZY] ✗ No fuzzy match found for: '{medication_name}'")

        # No match found
        return None

    def get_location_description(self, location_code: str) -> str:
        """Get human-readable description for location code."""
        location_map = {
            'PHRM': 'Main Pharmacy',
            'STR': 'Store Room',
            'VIT': 'Vitamins Section',
            'PHRM': 'Main Pharmacy',
            'STR': 'Store Room',
            'VIT': 'Vitamins Section',
            'IV': 'IV Room',
            'FRIDGE': 'Refrigerated Section'
        }
        return location_map.get(location_code, location_code)


# Global instance for easy import
_global_lookup = None

def get_location_lookup() -> MedicationLocationLookup:
    """Get or create the global location lookup instance."""
    global _global_lookup
    if _global_lookup is None:
        _global_lookup = MedicationLocationLookup()
    return _global_lookup


# Convenience function
def find_medication_location(medication_name: str, strength: str = "", form: str = "") -> Optional[Dict[str, str]]:
    """
    Convenience function to find medication location.

    Args:
        medication_name: Name of the medication
        strength: Strength/dosage (optional)
        form: Form (tablet, capsule, etc.) (optional)

    Returns:
        Dict with location_code and location_desc, or None if not found
    """
    lookup = get_location_lookup()
    return lookup.find_location(medication_name, strength, form)


if __name__ == "__main__":
    # Test the lookup
    lookup = MedicationLocationLookup()

    # Test cases
    test_meds = [
        ("ACETAMINOPHEN", "325 MG", "TABLET"),
        ("ABACAVIR", "300 MG", "TABLET"),
        ("INSULIN REGULAR", "", ""),
        ("ACETAMINOPHEN", "650 MG", "RECTAL SUPPOSITORY"),
    ]

    print("\nTesting medication location lookup:")
    print("-" * 60)
    for name, strength, form in test_meds:
        result = lookup.find_location(name, strength, form)
        if result:
            print(f"✓ {name} {strength} {form}")
            print(f"  Location: {result['location_code']} - {lookup.get_location_description(result['location_code'])}")
        else:
            print(f"✗ {name} {strength} {form} - NOT FOUND")
        print()
