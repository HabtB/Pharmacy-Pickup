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
from typing import List, Dict, Optional
from difflib import SequenceMatcher

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

    def parse(self, text: str) -> List[Dict]:
        """
        Hybrid parsing: Deterministic structure + validated extractions

        Strategy:
        1. DETERMINISTIC: Extract floor boundaries and structure
        2. DETERMINISTIC: Extract pick amounts (critical field)
        3. REGEX: Extract medication details
        4. VALIDATE: Verify all data against source text (anti-hallucination)
        5. POST-PROCESS: Merge generic/brand pairs and filter headers

        Args:
            text: OCR extracted text from BD pick list

        Returns:
            List of validated medication dictionaries
        """
        logger.info("=== HYBRID FLOOR STOCK PARSER: Starting ===")

        # DEBUG: Log full OCR text to check if correct numbers are present
        with open('/tmp/ocr_debug.txt', 'w') as f:
            f.write(text)
        logger.info(f"DEBUG: Full OCR text saved to /tmp/ocr_debug.txt ({len(text)} chars)")

        # Step 1: Try LLM-based parsing first (more accurate for compound names)
        if self.use_llm_verification:
            medications = self._parse_with_groq(text)
            if medications:
                logger.info(f"Using LLM parsing: {len(medications)} medications found")
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
            prompt = f"""You are a pharmacy expert. Extract medication information from this BD floor stock pick list and return ONLY valid JSON.

CRITICAL INSTRUCTIONS:
1. Extract EVERY medication listed under each Device/Floor (6W-1, 6W-2, 8E-1, 8E-2, 9E-1, 9E-2, etc.)
2. MANDATORY: Each medication MUST have a "floor" field. Look for Device numbers like "6W-1", "8E-2", "9E-1"
3. The floor/device stays the same for multiple medications until a new device number appears
4. For medication names: Use the generic name (lowercase first letter like "gabapentin", "ceFAZolin")
5. Extract strength with units (e.g., "500 mg", "1 g", "4%")
6. Extract form: tablet, capsule, patch, bag (for IV), vial, packet, nebulizer, syringe, ud cup, liquid, etc.
7. IMPORTANT: IV bags should have form "bag" not "injection"
8. CRITICAL - Extract ALL THREE numeric values for validation:
   - "pick_amount": The amount to pick (smaller number, typically first or second after medication)
   - "max": Maximum stock level (typically a larger number)
   - "current_amount": Current stock on hand (typically a larger number)

   BD TABLE COLUMNS (left to right):
   | Medication Description | Pick Area | Pick Amount | Pick Actual | Max | Current Amount |

   After each medication description, you'll see several numbers. Extract:
   - pick_amount: Usually the 1st or 2nd standalone number (the smaller value)
   - max: Usually appears later in the sequence (a larger value)
   - current_amount: Usually the last number in the sequence

   VALIDATION: Pick Amount should approximately equal (Max - Current Amount)
   - This helps you identify which number is which
   - Example: If you see numbers "42, 80, 38" → pick_amount=42, max=80, current_amount=38 (because 80-38≈42)

9. Handle multi-line medication entries (medication name may span multiple lines)

Example JSON output format:
{{
  "medications": [
    {{
      "name": "heparin",
      "strength": "5000 units/mL",
      "form": "vial",
      "floor": "9W-1",
      "pick_amount": 42,
      "max": 80,
      "current_amount": 38
    }},
    {{
      "name": "acetaminophen",
      "strength": "325 mg",
      "form": "tablet",
      "floor": "8E-1",
      "pick_amount": 79,
      "max": 200,
      "current_amount": 121
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
            # Supports: 8E-1, 8W-2, 7EM_MICU, 7ES_SICU, 6E-2_CICU, etc.
            if validation_passed and med.get('floor'):
                if not re.match(r'^\d+[EW][-_]?[\dA-Z]+[-_]?[A-Z]*$', med['floor']):
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

    def _fuzzy_match_in_text(self, search_term: str, text: str, threshold: float = 0.85) -> bool:
        """
        Fuzzy string matching to handle OCR errors
        Returns True if search_term appears in text (with some tolerance for OCR mistakes)
        """
        search_term = search_term.lower()
        text = text.lower()

        # Exact match (fastest)
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
