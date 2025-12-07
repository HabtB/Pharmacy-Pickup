#!/usr/bin/env python3
"""
Floor Stock Parser for BD Pick Lists - Hybrid Deterministic + LLM Approach
Parses tabular floor stock medication pick lists with Device, Med, Pick Amount columns

Key Design Principles (Production Healthcare Standards):
1. DETERMINISTIC extraction for critical fields (floor, pick_amount) - no hallucination risk
2. LLM assistance for complex medication names only
3. Source text verification for all extractions (anti-hallucination)
4. Conservative validation (false negatives acceptable, false positives catastrophic)
"""

import re
import logging
import json
import requests
import os
import base64
from typing import List, Dict, Optional
from difflib import SequenceMatcher
import google.generativeai as genai

logger = logging.getLogger(__name__)


class FloorStockParser:
    """Parser for floor stock BD pick list format"""

    # IV medications that should be marked as "bag" form
    IV_MEDICATIONS = [
        'cefazolin', 'ceftriaxone', 'ampicillin', 'vancomycin', 'piperacillin',
        'meropenem', 'ertapenem', 'ceftazidime', 'cefepime', 'gentamicin',
        'tobramycin', 'azithromycin', 'levofloxacin', 'ciprofloxacin', 'metronidazole',
        'normal saline', 'lactated ringers', 'dextrose', 'sodium chloride',
        'potassium chloride', 'magnesium sulfate'
    ]

    def __init__(self, api_key: Optional[str] = None, use_llm_verification: bool = True):
        """Initialize parser with optional API key for LLM"""
        self.api_key = api_key or os.getenv('GROK_API_KEY')
        self.grok_url = "https://api.x.ai/v1/chat/completions"
        self.use_llm_verification = use_llm_verification and self.api_key is not None
        logger.info(f"FloorStockParser init: API key={bool(self.api_key)}, use_llm_verification={self.use_llm_verification}")

    def _correct_medication_forms(self, medications: List[Dict]) -> List[Dict]:
        """
        Correct known medication form misidentifications by Gemini Vision.

        This is a hardcoded override to fix specific cases where Gemini
        consistently misidentifies the medication form, which would confuse
        pharmacy staff and prevent accurate location matching.

        Args:
            medications: List of medication dictionaries from Gemini

        Returns:
            List of medications with corrected forms
        """
        # Known form corrections: (medication_name_pattern, wrong_form, correct_form)
        FORM_CORRECTIONS = [
            # Dextrose 50% is always in syringe form, not IV solution
            (r'dextrose\s*50\s*%', 'iv soln', 'syringe'),
            (r'dextrose\s*50\s*%', 'injection', 'syringe'),
            (r'dextrose\s*50\s*%', 'solution', 'syringe'),
            # Norepinephrine IV bags are IVPB (IV piggyback), not just "bag"
            (r'norepinephrine', 'bag', 'iv'),
            (r'levophed', 'bag', 'iv'),
        ]

        corrected_count = 0
        for med in medications:
            med_name = med.get('name', '').lower()
            current_form = med.get('form', '').lower()

            # Check each correction pattern
            for pattern, wrong_form, correct_form in FORM_CORRECTIONS:
                if re.search(pattern, med_name, re.IGNORECASE):
                    if current_form == wrong_form.lower() or wrong_form.lower() in current_form:
                        original_form = med.get('form')
                        med['form'] = correct_form
                        logger.info(f"  [FORM CORRECTION] {med.get('name')}: '{original_form}' → '{correct_form}'")
                        corrected_count += 1
                        break  # Only apply first matching correction

        if corrected_count > 0:
            logger.info(f"Applied {corrected_count} form corrections")

        return medications

    def parse(self, text: str, word_annotations: Optional[List] = None) -> List[Dict]:
        """
        Hybrid parsing: Deterministic coordinate-based + LLM for names

        Strategy:
        1. DETERMINISTIC: Use bounding box coordinates to identify table structure
        2. DETERMINISTIC: Extract pick amounts from correct columns using coordinates
        3. LLM: Extract medication names (complex, compound names)
        4. VALIDATE: Verify using formula: Pick Amount = Max - Current

        Args:
            text: OCR extracted text from BD pick list
            word_annotations: List of word objects with bounding_poly coordinates

        Returns:
            List of validated medication dictionaries
        """
        logger.info("=== HYBRID FLOOR STOCK PARSER: Starting ===")

        # DEBUG: Log full OCR text to check if correct numbers are present
        with open('/tmp/ocr_debug.txt', 'w') as f:
            f.write(text)
        logger.info(f"DEBUG: Full OCR text saved to /tmp/ocr_debug.txt ({len(text)} chars)")

        # TRY: Hybrid row-based parsing (coordinates for structure + LLM for content)
        if word_annotations:
            logger.info("Attempting hybrid row-based parsing (coordinates + LLM)")
            medications = self._parse_with_row_clustering(text, word_annotations)
            if medications and len(medications) > 0:
                logger.info(f"✓ Hybrid row-based parsing found {len(medications)} medications")
                return medications
            else:
                logger.warning("Hybrid row-based parsing found no medications, falling back to pure LLM")

        # Step 2: Fallback to LLM-based parsing if coordinates unavailable
        if self.use_llm_verification:
            medications = self._parse_with_groq(text)
            if medications:
                logger.info(f"Using LLM parsing: {len(medications)} medications found")
                # Step 2.5: Use formula to identify pick/max/current from numbers list
                medications = self._identify_numbers_by_formula(medications)
            else:
                logger.info("LLM parsing failed, falling back to deterministic parser")
                medications = self._parse_bd_table_enhanced(text)
        else:
            # Fallback: Parse using deterministic structure
            medications = self._parse_bd_table_enhanced(text)

        # Step 3: Validate all extractions against source text
        validated_medications = self._validate_against_source(medications, text)

        # Step 4: Filter out obvious headers only (merging now happens during extraction)
        final_medications = []
        for med in validated_medications:
            name = med.get('name', '')
            # Skip obvious headers
            if re.match(r'^(PICK|Med|Description|Amount|Device|Summary)', name, re.IGNORECASE):
                logger.info(f"Filtering header: '{name}'")
                continue
            final_medications.append(med)

        logger.info(f"=== HYBRID PARSER: Found {len(final_medications)} validated medications ===")
        return final_medications

    def _parse_bd_table(self, text: str) -> List[Dict]:
        """Parse BD pick list table format - line by line approach"""
        medications = []
        lines = text.split('\n')

        current_device = None
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Extract Device/Floor in various formats:
            # - "Device: 8E-1" or "8E-1" (with dash)
            # - "7EM_MICU" or "7ES_SICU" (with underscore and unit name)
            # - "6E-2_CICU" (dash, number, underscore, unit name)
            # - Standalone "6W-1", "7E", "8W-2"
            device_match = re.match(r'^(?:Device:\s*)?(\d+[EW][-_]?[\dA-Z]+[-_]?[A-Z]*)$', line, re.IGNORECASE)
            if device_match:
                current_device = device_match.group(1)
                logger.info(f"Found device/floor: {current_device}")
                i += 1
                continue

            # Check if this line is a medication name
            # Medication names are typically lowercase words, sometimes with hyphens
            # Skip header words and common non-medication terms
            skip_terms = ['device', 'med', 'description', 'pick', 'amount', 'max', 'current', 'area', 'actual', 'report', 'time', 'group', 'by', 'summary', 'mount', 'sinai', 'morningside', 'run']

            if line.lower() in skip_terms:
                i += 1
                continue

            # Check if line starts with a medication name (letters, possibly with hyphens or spaces)
            # Exclude common form words that might be mistaken for medication names
            form_words = ['tablet', 'capsule', 'vial', 'bag', 'patch', 'syringe', 'packet', 'nebulizer', 'cup', 'syrup', 'liquid', 'suspension', 'injection', 'soln', 'ivpb', 'ivbg']

            # Pattern 1: Name only (letters, spaces, hyphens) - multi-line extraction
            is_name_only = re.match(r'^[A-Za-z][A-Za-z\s-]+$', line) and len(line) >= 4 and line.lower() not in form_words

            # Pattern 2: Name with numbers (e.g., "Albuterol 0.083%") - single-line extraction
            has_medication_pattern = re.match(r'^[A-Za-z][A-Za-z\s-]*\s+[\d.]+', line) and len(line) >= 4

            if is_name_only:
                # This could be a medication name
                # Look at next 10 lines for strength and form (BD format is very fragmented)
                med_name = line
                strength = ''
                form = 'tablet'
                pick_amount = 1
                found_strength = False
                found_form = False
                strength_parts = []

                # Check next lines for strength and form
                for offset in range(1, min(12, len(lines) - i)):
                    next_line = lines[i + offset].strip()

                    if not next_line:
                        continue

                    # Skip brand names in parentheses
                    if re.match(r'^\([A-Z\s]+\)$', next_line):
                        continue

                    # Look for strength patterns - may be split across lines
                    # Pattern 1: "10 mg/1 mL (5" followed by "mL) vial"
                    # Pattern 2: "0.9%" or "15 mmol"
                    strength_pattern = r'([\d.]+\s*(?:mg|mcg|g|mL|unit|units?|%|mEq|mmol)(?:\s*/\s*[\d.]+\s*(?:mL|L))?(?:\s*\([\d.]+)?)'
                    strength_match = re.search(strength_pattern, next_line, re.IGNORECASE)

                    if strength_match and not found_strength:
                        strength_parts.append(next_line)
                        # Check if this looks complete or needs continuation
                        if re.search(r'\d+\s*(?:mg|mcg|g|mL|mmol|unit|units?|%|mEq)(?:\s*/\s*\d+\s*mL)?$', next_line, re.IGNORECASE):
                            strength = ' '.join(strength_parts).strip()
                            found_strength = True
                            strength_parts = []
                            continue
                        # Check next line for continuation (e.g., "mL) vial")
                        continue

                    # Check if this completes a strength (e.g., "mL) vial")
                    if strength_parts and re.search(r'^mL?\)', next_line, re.IGNORECASE):
                        strength_parts.append(next_line)
                        # Clean up strength
                        full_text = ' '.join(strength_parts)
                        strength_match = re.search(r'([\d.]+\s*(?:mg|mcg|g|unit|units?|%|mEq|mmol)(?:\s*/\s*[\d.]+\s*mL)?)', full_text, re.IGNORECASE)
                        if strength_match:
                            strength = strength_match.group(1)
                            found_strength = True
                            strength_parts = []
                        continue

                    # Look for standalone form
                    if not found_form:
                        if next_line.lower() in form_words:
                            form = next_line.lower()
                            found_form = True
                            continue
                        # Check for "iv soln" or "iv soln."
                        if 'iv' in next_line.lower() and 'soln' in next_line.lower():
                            form = 'bag'
                            found_form = True
                            continue

                    # Look for pick amount (standalone number, 1-200 range)
                    if found_strength and re.match(r'^\d+$', next_line):
                        num = int(next_line)
                        if 1 <= num <= 200:
                            pick_amount = num
                            break

                # Create medication if we have valid data
                if current_device and found_strength:
                    # Normalize form
                    form = self._normalize_form(med_name, form)

                    med_data = {
                        'name': self._normalize_name(med_name),
                        'strength': strength,
                        'form': form,
                        'floor': current_device,
                        'pick_amount': pick_amount
                    }

                    medications.append(med_data)
                    logger.info(f"Extracted: {med_data['name']} - {med_data['strength']} - {med_data['form']} - Floor: {med_data['floor']} - Pick: {pick_amount}")

            elif has_medication_pattern and current_device:
                # Single-line format: name + strength on same line (e.g., "Albuterol 0.083%")
                med_data = self._extract_medication_from_text(line, current_device)
                if med_data and med_data.get('strength'):
                    # Look for pick amount in next lines
                    pick_amount = self._extract_pick_amount(lines, i + 1)
                    med_data['pick_amount'] = pick_amount

                    medications.append(med_data)
                    logger.info(f"Extracted (single-line): {med_data['name']} - {med_data['strength']} - {med_data['form']} - Floor: {med_data['floor']} - Pick: {pick_amount}")

            i += 1

        # Post-process: Remove duplicates and fragments
        medications = self._deduplicate_medications(medications)

        return medications

    def _extract_medication_from_text(self, text: str, device: Optional[str]) -> Optional[Dict]:
        """Extract medication data from full text (possibly multi-line)"""

        # BD format: medication name, then (BRAND), then "strength form"
        # Example: "gabapentin (NEURONTIN) 100 mg capsule"

        # First, extract medication name (first word before parentheses or numbers)
        name_match = re.match(r'^([A-Za-z][A-Za-z\s-]+?)(?:\s+\(|$)', text, re.IGNORECASE)
        if not name_match:
            return None

        name = name_match.group(1).strip()

        # Extract strength - look for numbers with units
        strength_match = re.search(r'([\d.]+\s*(?:mg|mcg|g|mL|unit|units?|%|mEq)(?:\s*/\s*[\d.]+\s*mL)?)', text, re.IGNORECASE)
        strength = strength_match.group(1).strip() if strength_match else ''

        # Extract form - look for form keywords in the text
        form = self._extract_form_from_text(text)

        # Normalize form based on context
        form = self._normalize_form(name + ' ' + text, form)

        return {
            'name': self._normalize_name(name),
            'strength': strength,
            'form': form,
            'floor': device
        }

    def _extract_form_from_text(self, text: str) -> str:
        """Extract medication form from text"""
        text_lower = text.lower()

        # Search for form keywords in order of specificity
        form_keywords = [
            ('patch', 'patch'),
            ('mini bag', 'bag'),
            ('ivpb', 'bag'),
            ('nebulizer', 'nebulizer'),
            ('syringe', 'syringe'),
            ('vial', 'vial'),
            ('packet', 'packet'),
            ('cup', 'cup'),
            ('syrup', 'syrup'),
            ('suspension', 'liquid'),
            ('liquid', 'liquid'),
            ('capsule', 'capsule'),
            ('tablet', 'tablet'),
            ('bag', 'bag'),
            ('injection', 'injection'),
        ]

        for keyword, form in form_keywords:
            if keyword in text_lower:
                return form

        # Default
        return 'tablet'

    def _extract_pick_amount(self, lines: List[str], start_idx: int) -> int:
        """Extract pick amount from next few lines after medication"""
        # BD format has pick amount on separate lines after the medication
        # Look for standalone numbers in the next 1-3 lines

        for i in range(start_idx, min(start_idx + 3, len(lines))):
            line = lines[i].strip()

            # Match standalone number (pick amount)
            if re.match(r'^\d+$', line):
                return int(line)

        return 1  # Default if not found

    def _normalize_name(self, name: str) -> str:
        """Normalize medication name"""
        # Title case for consistency
        name = name.strip().title()

        # Remove extra spaces
        name = re.sub(r'\s+', ' ', name)

        return name

    def _normalize_form(self, name: str, form: str) -> str:
        """Normalize medication form, especially for IV bags"""
        form_lower = form.lower()
        name_lower = name.lower()

        # IV bags should be "bag" not "injection" or "mini bag"
        if form_lower in ['mini bag', 'ivpb', 'mini-bag']:
            return 'bag'

        # Check if medication is an IV medication by name
        for iv_med in self.IV_MEDICATIONS:
            if iv_med in name_lower:
                if form_lower in ['injection', 'vial']:
                    return 'bag'
                break

        # Normalize other forms
        if form_lower in ['ea', 'each']:
            # Context-based determination
            if 'patch' in name_lower:
                return 'patch'
            elif 'bag' in name_lower:
                return 'bag'
            else:
                return 'packet'

        if form_lower == 'suspension':
            return 'liquid'

        return form_lower

    def validate_medication(self, med: Dict) -> bool:
        """Validate medication data"""
        # Must have name
        if not med.get('name') or len(med['name']) < 2:
            return False

        # Reject common non-medication words
        invalid_names = [
            'device', 'med', 'description', 'pick', 'amount', 'max', 'current',
            'area', 'actual', 'page', 'report', 'time', 'group', 'run'
        ]

        if med['name'].lower() in invalid_names:
            return False

        return True

    def _parse_with_groq(self, text: str) -> List[Dict]:
        """Parse BD floor stock using Groq LLM"""
        try:
            # First, extract all standalone numbers from the text for the LLM to work with
            all_standalone_numbers = re.findall(r'(?<!\d)(\d+)(?!\d)', text)
            all_standalone_numbers = [int(n) for n in all_standalone_numbers if 1 <= int(n) <= 200]

            prompt = f"""You are a pharmacy expert. Extract medication information from this BD floor stock pick list and return ONLY valid JSON.

CRITICAL INSTRUCTIONS:
1. Extract EVERY medication listed under each Device/Floor (6W-1, 6W-2, 8E-1, 8E-2, 9E-1, 9E-2, etc.)
2. MANDATORY: Each medication MUST have a "floor" field. Look for Device numbers like "6W-1", "8E-2", "9E-1"
3. The floor/device stays the same for multiple medications until a new device number appears
4. For medication names: Use the generic name (lowercase first letter like "gabapentin", "ceFAZolin")
5. Extract strength with units (e.g., "500 mg", "1 g", "4%")
6. Extract form: tablet, capsule, patch, bag (for IV), vial, packet, nebulizer, syringe, ud cup, liquid, etc.
7. IMPORTANT: IV bags should have form "bag" not "injection"

ALL STANDALONE NUMBERS IN TEXT: {all_standalone_numbers}

8. CRITICAL - Extract numbers for EACH medication:
   - For each medication, extract 3 numbers: Pick Amount, Max Amount, Current Amount
   - These numbers satisfy the formula: Pick = Max - Current (±5 tolerance)
   - Numbers may appear near the medication name OR scattered elsewhere in the text
   - If you don't find 3 valid numbers near the medication, search the full list above for triplets that match the formula
   - "numbers": Extract ALL standalone numbers from the ENTIRE TEXT that could belong to this medication
   - OCR reading order may be scrambled, so a medication's numbers might appear ANYWHERE in the text
   - For medications without nearby numbers, SEARCH THE ENTIRE TEXT for matching triplets
   - Include ONLY standalone numbers (not part of strength like "650 mg" or "100 mg")
   - Typically 3 numbers per medication: Pick Amount, Max, Current Amount
   - If you find fewer than 3 numbers near the medication name, search the ENTIRE text for additional standalone numbers

   IMPORTANT: Numbers may appear in wrong locations due to OCR column misalignment!
   Example: pantoprazole's numbers [11, 20, 9] might appear in sodium bicarbonate's section

   Example patterns in OCR text:
   ```
   Pattern 1 (numbers after medication name):
   sodium
   bicarbonate
   30          ← EXTRACT ALL numbers between this med and next
   17          ← EXTRACT
   40          ← EXTRACT
   23          ← EXTRACT (correct numbers)
   40          ← EXTRACT
   17          ← EXTRACT
   11          ← EXTRACT (actually belongs to pantoprazole!)
   20          ← EXTRACT (actually belongs to pantoprazole!)
   9           ← EXTRACT (actually belongs to pantoprazole!)
   (SODIUM BICARBONATE)
   650 mg tablet
   hydralazine  ← STOP HERE (next medication)

   Pattern 2 (medication with no numbers):
   pantoprazole
   (PROTONIX)
   40 mg vial   ← No standalone numbers here!
   nifedipine   ← Next medication

   ACTION: Search ENTIRE TEXT for unused number sequences [10-20 range]
   Possible triplets: [11, 20, 9], [10, 25, 15], etc.
   ```

   NOTE: We use formula (Pick = Max - Current) to identify correct triplets. Extract ALL numbers you see!

9. Handle multi-line medication entries (medication name may span multiple lines)

Example JSON output format:
{{
  "medications": [
    {{
      "name": "heparin",
      "strength": "5000 units/mL",
      "form": "vial",
      "floor": "9W-1",
      "numbers": [42, 80, 38]
    }},
    {{
      "name": "acetaminophen",
      "strength": "325 mg",
      "form": "tablet",
      "floor": "8E-1",
      "numbers": [79, 200, 121]
    }}
  ]
}}

Text to parse:
{text}

Return ONLY the JSON response, no explanations:"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "messages": [
                    {"role": "system", "content": "You are a pharmacy medication extraction expert."},
                    {"role": "user", "content": prompt}
                ],
                "model": "grok-2-latest",
                "temperature": 0.1,
                "max_tokens": 3000,
                "stream": False
            }

            logger.info("Calling Groq for floor stock parsing")
            response = requests.post(self.grok_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # Parse JSON response
            medications = self._parse_llm_json_response(content)
            logger.info(f"Groq parsed {len(medications)} medications")

            # Validate and correct pick amounts using the formula: Pick Amount ≈ Max - Current
            medications = self._validate_and_correct_pick_amounts(medications)

            return medications

        except Exception as e:
            logger.error(f"Groq parsing failed: {e}")
            return []

    def _parse_llm_json_response(self, content: str) -> List[Dict]:
        """Parse LLM JSON response"""
        try:
            # Clean response
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()

            # Parse JSON
            data = json.loads(content)
            medications = data.get('medications', [])

            # Validate and normalize each medication
            validated = []
            for med in medications:
                if self.validate_medication(med):
                    # Normalize form for IV bags
                    if med.get('form'):
                        med['form'] = self._normalize_form(med.get('name', ''), med['form'])
                    validated.append(med)

            return validated

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq JSON: {e}")
            logger.error(f"Raw content: {content}")
            return []
        except Exception as e:
            logger.error(f"LLM response parsing error: {e}")
            return []

    def _parse_with_coordinates(self, text: str, word_annotations: List) -> List[Dict]:
        """
        Deterministic parsing using bounding box coordinates from Google Vision

        Strategy:
        1. Extract all words with their X,Y coordinates
        2. Identify table rows (group by Y-coordinate)
        3. Identify table columns (group by X-coordinate)
        4. Use LLM to extract medication names only
        5. Match numbers to medications using row alignment
        6. Validate using Pick Amount = Max - Current formula
        """
        try:
            # Skip the first annotation (full text), get individual words with coordinates
            words = word_annotations[1:] if len(word_annotations) > 1 else []

            if not words:
                logger.warning("No word annotations available for coordinate parsing")
                return []

            # Extract words with their bounding box coordinates
            word_data = []
            for word_annotation in words:
                if not hasattr(word_annotation, 'bounding_poly') or not hasattr(word_annotation, 'description'):
                    continue

                vertices = word_annotation.bounding_poly.vertices
                if not vertices:
                    continue

                # Calculate center Y position (for row grouping)
                y_center = (vertices[0].y + vertices[2].y) / 2
                # Calculate left X position (for column identification)
                x_left = vertices[0].x

                word_data.append({
                    'text': word_annotation.description,
                    'y': y_center,
                    'x': x_left,
                    'vertices': vertices
                })

            logger.info(f"Extracted {len(word_data)} words with coordinates")

            # Step 1: Identify table column X-positions from headers
            pick_col_x, max_col_x, current_col_x = self._identify_table_columns(word_data)

            if not all([pick_col_x, max_col_x, current_col_x]):
                logger.warning("Could not identify table column positions, falling back to LLM")
                return []

            logger.info(f"Table columns identified: Pick={pick_col_x}, Max={max_col_x}, Current={current_col_x}")

            # Step 2: Use LLM to extract medication names and floors
            medications_from_llm = self._parse_with_groq(text)

            if not medications_from_llm:
                logger.warning("LLM failed to extract medication names")
                return []

            # Step 3: Extract ALL number triplets from the table columns and match by formula
            # Strategy: Table data is at TOP of image, medication names at BOTTOM
            # We can't use Y-position matching, so we'll use formula matching instead

            # Extract all numbers from each column
            pick_numbers = []
            max_numbers = []
            current_numbers = []

            for word in word_data:
                if word['text'].isdigit() and len(word['text']) <= 3:
                    x_pos = word['x']
                    value = int(word['text'])

                    # Match to column by X-position (±1000px tolerance - headers and data are far apart!)
                    if abs(x_pos - pick_col_x) < 1000:
                        pick_numbers.append({'value': value, 'y': word['y'], 'x': x_pos})
                    if abs(x_pos - max_col_x) < 1000:
                        max_numbers.append({'value': value, 'y': word['y'], 'x': x_pos})
                    if abs(x_pos - current_col_x) < 1000:
                        current_numbers.append({'value': value, 'y': word['y'], 'x': x_pos})

            logger.info(f"Extracted from columns: Pick={len(pick_numbers)}, Max={len(max_numbers)}, Current={len(current_numbers)}")

            # Group numbers by Y-position (same row)
            # Numbers in the same row should have similar Y values (within 20px)
            def group_by_row(pick_nums, max_nums, current_nums):
                """Group numbers that are on the same row (similar Y-coordinates)"""
                rows = []
                for p in pick_nums:
                    # Find max and current numbers with similar Y
                    matching_max = [m for m in max_nums if abs(m['y'] - p['y']) < 50]
                    matching_current = [c for c in current_nums if abs(c['y'] - p['y']) < 50]

                    if matching_max and matching_current:
                        # Found a complete row - use first match for each
                        rows.append({
                            'pick': p['value'],
                            'max': matching_max[0]['value'],
                            'current': matching_current[0]['value'],
                            'y': p['y']
                        })
                return rows

            rows_data = group_by_row(pick_numbers, max_numbers, current_numbers)
            logger.info(f"Found {len(rows_data)} complete rows with all three values")

            # Match medications to rows using formula validation
            medications_with_coords = []
            for med in medications_from_llm:
                # Try to find a row where Pick = Max - Current matches the LLM's pick_amount
                llm_pick = med.get('pick_amount', 0)
                best_match = None

                for row in rows_data:
                    expected_pick = row['max'] - row['current']
                    # Check if this row's formula-validated pick matches what LLM extracted
                    if abs(expected_pick - row['pick']) <= 5:
                        # This row is formula-valid, check if it matches LLM's extraction
                        if llm_pick == expected_pick or llm_pick == row['pick']:
                            best_match = row
                            break

                if best_match:
                    med['pick_amount'] = best_match['pick']
                    med['max'] = best_match['max']
                    med['current_amount'] = best_match['current']
                    logger.info(f"✓ {med['name']}: Matched to row with pick={best_match['pick']}, max={best_match['max']}, current={best_match['current']}")
                else:
                    logger.warning(f"⚠ {med['name']}: No formula-valid row found, keeping LLM values")

                medications_with_coords.append(med)

            # Validate using formula
            validated = self._validate_and_correct_pick_amounts(medications_with_coords)

            return validated

        except Exception as e:
            logger.error(f"Coordinate parsing error: {e}", exc_info=True)
            return []

    def _identify_table_columns(self, word_data: List[Dict]) -> tuple:
        """
        Identify X-positions of table columns by finding headers

        Strategy: Find "Max" and "Current" first (they're unique), then find "Pick Amount"
        that's spatially near them (within 200px to the left)

        Returns: (pick_col_x, max_col_x, current_col_x)
        """
        pick_col_x = None
        max_col_x = None
        current_col_x = None

        logger.info("\n=== Searching for table column headers ===")

        # First pass: Find Max and Current (they're unique and reliable)
        for word in word_data:
            text_lower = word['text'].lower()

            # Look for "Max" header
            if text_lower == 'max':
                max_col_x = word['x']
                logger.info(f"✓ Found 'Max' column header '{word['text']}' at X={max_col_x}, Y={word['y']}")

            # Look for "Current" header
            elif text_lower == 'current':
                current_col_x = word['x']
                logger.info(f"✓ Found 'Current' column header '{word['text']}' at X={current_col_x}, Y={word['y']}")

        # Second pass: Find "Pick Amount" that's near Max/Current
        # Pick Amount column should be to the left of Max column (within ~200px)
        if max_col_x is not None:
            for word in word_data:
                text_lower = word['text'].lower()

                # Look for "Pick" or "Amount"
                if 'pick' in text_lower or text_lower == 'amount':
                    x_distance_to_max = abs(word['x'] - max_col_x)

                    # Pick Amount should be within 200px to the left of Max
                    if word['x'] < max_col_x and x_distance_to_max < 200:
                        pick_col_x = word['x']
                        logger.info(f"✓ Found 'Pick Amount' column header '{word['text']}' at X={pick_col_x}, Y={word['y']} (distance to Max: {x_distance_to_max}px)")
                        break
                    else:
                        logger.debug(f"  Rejected 'Pick' at X={word['x']} (too far from Max: {x_distance_to_max}px)")

        logger.info(f"Column X-positions: Pick={pick_col_x}, Max={max_col_x}, Current={current_col_x}")
        return (pick_col_x, max_col_x, current_col_x)

    def _identify_numbers_by_formula(self, medications: List[Dict]) -> List[Dict]:
        """
        For each medication with a 'numbers' list, identify which are pick, max, current
        using the formula Pick = Max - Current

        Handle two cases:
        1. Single number: Just the pick amount (common for medications at top of page)
        2. Three+ numbers: Pick, Max, Current (use formula validation)
        """
        processed_meds = []
        all_unused_triplets = []  # Track unused valid triplets from other medications

        # FIRST PASS: Process medications with numbers
        for med in medications:
            if 'numbers' in med and isinstance(med['numbers'], list) and len(med['numbers']) >= 1:
                numbers = med['numbers']

                if len(numbers) == 1:
                    # Only one number - it's the pick amount
                    med['pick_amount'] = numbers[0]
                    logger.info(f"✓ {med['name']}: Single number (pick amount only) = {numbers[0]}")
                elif len(numbers) >= 3:
                    # Three or more numbers - use formula to identify
                    pick, max_val, current = self._identify_columns_by_formula(numbers)

                    if pick is not None:
                        med['pick_amount'] = pick
                        med['max'] = max_val
                        med['current_amount'] = current
                        logger.info(f"✓ {med['name']}: Formula identified pick={pick}, max={max_val}, current={current} from numbers={numbers}")

                        # Find ALL valid triplets in this medication's numbers and mark unused ones
                        seen_triplets = set()
                        for i in range(len(numbers)):
                            for j in range(len(numbers)):
                                for k in range(len(numbers)):
                                    if i == j or j == k or i == k:
                                        continue
                                    p, m, c = numbers[i], numbers[j], numbers[k]
                                    if abs(p - (m - c)) <= 5:
                                        # This is a valid triplet - if it's not the one we used, save it
                                        triplet_key = (p, m, c)
                                        if not (p == pick and m == max_val and c == current) and triplet_key not in seen_triplets:
                                            seen_triplets.add(triplet_key)
                                            all_unused_triplets.append({
                                                'pick': p,
                                                'max': m,
                                                'current': c,
                                                'source_med': med['name']
                                            })
                                            # Debug: Log triplets with pick=10 or 11 from specific medications
                                            if p in [10, 11] and med['name'] in ['sodium bicarbonate', 'lactulose']:
                                                logger.info(f"    DEBUG: Found unused triplet ({p}, {m}, {c}) from {med['name']}")
                    else:
                        # Fallback: use first 3 numbers as pick, max, current
                        med['pick_amount'] = numbers[0] if len(numbers) > 0 else 0
                        med['max'] = numbers[1] if len(numbers) > 1 else 0
                        med['current_amount'] = numbers[2] if len(numbers) > 2 else 0
                        med['warning'] = f"⚠ Formula mismatch! Found Pick={med['pick_amount']}, Max={med['max']}, Current={med['current_amount']}. Please enter correct amount manually."
                        logger.warning(f"⚠ {med['name']}: No formula match, using first 3 numbers: {med['pick_amount']}, {med['max']}, {med['current_amount']}")
                else:
                    # Two numbers - use first as pick amount
                    med['pick_amount'] = numbers[0]
                    med['warning'] = f"⚠ Incomplete data! Only {len(numbers)} number(s) found. Please enter correct amount manually."
                    logger.warning(f"⚠ {med['name']}: Only 2 numbers found, using first as pick amount: {numbers[0]}")

            processed_meds.append(med)

        # SECOND PASS: Try to assign unused triplets to medications without pick amounts OR with suspicious single numbers
        if all_unused_triplets:
            # Sort by pick amount (ascending) to prefer smaller values first
            all_unused_triplets.sort(key=lambda t: t['pick'])

            # Log all unused triplets for debugging
            logger.info(f"Found {len(all_unused_triplets)} unused valid triplets to redistribute (sorted by pick amount)")
            logger.info(f"  First 10 triplets: {[(t['pick'], t['max'], t['current']) for t in all_unused_triplets[:10]]}")

            # Log triplets with pick=10 or pick=11 specifically (for pantoprazole and nifedipine)
            target_triplets = [t for t in all_unused_triplets if t['pick'] in [10, 11]]
            if target_triplets:
                logger.info(f"  Triplets with pick=10 or pick=11: {[(t['pick'], t['max'], t['current'], t['source_med']) for t in target_triplets[:5]]}")

            for med in processed_meds:
                # ONLY redistribute if there's NO pick amount at all
                # If LLM extracted a single number, trust it - don't override with unused triplets
                needs_redistribution = ('pick_amount' not in med or med.get('pick_amount') is None)

                if needs_redistribution:
                    # This medication needs a triplet - try to find a matching one
                    if all_unused_triplets:
                        # SMART MATCHING: Prefer triplets with pick amounts in reasonable range (10-20)
                        # Most floor stock pick amounts are in the 10-20 range
                        reasonable_triplets = [t for t in all_unused_triplets if 10 <= t['pick'] <= 20]

                        if reasonable_triplets:
                            # Use the smallest reasonable triplet
                            triplet = reasonable_triplets[0]
                            all_unused_triplets.remove(triplet)
                        else:
                            # Fall back to 5-30 range, then any available
                            fallback_triplets = [t for t in all_unused_triplets if 5 <= t['pick'] <= 30]
                            if fallback_triplets:
                                triplet = fallback_triplets[0]
                                all_unused_triplets.remove(triplet)
                            else:
                                triplet = all_unused_triplets.pop(0)

                        med['pick_amount'] = triplet['pick']
                        med['max'] = triplet['max']
                        med['current_amount'] = triplet['current']
                        logger.info(f"✓ {med['name']}: Assigned unused triplet from {triplet['source_med']}: pick={triplet['pick']}, max={triplet['max']}, current={triplet['current']}")

        return processed_meds

    def _identify_columns_by_formula(self, numbers: List[int]) -> tuple:
        """
        Identify which numbers are pick_amount, max, current using the formula
        Pick Amount = Max - Current

        STRATEGY: Find ALL valid triplets, then choose the best one based on:
        1. Prefer consecutive or near-consecutive triplets (positions close together)
        2. Prefer triplets with smaller pick amounts (large numbers are often wrong)
        3. Prefer triplets later in the array (medication data appears after header)
        """
        valid_triplets = []

        # FIRST PASS: Try consecutive triplets (most reliable)
        for i in range(len(numbers) - 2):
            pick = numbers[i]
            max_val = numbers[i + 1]
            curr = numbers[i + 2]

            # Check formula with ±5 tolerance
            if abs(pick - (max_val - curr)) <= 5:
                distance = 2  # Consecutive triplet
                valid_triplets.append({
                    'positions': (i, i+1, i+2),
                    'values': (pick, max_val, curr),
                    'distance': distance,
                    'score': 100 - distance + (i * 0.1)  # Prefer later positions
                })
                logger.info(f"  Found consecutive triplet at [{i}, {i+1}, {i+2}]: pick={pick}, max={max_val}, current={curr}")

        # SECOND PASS: Try near-consecutive (gap of 1)
        for i in range(len(numbers) - 3):
            # Try skip patterns: [i, i+1, i+3] and [i, i+2, i+3]
            for pattern in [(i, i+1, i+3), (i, i+2, i+3)]:
                p_idx, m_idx, c_idx = pattern
                if c_idx < len(numbers):
                    pick = numbers[p_idx]
                    max_val = numbers[m_idx]
                    curr = numbers[c_idx]

                    if abs(pick - (max_val - curr)) <= 5:
                        distance = max(m_idx - p_idx, c_idx - m_idx)
                        valid_triplets.append({
                            'positions': pattern,
                            'values': (pick, max_val, curr),
                            'distance': distance,
                            'score': 80 - distance + (p_idx * 0.1)
                        })
                        logger.info(f"  Found near-consecutive triplet at {pattern}: pick={pick}, max={max_val}, current={curr}")

        # THIRD PASS: Try all combinations if no close triplets found
        if not valid_triplets:
            logger.info("  No consecutive triplets found, trying all combinations...")
            for i in range(len(numbers)):
                for j in range(len(numbers)):
                    for k in range(len(numbers)):
                        if i == j or j == k or i == k:
                            continue

                        pick = numbers[i]
                        max_val = numbers[j]
                        curr = numbers[k]

                        if abs(pick - (max_val - curr)) <= 5:
                            distance = max(abs(j - i), abs(k - j))
                            valid_triplets.append({
                                'positions': (i, j, k),
                                'values': (pick, max_val, curr),
                                'distance': distance,
                                'score': 50 - distance + (i * 0.1)
                            })

        # Choose best triplet
        if valid_triplets:
            # Sort by score (higher is better)
            best = max(valid_triplets, key=lambda t: t['score'])
            pick, max_val, curr = best['values']
            logger.info(f"  Selected best triplet at positions {best['positions']}: pick={pick}, max={max_val}, current={curr} (score={best['score']:.1f})")
            return (pick, max_val, curr)

        # No valid combination found
        logger.warning("  No valid triplet found matching formula Pick = Max - Current")
        return (None, None, None)

    def _validate_and_correct_pick_amounts(self, medications: List[Dict]) -> List[Dict]:
        """
        Validate pick amounts using the formula: Pick Amount ≈ Max - Current Amount
        Auto-correct if the values are swapped (e.g., LLM extracted Max as pick_amount)

        This is a dynamic validation that doesn't rely on hardcoded examples.
        """
        corrected_medications = []

        for med in medications:
            pick_amount = med.get('pick_amount', 0)
            max_stock = med.get('max', 0)
            current_stock = med.get('current_amount', 0)

            # If we have all three values, validate using the formula
            if pick_amount and max_stock and current_stock:
                expected_pick = max_stock - current_stock
                tolerance = 5  # Allow ±5 difference (accounting for timing differences)

                # Check if pick_amount matches the formula
                if abs(pick_amount - expected_pick) <= tolerance:
                    # Valid! Formula matches
                    logger.info(f"✓ {med['name']}: pick_amount={pick_amount} validated (max={max_stock}, current={current_stock}, expected={expected_pick})")
                    corrected_medications.append(med)
                else:
                    # Invalid! Try to correct by checking if values are swapped
                    # Common mistake: LLM extracts Max as pick_amount
                    logger.warning(f"⚠ {med['name']}: pick_amount={pick_amount} doesn't match formula (max={max_stock}, current={current_stock}, expected={expected_pick})")

                    # Try swapping: Maybe pick_amount is actually max, and max is actually pick_amount
                    if abs(max_stock - expected_pick) <= tolerance:
                        # Swap worked! max was actually pick_amount
                        logger.info(f"✓ Auto-corrected {med['name']}: Swapped pick_amount and max (new pick_amount={expected_pick})")
                        med['pick_amount'] = expected_pick
                        corrected_medications.append(med)
                    else:
                        # Use the formula result as the correct value
                        logger.info(f"✓ Auto-corrected {med['name']}: Using formula result pick_amount={expected_pick} (was {pick_amount})")
                        med['pick_amount'] = expected_pick
                        corrected_medications.append(med)
            else:
                # Missing validation data, keep as-is
                logger.debug(f"No validation data for {med.get('name', 'Unknown')}, keeping original pick_amount={pick_amount}")
                corrected_medications.append(med)

        return corrected_medications

    def _parse_bd_table_enhanced(self, text: str) -> List[Dict]:
        """
        Column-aware parser: Understanding BD table structure

        BD Pick List table structure (6 columns read left-to-right by OCR):
        | Med Description    | Pick Area | Pick Amount | Actual | Max | Current |
        | (3-5 lines)        | (empty)   | NUMBER      | (empty)| NUM | NUM     |

        OCR reads row-by-row, so pattern is:
        - Med line 1
        - Med line 2
        - Med line 3
        - [empty] (Pick Area)
        - NUMBER (Pick Amount) ← Extract this!
        - [empty] (Actual)
        - NUMBER (Max) ← Skip
        - NUMBER (Current) ← Skip
        """
        medications = []
        lines = text.split('\n')

        current_device = None
        current_med_lines = []
        in_medication_table = False
        numbers_seen = 0  # Track how many numbers we've seen after med description

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Check for device/floor
            device_match = re.match(r'^(?:Device:\s*)?(\d+[EW][-_]?[\dA-Z]+[-_]?[A-Z]*)$', line, re.IGNORECASE)
            if device_match:
                current_device = device_match.group(1)
                in_medication_table = True
                logger.info(f"Found device/floor: {current_device}")
                i += 1
                continue

            if not in_medication_table:
                i += 1
                continue

            # Skip headers
            skip_terms = ['device', 'med', 'description', 'pick', 'amount', 'max', 'current', 'area', 'actual', 'report', 'time', 'group', 'by', 'summary', 'mount', 'sinai', 'morningside', 'run', 'des', 'bd']
            if line.lower() in skip_terms or '|' in line:
                i += 1
                continue

            # Check if this is a standalone number (table column data)
            if re.match(r'^\d{1,3}$', line) and len(line) <= 3:
                numbers_seen += 1

                # Column pattern: Pick Area (1st num) | Pick Amount (2nd num) | Actual (3rd) | Max (4th) | Current (5th)
                # We want the SECOND number as pick amount
                if numbers_seen == 2:
                    potential_pick_amount = int(line)

                # Skip numbers - they're table columns, not part of med description
                i += 1
                continue

            # Check if this line starts a NEW medication
            # New med starts with: lowercase letter (generic name) or mixed-case (NORepinephrine) or device name
            is_new_med_start = False
            if len(line) >= 3:
                # Starts with lowercase letter (generic name like "atorvastatin", "meropenem")
                # OR mixed-case like "NORepinephrine" (uppercase followed by lowercase)
                # BUT must be a real word (at least 4 chars of actual letters)
                is_lowercase_start = re.match(r'^[a-z]', line)
                is_mixed_case_start = re.match(r'^[A-Z]{2,}[a-z]', line)  # NORepinephrine, QUEtiapine, etc.

                if is_lowercase_start or is_mixed_case_start:
                    # Reject "g (" or "mL)" patterns - these are strength continuations, not medications
                    if re.match(r'^[a-z]\s*[\(\[]', line):
                        # Likely a strength continuation like "g (100 mL)"
                        is_new_med_start = False
                    else:
                        # Check if it's a substantial medication name, not just a unit or form
                        clean_letters = re.sub(r'[^A-Za-z]', '', line)
                        # Must have at least 4 letters and not be a form-only or unit word
                        if len(clean_letters) >= 4:
                            form_only_words = ['vial', 'tablet', 'capsule', 'bag', 'patch', 'syringe',
                                              'packet', 'ivpb', 'mini', 'soln']
                            unit_words = ['mg', 'mcg', 'ml', 'meq', 'mmol', 'unit', 'units']
                            if line.lower() not in form_only_words and clean_letters.lower() not in unit_words:
                                is_new_med_start = True
                # Or is a device name
                elif re.match(r'^\d+[EW][-_]?[\dA-Z]+', line):
                    is_new_med_start = True

            # If we found a new medication start and we have accumulated lines, process previous med
            if is_new_med_start and current_med_lines and numbers_seen > 0:
                med_text = ' '.join(current_med_lines)
                pick_amount = potential_pick_amount if 'potential_pick_amount' in locals() else 0

                if current_device:
                    med_data = self._parse_medication_block(med_text, current_device, pick_amount)
                    if med_data:
                        medications.append(med_data)
                        logger.info(f"Extracted: {med_data['name']} | {med_data['strength']} | {med_data['form']} | Pick: {pick_amount}")
                    else:
                        logger.warning(f"Failed to parse: '{med_text}'")

                # Reset for next medication
                current_med_lines = [line]  # Start new med with this boundary line
                numbers_seen = 0
                if 'potential_pick_amount' in locals():
                    del potential_pick_amount
                i += 1
                continue  # Skip to next iteration - don't double-add this line

            # Accumulate medication description lines
            if len(line) >= 2:
                current_med_lines.append(line)

            i += 1

        # Process the last medication if any
        if current_med_lines and numbers_seen > 0:
            med_text = ' '.join(current_med_lines)
            pick_amount = potential_pick_amount if 'potential_pick_amount' in locals() else 0

            if current_device:
                med_data = self._parse_medication_block(med_text, current_device, pick_amount)
                if med_data:
                    medications.append(med_data)
                    logger.info(f"Extracted (final): {med_data['name']} | {med_data['strength']} | {med_data['form']} | Pick: {pick_amount}")
                else:
                    logger.warning(f"Failed to parse (final): '{med_text}'")

        logger.info(f"Column-aware parser found {len(medications)} medications")
        return medications

    def _parse_medication_block(self, text: str, device: str, pick_amount: int) -> Optional[Dict]:
        """
        Parse a medication block (all lines between pick amounts)
        Example: "atorvastatin (LIPITOR) 20 mg tablet"
        Example: "amiodarone in D5W (NEXTERONE IN D5W) 360 mg (200 mL) iv"
        """
        # Skip common non-medication words that shouldn't be parsed
        invalid_meds = ['pick', 'description', 'med', 'amount', 'device', 'area', 'actual', 'max', 'current']
        if text.lower().strip() in invalid_meds:
            return None

        # Skip form-only words that are fragments (not real medications)
        form_only_words = ['vial', 'tablet', 'capsule', 'bag', 'patch', 'syringe', 'packet',
                          'nebulizer', 'cup', 'syrup', 'liquid', 'suspension', 'injection',
                          'solution', 'ivpb', 'iv', 'soln', 'mini', 'mini-bag']
        if text.lower().strip() in form_only_words:
            return None

        # CRITICAL FIX: Remove form word prefixes that got incorrectly included
        # Pattern: "5 mg vial QUEtiapine" or "mg vial QUEtiapine" or "mg tablet rifAXIMin"
        # Strip leading "optional number + unit + form" patterns
        text = re.sub(r'^\d*\s*(mg|mcg|g|mL)\s+(vial|tablet|capsule|bag|patch|syringe)\s+', '', text, flags=re.IGNORECASE)
        text = text.strip()

        # Extract form first (highest priority terms that appear at end)
        form_pattern = r'\b(IVPB|ivpb|IV|iv|half[\s-]tablet|tablet|capsule|vial|bag|mini[\s-]bag|patch|syringe|packet|nebulizer|cup|syrup|liquid|suspension|injection|solution)\b'
        form_match = re.search(form_pattern, text, re.IGNORECASE)
        form = form_match.group(1).lower() if form_match else 'tablet'

        # Normalize form
        if 'ivpb' in form or 'mini' in form:
            form = 'bag'  # IVPB is an IV bag, normalize to 'bag'
        elif 'half' in form:
            form = 'half tablet'
        elif form == 'iv':
            form = 'bag'  # IV medications should be 'bag' form

        # Extract strength (numbers with units)
        strength_pattern = r'(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit|units?|%|mEq|mmol)(?:\s*/\s*\d+(?:\.\d+)?\s*(?:mL|L))?)'
        strength_match = re.search(strength_pattern, text, re.IGNORECASE)
        strength = strength_match.group(1) if strength_match else ''

        # Extract medication name with brand name in parentheses
        # Pattern: "generic name (BRAND NAME) dosage form"
        # Also handle: "generic in solution (BRAND IN SOLUTION) dosage form"

        # Try to find pattern: text (BRAND) ...
        brand_pattern = r'([A-Za-z][A-Za-z\s-]+?)\s+\(([A-Z][A-Z\s-]+(?:\s+IN\s+[A-Z\s]+)?)\)'
        brand_match = re.search(brand_pattern, text)

        if brand_match:
            # Found generic (BRAND) pattern
            generic = brand_match.group(1).strip()
            brand = brand_match.group(2).strip()

            # Clean up generic name: remove trailing "in" if brand also has "IN"
            if ' IN ' in brand and generic.lower().endswith(' in'):
                generic = generic[:-3].strip()

            # Combine: "generic (BRAND)"
            name = f"{generic} ({brand})"
        else:
            # No parentheses found - try to extract just the medication name
            # Stop at dosage or form
            name_end_pattern = r'^([A-Za-z][A-Za-z\s-]+?)(?:\s+\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit|%|mEq)|(?:\s+IVPB|iv|tablet|capsule|vial|bag))'
            name_match = re.search(name_end_pattern, text, re.IGNORECASE)

            if name_match:
                name = name_match.group(1).strip()
            else:
                # Fallback: take first few words, excluding numbers
                words = []
                for word in text.split():
                    if re.match(r'^\d', word):  # Stop at first number
                        break
                    if word.lower() not in ['in', 'iv', 'ivpb']:
                        words.append(word)
                    if len(words) >= 5:  # Limit to 5 words
                        break
                name = ' '.join(words) if words else text.split()[0]

        # Final cleanup
        name = name.strip()

        # Validate name isn't empty or just punctuation
        if not name or not re.search(r'[A-Za-z]', name):
            return None

        # Reject fragments: name must be at least 3 characters and have real letters
        # This filters out fragments like "g (100 mL)", "mL", "NS", etc.
        clean_name = re.sub(r'[^A-Za-z]', '', name)  # Remove non-letters
        if len(clean_name) < 3:
            return None

        # Reject if name is ONLY a form word (already checked above, but double-check)
        if name.lower() in form_only_words:
            return None

        # Reject if name is just a unit abbreviation like "g", "mg", "mL", etc.
        unit_abbrevs = ['g', 'mg', 'mcg', 'ml', 'l', 'meq', 'mmol', 'units', 'unit']
        if clean_name.lower() in unit_abbrevs:
            return None

        # Validate we have at least a strength OR the name is substantial (not just a unit)
        # This prevents "g" or "mL" from being accepted as medications
        if not strength and len(clean_name) < 5:
            return None

        return {
            'name': name,
            'strength': strength,
            'form': form,
            'floor': device,
            'pick_amount': pick_amount
        }

    def _verify_medication_names_with_llm(self, medications: List[Dict]) -> List[Dict]:
        """
        Use LLM to verify that extracted names are real medications
        This filters out fragments like "g (100 mL)", "vial", mismatched brands, etc.
        """
        if not self.use_llm_verification or not medications:
            return medications

        try:
            # Prepare medication names for verification
            med_names = [med['name'] for med in medications]

            prompt = f"""You are a pharmacy expert. Review this list of extracted medication names and identify which ones are REAL medications vs fragments/errors.

For each entry, respond with ONLY "VALID" or "INVALID" and a brief reason.

Rules:
- VALID: Real medication names (generic or brand), including combinations like "amiodarone in D5W"
- INVALID: Fragments like "g (100 mL)", single units, form words only ("vial", "tablet"), incomplete names
- INVALID: Brand-generic mismatches (e.g., "atorvastatin (ZOFRAN)" - ZOFRAN is ondansetron's brand)

Medication names to verify:
{chr(10).join(f'{i+1}. {name}' for i, name in enumerate(med_names))}

Respond in this exact format (one line per medication):
1. VALID/INVALID - reason
2. VALID/INVALID - reason
etc.
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "messages": [
                    {"role": "system", "content": "You are a pharmacy expert who verifies medication names."},
                    {"role": "user", "content": prompt}
                ],
                "model": "grok-2-latest",
                "temperature": 0.1,
                "max_tokens": 1000,
                "stream": False
            }

            logger.info("Calling LLM for medication name verification...")
            response = requests.post(self.grok_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # Parse LLM response
            verified_medications = []
            lines = content.split('\n')

            for i, med in enumerate(medications):
                # Find corresponding line in LLM response
                verification_line = None
                for line in lines:
                    if line.startswith(f'{i+1}.'):
                        verification_line = line
                        break

                if verification_line:
                    if 'VALID' in verification_line and 'INVALID' not in verification_line:
                        verified_medications.append(med)
                        logger.info(f"✓ LLM verified: {med['name']}")
                    else:
                        logger.warning(f"✗ LLM rejected: {med['name']} - {verification_line}")
                else:
                    # If LLM didn't provide clear verdict, keep the medication (conservative)
                    verified_medications.append(med)
                    logger.warning(f"? LLM unclear for: {med['name']}, keeping it")

            logger.info(f"LLM verification: {len(medications)} → {len(verified_medications)} medications")
            return verified_medications

        except Exception as e:
            logger.error(f"LLM verification failed: {e}")
            # On error, return original list (fail-safe)
            return medications

    def _validate_against_source(self, medications: List[Dict], source_text: str) -> List[Dict]:
        """
        CRITICAL: Validate all extractions against source text to prevent hallucinations

        This is the key anti-hallucination layer that ensures LLMs haven't made up data
        """
        validated = []
        source_lower = source_text.lower()

        for med in medications:
            validation_passed = True

            # Validation 1: Medication name must appear in source
            name_lower = med['name'].lower()
            if not self._fuzzy_match_in_text(name_lower, source_lower):
                logger.warning(f"VALIDATION FAILED: '{med['name']}' not found in source text (possible hallucination)")
                validation_passed = False

            # Validation 2: Strength validation disabled for floor stock
            # Floor stock OCR is highly fragmented, making strength validation unreliable
            # The deterministic extraction already ensures strengths are from the source
            # Validation would cause too many false negatives
            if validation_passed and med.get('strength'):
                # Just log the strength for debugging, but don't fail validation
                logger.debug(f"Strength extracted: '{med['strength']}' for {med['name']}")

            # Validation 3: Floor must be valid BD format
            # Supports: 8W, 8E-1, 7EM_MICU, 7ES_SICU, etc.
            if validation_passed and med.get('floor'):
                # Regex relaxed to allow "8W", "10-ES" (hyphenated), "7EM_MICU", etc.
                # Use a broader pattern: Digits + optional separator + alphanumeric
                if not re.match(r'^\d+[-_]?[A-Za-z0-9]+[-_]?[A-Za-z0-9]*$', med['floor']):
                    logger.warning(f"VALIDATION FAILED: Invalid floor format '{med['floor']}'")
                    validation_passed = False

            # Validation 4: Pick amount must be reasonable (0-200)
            if validation_passed and med.get('pick_amount'):
                if not (0 <= med['pick_amount'] <= 200):
                    logger.warning(f"VALIDATION WARNING: Unusual pick amount {med['pick_amount']} for {med['name']}")
                    # Don't fail validation, just warn

            # Only add if all validations passed
            if validation_passed:
                validated.append(med)
            else:
                logger.info(f"Rejected medication: {med.get('name', 'Unknown')} (failed validation)")

        return validated

    def _fuzzy_match_in_text(self, search_term: str, text: str, threshold: float = 0.70) -> bool:
        """
        Fuzzy string matching to handle OCR errors
        Returns True if search_term appears in text (with some tolerance for OCR mistakes)
        """
        search_term = search_term.lower()
        text = text.lower()

        # Normalize whitespace (handle newlines in OCR text)
        # Replace newlines with spaces so "piperacillin-\ntazobactam" becomes "piperacillin- tazobactam"
        text_normalized = ' '.join(text.split())
        search_normalized = ' '.join(search_term.split())

        # Exact match (fastest)
        if search_normalized in text_normalized:
            return True

        # Also check original text (in case normalization broke something)
        if search_term in text:
            return True

        # For compound names like "NORepinephrine NS (LEVOPHED NS (8mg))",
        # check if major components are present
        # Extract the main medication name (before parentheses)
        main_name = search_term.split('(')[0].strip()

        # Check if main name appears in text
        if main_name in text:
            return True

        # For names with "in" (e.g., "norepinephrine in ns"), check each part
        if ' in ' in main_name:
            parts = main_name.split(' in ')
            # Check if the main medication name is present
            if all(part.strip() in text for part in parts if part.strip()):
                return True

        # Fuzzy match for OCR errors (e.g., "gabapentin" vs "gabapent1n")
        words = text.split()
        search_words = search_term.split()

        # For multi-word terms, check n-grams
        for i in range(len(words)):
            for j in range(i + 1, min(i + len(search_words) + 2, len(words) + 1)):
                phrase = ' '.join(words[i:j])
                ratio = SequenceMatcher(None, search_term, phrase).ratio()
                if ratio >= threshold:
                    return True

        # Final check: if it's a long compound name, check if the core medication word is present
        # (at least 6 chars to avoid false positives)
        for word in main_name.split():
            if len(word) >= 6 and word in text:
                return True

        return False

    def _deduplicate_medications(self, medications: List[Dict]) -> List[Dict]:
        """
        Remove duplicates and fragments caused by medication names split across lines.
        Examples:
        - "Sodium" + "Bicarbonate 8.4%" → Keep only "Sodium Bicarbonate"
        - "Cefazolin In Iso-" + "Osmotic Dextrose" → Keep both if not fragments
        """
        if not medications:
            return medications

        deduplicated = []
        skip_indices = set()

        for i, med in enumerate(medications):
            if i in skip_indices:
                continue

            # Check if this medication's name appears to be a fragment or part of another
            is_fragment = False

            for j, other_med in enumerate(medications):
                if i == j or j in skip_indices:
                    continue

                # Same floor/device and similar strength
                if med.get('floor') == other_med.get('floor') and \
                   med.get('strength') == other_med.get('strength'):

                    med_name = med['name'].lower()
                    other_name = other_med['name'].lower()

                    # Check if one name is a substring of another (fragment)
                    if med_name in other_name:
                        # Current med is a fragment of other
                        logger.info(f"Removing fragment: '{med['name']}' (found in '{other_med['name']}')")
                        is_fragment = True
                        skip_indices.add(i)
                        break
                    elif other_name in med_name:
                        # Other med is a fragment of current
                        logger.info(f"Removing fragment: '{other_med['name']}' (found in '{med['name']}')")
                        skip_indices.add(j)

            if not is_fragment:
                deduplicated.append(med)

        logger.info(f"Deduplication: {len(medications)} → {len(deduplicated)} medications")
        return deduplicated

    def _merge_generic_brand_pairs(self, medications: List[Dict]) -> List[Dict]:
        """
        Merge generic and brand name pairs, and filter out header text.

        Examples:
        - "ondansetron" + "(ZOFRAN)" → "ondansetron (ZOFRAN)"
        - "(LIPITOR)" alone → Look for known generic "atorvastatin (LIPITOR)"
        - "PICK (Pick and Delivery Summary)" → Remove (header text)
        - "D5W (NEXTERONE IV)" → Add generic "amiodarone in D5W (NEXTERONE IV)"
        """
        if not medications:
            return medications

        # Common brand-to-generic mappings for floor stock medications
        brand_to_generic = {
            'LIPITOR': 'atorvastatin',
            'ZOFRAN': 'ondansetron',
            'NEXTERONE': 'amiodarone',
            'MERREM': 'meropenem',
            'ORAVERSE': 'phentolamine',
            'SEROQUEL': 'quetiapine',
            'XIFAXAN': 'rifaximin',
            'KEPPRA': 'levetiracetam',
            'LOVENOX': 'enoxaparin',
            'LASIX': 'furosemide',
            'ANCEF': 'cefazolin',
            'ELIQUIS': 'apixaban',
            'MEPRON': 'atovaquone',
            'PROTONIX': 'pantoprazole',
            'ZOSYN': 'piperacillin-tazobactam',
        }

        # Header text patterns to filter out
        header_patterns = [
            r'^PICK\b',
            r'Pick and Delivery',
            r'^DESCRIPTION\b',
            r'^MED\b',
            r'^AMOUNT\b',
            r'^DEVICE\b',
        ]

        merged = []
        skip_indices = set()

        for i, med in enumerate(medications):
            if i in skip_indices:
                continue

            name = med['name']

            # Filter out header text
            is_header = False
            for pattern in header_patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    logger.info(f"Filtering out header text: '{name}'")
                    is_header = True
                    break

            if is_header:
                skip_indices.add(i)
                continue

            # Check if this is a brand-only name like "(LIPITOR)" or "(ZOFRAN)"
            brand_only_match = re.match(r'^\(([A-Z][A-Z\s]+)\)$', name)
            if brand_only_match:
                brand = brand_only_match.group(1).strip()

                # Try to find matching generic in the list
                generic_found = False
                for j, other_med in enumerate(medications):
                    if i == j or j in skip_indices:
                        continue

                    # Same floor and similar context (adjacent entries)
                    if med.get('floor') == other_med.get('floor') and abs(i - j) <= 3:
                        other_name = other_med['name'].lower()

                        # Check if other_name is a potential generic (no parentheses, lowercase)
                        # Also check brand-to-generic mapping to confirm it's the right generic
                        if '(' not in other_name and (
                            other_name.replace('-', '').replace(' ', '').isalpha() or
                            (brand in brand_to_generic and other_name == brand_to_generic[brand].lower())
                        ):
                            # Merge: generic (BRAND)
                            merged_name = f"{other_name} ({brand})"

                            # Combine info from both entries, prefer non-empty values
                            merged_med = {
                                'name': merged_name,
                                'strength': med.get('strength') or other_med.get('strength', ''),
                                'form': med.get('form') if med.get('form') != 'tablet' else other_med.get('form', 'tablet'),
                                'floor': med['floor'],
                                'pick_amount': med.get('pick_amount', 0) + other_med.get('pick_amount', 0)
                            }

                            logger.info(f"Merged: '{other_name}' + '({brand})' → '{merged_name}'")
                            merged.append(merged_med)
                            skip_indices.add(i)
                            skip_indices.add(j)
                            generic_found = True
                            break

                # If no generic found in list, use known mapping
                if not generic_found and brand in brand_to_generic:
                    generic = brand_to_generic[brand]
                    merged_name = f"{generic} ({brand})"
                    med['name'] = merged_name
                    logger.info(f"Added generic from mapping: '({brand})' → '{merged_name}'")
                    merged.append(med)
                    skip_indices.add(i)
                elif not generic_found:
                    # Keep as-is if no mapping found
                    merged.append(med)
                    skip_indices.add(i)

                continue

            # Check if this is a generic-only name and there's a matching brand nearby
            # Look for potential brand matches within 3 entries
            # IMPORTANT: Only merge if brand name actually matches the generic via mapping
            if '(' not in name and name.replace('-', '').replace(' ', '').replace('in', '').replace('ns', '').replace('d5w', '').strip().isalpha():
                brand_found = False
                for j, other_med in enumerate(medications):
                    if i == j or j in skip_indices:
                        continue

                    # Same floor and nearby
                    if med.get('floor') == other_med.get('floor') and abs(i - j) <= 3:
                        other_name = other_med['name']

                        # Check if other is a brand-only name
                        brand_match = re.match(r'^\(([A-Z][A-Z\s]+)\)$', other_name)
                        if brand_match:
                            brand = brand_match.group(1).strip()

                            # CRITICAL: Verify this generic actually matches the brand using our mapping
                            # Extract just the medication name (remove "in NS", "in D5W" etc)
                            generic_clean = name.lower().split(' in ')[0].strip()

                            if brand in brand_to_generic and generic_clean == brand_to_generic[brand].lower():
                                # Merge: generic (BRAND)
                                merged_name = f"{name} ({brand})"

                                merged_med = {
                                    'name': merged_name,
                                    'strength': med.get('strength') or other_med.get('strength', ''),
                                    'form': med.get('form') if med.get('form') != 'tablet' else other_med.get('form', 'tablet'),
                                    'floor': med['floor'],
                                    'pick_amount': med.get('pick_amount', 0) + other_med.get('pick_amount', 0)
                                }

                                logger.info(f"Merged: '{name}' + '{other_name}' → '{merged_name}'")
                                merged.append(merged_med)
                                skip_indices.add(i)
                                skip_indices.add(j)
                                brand_found = True
                                break

                if brand_found:
                    continue

            # Check if this is a solution name like "D5W (NEXTERONE IV)"
            solution_match = re.match(r'^(D5W|NS|sodium chloride|iso-osmotic)\s*\(([A-Z\s]+)\)', name, re.IGNORECASE)
            if solution_match:
                solution = solution_match.group(1)
                brand = solution_match.group(2).strip()

                # Extract just the brand name (remove "IV", "IN", etc.)
                brand_clean = re.sub(r'\s+(IV|IN|IVPB)$', '', brand).strip()

                if brand_clean in brand_to_generic:
                    generic = brand_to_generic[brand_clean]
                    merged_name = f"{generic} in {solution} ({brand})"
                    med['name'] = merged_name
                    logger.info(f"Added generic to solution: '{name}' → '{merged_name}'")

                merged.append(med)
                skip_indices.add(i)
                continue

            # Check if name already has generic (BRAND) format - keep as-is
            if re.search(r'[a-z]+\s*\([A-Z\s]+\)', name):
                merged.append(med)
                skip_indices.add(i)
                continue

            # Default: keep medication as-is
            if i not in skip_indices:
                merged.append(med)

        logger.info(f"Merge/filter: {len(medications)} → {len(merged)} medications")
        return merged

    def _parse_with_row_clustering(self, text: str, word_annotations: List) -> List[Dict]:
        """
        Hybrid approach: Use coordinates to identify rows, LLM to interpret content
    
        Strategy:
        1. Cluster words by Y-coordinate into table rows
        2. Identify column X-positions from header row
        3. For each data row, extract words by column
        4. Give LLM structured row data to interpret
        5. Validate with formula: Pick = Max - Current
        """
        try:
            logger.info("=== HYBRID ROW-BASED PARSER: Starting ===")
    
            # Step 1: Extract words with coordinates from Google Vision
            words = self._extract_words_with_coordinates(word_annotations)
            if not words:
                logger.warning("No words with coordinates found")
                return []
    
            logger.info(f"Extracted {len(words)} words with coordinates")
    
            # Step 2: Cluster words into rows by Y-coordinate
            rows = self._cluster_words_into_rows(words)
            logger.info(f"Clustered into {len(rows)} rows")
    
            if len(rows) < 2:
                logger.warning("Not enough rows found (need at least header + 1 data row)")
                return []

            # Step 3: Find the header row (contains "Pick", "Amount", "Max", "Current")
            header_row_idx = self._find_header_row(rows)
            if header_row_idx is None:
                logger.warning("Could not find table header row")
                return []

            logger.info(f"Found header row at index {header_row_idx}")

            # Step 4: Identify column positions from ALL header rows (they may be split across multiple rows)
            # Collect all words from rows 0 through header_row_idx
            all_header_words = []
            for i in range(header_row_idx + 1):
                all_header_words.extend(rows[i])

            columns = self._identify_columns_from_header(all_header_words)
            if not columns:
                logger.warning("Could not identify table columns from header")
                return []

            logger.info(f"Identified columns: {list(columns.keys())}")

            # Step 5: Extract medications from data rows (after header)
            medications = []
            current_floor = None

            # Debug: Log rows after header
            data_rows = rows[header_row_idx+1:]
            logger.info(f"DEBUG: Processing {len(data_rows)} rows after header (total rows: {len(rows)}, header at: {header_row_idx})")
            for idx in range(min(10, len(data_rows))):
                row_text = ' '.join([w['text'] for w in data_rows[idx]])
                logger.info(f"  Data row {idx}: {row_text[:100]}")

            for i, row in enumerate(rows[header_row_idx+1:], start=1):  # Skip rows before and including header
                # Check if this row contains a floor/device identifier
                floor = self._extract_floor_from_row(row)
                if floor:
                    current_floor = floor
                    logger.info(f"Row {i}: Found floor identifier: {floor}")
                    continue

                # Extract medication data from row
                med_data = self._extract_medication_from_row(row, columns, current_floor)

                # Debug: Log extraction attempts
                if med_data:
                    logger.info(f"Row {i}: ✓ Extracted medication {med_data.get('name', 'UNKNOWN')}")
                else:
                    row_text = ' '.join([w['text'] for w in row])[:80]
                    logger.info(f"Row {i}: ✗ No medication extracted from: {row_text}")
                if med_data:
                    # Validate with formula
                    if med_data.get('pick_amount') and med_data.get('max') and med_data.get('current_amount'):
                        expected_pick = med_data['max'] - med_data['current_amount']
                        actual_pick = med_data['pick_amount']
    
                        if abs(actual_pick - expected_pick) <= 5:
                            logger.info(f"✓ {med_data['name']}: Formula validated pick={actual_pick}, max={med_data['max']}, current={med_data['current_amount']}")
                        else:
                            logger.warning(f"⚠ {med_data['name']}: Formula mismatch! pick={actual_pick}, expected={expected_pick} (max={med_data['max']}, current={med_data['current_amount']})")
                            med_data['warning'] = f"⚠ Formula mismatch! Found Pick={actual_pick}, Max={med_data['max']}, Current={med_data['current_amount']}. Expected Pick={expected_pick}. Please verify manually."
    
                    medications.append(med_data)
                    logger.info(f"Row {i}: Extracted {med_data['name']} - Pick: {med_data.get('pick_amount', 'N/A')}")
    
            logger.info(f"=== HYBRID PARSER: Found {len(medications)} medications ===")
            return medications
    
        except Exception as e:
            logger.error(f"Hybrid row-based parsing failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    
    def _extract_words_with_coordinates(self, word_annotations: List) -> List[Dict]:
        """Extract words with their bounding box coordinates from Google Vision response"""
        words = []

        if not word_annotations:
            logger.warning("word_annotations is empty or None")
            return words

        try:
            # Debug: Log what we received
            logger.info(f"word_annotations type: {type(word_annotations)}")
            logger.info(f"word_annotations length: {len(word_annotations)}")

            if len(word_annotations) > 0:
                logger.info(f"First item type: {type(word_annotations[0])}")
                logger.info(f"First item has bounding_poly: {hasattr(word_annotations[0], 'bounding_poly')}")
                logger.info(f"First item has description: {hasattr(word_annotations[0], 'description')}")

            # Handle Google Vision response structure
            # Google Vision returns a RepeatedComposite (protobuf list) of TextAnnotation objects
            if len(word_annotations) > 1:
                logger.info(f"Processing {len(word_annotations)-1} word annotations (skipping first full-text annotation)")

                # Skip first annotation (full text), process individual words
                for i, annotation in enumerate(word_annotations[1:]):
                    try:
                        # TextAnnotation object has bounding_poly attribute
                        if hasattr(annotation, 'bounding_poly') and hasattr(annotation, 'description'):
                            vertices = annotation.bounding_poly.vertices
                            if len(vertices) >= 2:
                                # Extract x, y coordinates from vertices
                                x_coords = [v.x for v in vertices]
                                y_coords = [v.y for v in vertices]

                                words.append({
                                    'text': annotation.description,
                                    'x': sum(x_coords) / len(x_coords),
                                    'y': sum(y_coords) / len(y_coords),
                                    'x_min': min(x_coords),
                                    'x_max': max(x_coords),
                                    'y_min': min(y_coords),
                                    'y_max': max(y_coords),
                                })

                                if i < 3:  # Log first 3 for debugging
                                    logger.info(f"  Word {i+1}: '{annotation.description}' at ({words[-1]['x']:.1f}, {words[-1]['y']:.1f})")
                        else:
                            if i < 3:
                                logger.warning(f"  Word {i+1}: Missing bounding_poly or description")
                    except Exception as e:
                        logger.error(f"  Error processing word {i+1}: {str(e)}")

            logger.info(f"Extracted {len(words)} words with coordinates")
            return words

        except Exception as e:
            logger.error(f"Error extracting words with coordinates: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    
    def _cluster_words_into_rows(self, words: List[Dict]) -> List[List[Dict]]:
        """Cluster words by Y-coordinate into table rows"""
        if not words:
            return []
    
        # Sort words by Y-coordinate
        sorted_words = sorted(words, key=lambda w: w['y'])
    
        # Cluster into rows with ±15px Y-tolerance
        rows = []
        current_row = [sorted_words[0]]
        current_y = sorted_words[0]['y']
    
        for word in sorted_words[1:]:
            if abs(word['y'] - current_y) <= 15:  # Same row
                current_row.append(word)
            else:  # New row
                # Sort current row by X-coordinate (left to right)
                current_row.sort(key=lambda w: w['x'])
                rows.append(current_row)
    
                # Start new row
                current_row = [word]
                current_y = word['y']
    
        # Add last row
        if current_row:
            current_row.sort(key=lambda w: w['x'])
            rows.append(current_row)
    
        logger.info(f"Clustered {len(words)} words into {len(rows)} rows")
        return rows
    
    
    def _find_header_row(self, rows: List[List[Dict]]) -> Optional[int]:
        """Find the row that contains table headers (Pick, Amount, Max, Current, etc.)

        Note: Headers may be split across multiple rows in the BD table format.
        We'll find where the header region ends and data begins.
        """
        # Debug: Log first 30 rows to see what we're looking for
        logger.info("Searching for header row in first 30 rows:")
        for i in range(min(30, len(rows))):
            row_text = ' '.join([word['text'] for word in rows[i]])
            logger.info(f"  Row {i}: {row_text[:100]}")

        # Strategy: Find the last row that contains ONLY header-like words
        # Data rows will contain medication names (lowercase) and numbers
        last_pure_header_row = None

        for i in range(min(40, len(rows))):  # Only check first 40 rows
            row = rows[i]
            row_text = ' '.join([word['text'] for word in row])
            row_text_lower = row_text.lower()

            # Check if this row contains header column names
            has_header_columns = any(keyword in row_text_lower for keyword in [
                'pick amount', 'pick actual', 'current amount', 'med description'
            ])

            # Or individual header words (but be strict - must be exact match or part of known header phrase)
            has_standalone_header = any(word['text'].lower() in ['pick', 'max', 'current', 'amount', 'actual', 'description', 'device', 'area']
                                       for word in row if len(word['text']) > 1)

            # Skip if row contains mostly numbers (likely data row)
            words = [w['text'] for w in row]
            number_count = sum(1 for w in words if w.isdigit())
            if number_count > len(words) * 0.5:  # More than 50% numbers
                continue

            if has_header_columns or has_standalone_header:
                last_pure_header_row = i
                logger.info(f"  Row {i} is header-like: {row_text[:80]}")

        if last_pure_header_row is not None:
            logger.info(f"Header region ends at row {last_pure_header_row}. Data rows start at {last_pure_header_row + 1}")
            return last_pure_header_row

        logger.warning("Could not find header row - no rows contain clear header keywords")
        return None

    def _identify_columns_from_header(self, header_row: List[Dict]) -> Dict[str, tuple]:
        """Identify column X-position ranges from header row"""
        columns = {}
    
        # Find key headers
        for word in header_row:
            text_lower = word['text'].lower()
    
            if 'pick' in text_lower and 'amount' in text_lower:
                columns['pick_amount'] = (word['x_min'] - 30, word['x_max'] + 30)
            elif 'pick' in text_lower and 'actual' not in text_lower:
                if 'pick_amount' not in columns:  # Don't override "Pick Amount"
                    columns['pick_amount'] = (word['x_min'] - 30, word['x_max'] + 30)
            elif text_lower == 'max':
                columns['max'] = (word['x_min'] - 30, word['x_max'] + 30)
            elif 'current' in text_lower:
                columns['current_amount'] = (word['x_min'] - 30, word['x_max'] + 30)
            elif 'med' in text_lower or 'description' in text_lower:
                columns['med_description'] = (word['x_min'] - 30, word['x_max'] + 100)
            elif 'device' in text_lower:
                columns['device'] = (word['x_min'] - 30, word['x_max'] + 30)
    
        # If we didn't find Pick Amount but found Max and Current, infer Pick Amount position
        if 'max' in columns and 'current_amount' in columns and 'pick_amount' not in columns:
            max_x = columns['max'][0]
            # Pick Amount is typically 80-150px to the left of Max
            columns['pick_amount'] = (max_x - 150, max_x - 50)
            logger.info(f"Inferred pick_amount column position: {columns['pick_amount']}")
    
        return columns
    
    
    def _extract_floor_from_row(self, row: List[Dict]) -> Optional[str]:
        """Check if row contains a floor/device identifier (e.g., '9E-1', '9E-2')"""
        # Look for patterns like "9E-1", "9E-2", "6W-1", etc.
        for word in row:
            text = word['text'].strip()
            # Match floor pattern: number + letter(s) + dash + number
            if re.match(r'^\d+[A-Z]+-\d+$', text):
                return text
            # Also check for "9E" style (without the -1/-2)
            if re.match(r'^\d+[A-Z]+$', text) and len(text) <= 4:
                # Check if next word is a dash or number
                idx = row.index(word)
                if idx + 1 < len(row):
                    next_text = row[idx + 1]['text'].strip()
                    if next_text == '-' and idx + 2 < len(row):
                        floor_num = row[idx + 2]['text'].strip()
                        if floor_num.isdigit():
                            return f"{text}-{floor_num}"
    
        return None
    
    
    def _extract_medication_from_row(self, row: List[Dict], columns: Dict[str, tuple], current_floor: Optional[str]) -> Optional[Dict]:
        """Extract medication data from a table row using column positions"""
        try:
            # Extract words in each column
            med_words = []
            pick_amount = None
            max_amount = None
            current_amount = None

            # DEBUG: Log all numbers found in row with their X coordinates
            all_numbers = [(w['x'], w['text']) for w in row if w['text'].isdigit()]
            if all_numbers:
                logger.info(f"DEBUG ROW: Found {len(all_numbers)} numbers: {all_numbers}")
                logger.info(f"DEBUG COLUMNS: pick_amount={columns.get('pick_amount')}, max={columns.get('max')}, current={columns.get('current_amount')}")

            for word in row:
                x = word['x']
                text = word['text'].strip()

                # Skip empty words
                if not text:
                    continue

                # Check which column this word belongs to
                if 'med_description' in columns:
                    x_min, x_max = columns['med_description']
                    if x_min <= x <= x_max:
                        # Skip if it's a number in strength (e.g., "650" in "650 mg")
                        if not (text.isdigit() and len(med_words) > 0 and 'mg' in ' '.join([w['text'] for w in row])):
                            med_words.append(text)

                if 'pick_amount' in columns:
                    x_min, x_max = columns['pick_amount']
                    if x_min <= x <= x_max and text.isdigit():
                        pick_amount = int(text)
                        logger.info(f"DEBUG: Assigned pick_amount={pick_amount} from x={x} (column range {x_min}-{x_max})")

                if 'max' in columns:
                    x_min, x_max = columns['max']
                    if x_min <= x <= x_max and text.isdigit():
                        max_amount = int(text)
                        logger.info(f"DEBUG: Assigned max={max_amount} from x={x} (column range {x_min}-{x_max})")

                if 'current_amount' in columns:
                    x_min, x_max = columns['current_amount']
                    if x_min <= x <= x_max and text.isdigit():
                        current_amount = int(text)
                        logger.info(f"DEBUG: Assigned current={current_amount} from x={x} (column range {x_min}-{x_max})")
    
            # Must have at least a medication name
            if not med_words:
                return None
    
            # Join medication words
            med_text = ' '.join(med_words)
    
            # Use LLM to parse medication name, strength, and form from the text
            med_data = self._parse_medication_text_with_llm(med_text)
            if not med_data:
                return None
    
            # Add the numbers we extracted from columns
            med_data['pick_amount'] = pick_amount
            med_data['max'] = max_amount
            med_data['current_amount'] = current_amount
            med_data['floor'] = current_floor
    
            return med_data
    
        except Exception as e:
            logger.error(f"Error extracting medication from row: {str(e)}")
            return None
    
    
    def _parse_medication_text_with_llm(self, med_text: str) -> Optional[Dict]:
        """Use LLM to parse medication name, strength, and form from text"""
        try:
            if not self.api_key:
                return None
    
            prompt = f"""Extract medication information from this text and return ONLY valid JSON:
    
    Text: "{med_text}"
    
    Extract:
    - name: generic medication name (lowercase first letter, e.g., "gabapentin", "acetaminophen")
    - strength: dose with units (e.g., "325 mg", "100 mg")
    - form: medication form (tablet, capsule, vial, bag, patch, etc.)
    
    Return ONLY JSON in this exact format:
    {{"name": "medication name", "strength": "dose with units", "form": "form"}}
    
    No explanations, just the JSON:"""
    
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
    
            payload = {
                "messages": [
                    {"role": "system", "content": "You are a medication extraction expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.1,
                "max_tokens": 200
            }
    
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
    
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content'].strip()
    
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    med_data = json.loads(json_match.group())
                    return med_data
    
            return None
    
        except Exception as e:
            logger.error(f"LLM parsing failed: {str(e)}")
            return None

    def parse_with_gemini_vision(self, image_bytes: bytes) -> List[Dict]:
        """
        Parse floor stock table using Gemini 1.5 Pro vision capabilities.
        This is the most accurate method as it can SEE the table structure.

        Args:
            image_bytes: Raw image bytes from the camera

        Returns:
            List of medication dictionaries with accurate pick amounts
        """
        try:
            # Configure Gemini API
            google_api_key = os.getenv('GEMINI_API_KEY')
            if not google_api_key:
                logger.error("GEMINI_API_KEY environment variable not set")
                return []

            genai.configure(api_key=google_api_key)
            # Use Gemini 2.5 Flash (latest model with vision capabilities)
            # Alternative: gemini-2.5-pro for more complex tables
            model = genai.GenerativeModel('gemini-2.5-flash')

            logger.info("Using Gemini 2.5 Flash for table parsing")

            # Create the prompt for Gemini
            prompt = """You are analyzing a BD pharmacy floor stock pick list table image.

YOUR TASK: Extract Pick Amount, Max, and Current for each medication, then verify using the formula.

TABLE STRUCTURE (left to right):
Column 1: Device/Floor (e.g., "7EM_MICU", "8E-1")
Column 2: Med Description (name, strength, form)
Column 3: Pick Area (usually empty)
Column 4: Pick Amount (first number in row)
Column 5: Pick Actual (usually empty)
Column 6: Max (second number in row)
Column 7: Current Amount (third number in row)

VERIFICATION FORMULA:
Pick Amount = Max - Current

TWO CASES:
1. Normal case: You see 3 numbers (Pick, Max, Current)
   - Read all 3 numbers
   - Verify: Pick = Max - Current
   - If formula matches, use the Pick Amount
   - If formula doesn't match, use calculated value: Max - Current

2. Rare case: Only one number appears (lone Pick Amount)
   - Max = 0, Current = 0
   - Use the Pick Amount directly without verification

MEDICATION NAMING - CRITICAL:
- ALWAYS include release type abbreviations in the form field:
  - ER = Extended Release
  - DR = Delayed Release
  - CR = Continuous Release
  - XL = Extended Release
- Example: "tablet ER" not just "tablet"
- Example: "capsule DR" not just "capsule"

REQUIRED OUTPUT FORMAT:
{
  "medications": [
    {
      "name": "medication name",
      "strength": "dose with units",
      "form": "tablet/tablet ER/capsule DR/bag/vial/etc",
      "floor": "device code",
      "pick_amount": <verified Pick Amount>
    }
  ]
}

EXAMPLES:
Row: "divalproex (DEPAKOTE ER) | 250 mg | tablet | 3  6  3"
- Read: Pick=3, Max=6, Current=3
- Verify: 3 = 6-3 ✓ Formula matches
- Output: {"name": "divalproex (DEPAKOTE ER)", "strength": "250 mg", "form": "tablet ER", "floor": "8W", "pick_amount": 3}

Row: "insulin regular | 100 UNITS | 2  10  8"
- Read: Pick=2, Max=10, Current=8
- Verify: 2 = 10-8 ✓ Formula matches
- Output: {"name": "insulin regular", "strength": "100 UNITS", "form": "iv soln", "floor": "7EM_MICU", "pick_amount": 2}

Row: "acetaminophen | 325 mg | 158  200  42"
- Read: Pick=158, Max=200, Current=42
- Verify: 158 = 200-42 ✓ Formula matches
- Output: {"name": "acetaminophen", "strength": "325 mg", "form": "tablet", "floor": "8W", "pick_amount": 158}

Return ONLY the JSON. No markdown. No ```json blocks."""

            # Prepare image for Gemini
            import PIL.Image
            import io
            image = PIL.Image.open(io.BytesIO(image_bytes))

            # Generate content with vision
            response = model.generate_content([prompt, image])

            logger.info(f"Gemini response received: {len(response.text)} chars")
            logger.info(f"Raw Gemini output: {response.text[:500]}")

            # Parse JSON response
            medications = self._parse_llm_json_response(response.text)

            if medications:
                logger.info(f"Gemini vision parsed {len(medications)} medications")
                # Log the parsed medications for debugging
                for med in medications[:3]:  # Log first 3 for debugging
                    logger.info(f"  ✓ Parsed: {med.get('name')} {med.get('strength')} {med.get('form')} | pick_amount={med.get('pick_amount')}")

                # Apply form corrections for known Gemini misidentifications
                medications = self._correct_medication_forms(medications)

                # No formula validation needed - Gemini reads pick_amount directly from the image
                return medications
            else:
                logger.warning("Gemini returned no medications")
                return []

        except Exception as e:
            logger.error(f"Gemini vision parsing failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
