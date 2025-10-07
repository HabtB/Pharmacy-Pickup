#!/usr/bin/env python3
"""
Floor Stock Parser for BD Pick Lists
Parses tabular floor stock medication pick lists with Device, Med, Pick Amount columns
"""

import re
import logging
import json
import requests
import os
from typing import List, Dict, Optional

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

    def __init__(self, api_key: Optional[str] = None):
        """Initialize parser with optional API key for LLM"""
        self.api_key = api_key or os.getenv('GROK_API_KEY')
        self.grok_url = "https://api.x.ai/v1/chat/completions"

    def parse(self, text: str) -> List[Dict]:
        """
        Parse floor stock text to extract medications

        Args:
            text: OCR extracted text from BD pick list

        Returns:
            List of medication dictionaries with name, strength, form, floor, pick_amount
        """
        logger.info("=== FLOOR STOCK PARSER: Starting ===")
        medications = []

        # Try Groq LLM first if API key available
        if self.api_key:
            logger.info("Attempting Groq LLM parsing for floor stock")
            medications = self._parse_with_groq(text)

        # Fall back to regex parsing if LLM fails
        if not medications:
            logger.info("Groq parsing failed or unavailable, using regex fallback")
            medications = self._parse_bd_table(text)

        logger.info(f"=== FLOOR STOCK PARSER: Found {len(medications)} medications ===")
        return medications

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

            # Extract Device/Floor (e.g., "6W-1", "7E", "8W-2")
            device_match = re.match(r'^(\d+[EW]-?\d*)$', line)
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

            # Check if line starts with a medication name (letters, possibly with hyphens)
            if re.match(r'^[A-Za-z][A-Za-z-]+$', line) and len(line) >= 4:
                # This could be a medication name
                # Look at next 3-4 lines for strength and form
                med_name = line
                strength = ''
                form = 'tablet'

                # Check next lines for strength (number + unit) and form
                for offset in range(1, min(5, len(lines) - i)):
                    next_line = lines[i + offset].strip()

                    # Skip brand names in parentheses
                    if re.match(r'^\([A-Z\s]+\)$', next_line):
                        continue

                    # Look for strength pattern (number + unit + form)
                    strength_form_match = re.search(r'([\d.]+\s*(?:mg|mcg|g|mL|unit|units?|%|mEq)(?:\s*/\s*[\d.]+\s*mL)?)\s+(tablet|capsule|vial|bag|nebulizer|patch|packet|syringe|cup|syrup|liquid|suspension|injection|each)', next_line, re.IGNORECASE)

                    if strength_form_match:
                        strength = strength_form_match.group(1)
                        form = strength_form_match.group(2).lower()
                        break

                    # Just strength without form
                    strength_match = re.search(r'([\d.]+\s*(?:mg|mcg|g|mL|unit|units?|%|mEq)(?:\s*/\s*[\d.]+\s*mL)?)', next_line, re.IGNORECASE)
                    if strength_match:
                        strength = strength_match.group(1)
                        # Keep looking for form in next line

                # Create medication if we have valid data
                if current_device and strength:
                    # Normalize form
                    form = self._normalize_form(med_name, form)

                    # Look for pick amount after this medication
                    pick_amount = self._extract_pick_amount(lines, i + 4)

                    med_data = {
                        'name': self._normalize_name(med_name),
                        'strength': strength,
                        'form': form,
                        'floor': current_device,
                        'pick_amount': pick_amount
                    }

                    medications.append(med_data)
                    logger.info(f"Extracted: {med_data['name']} - {med_data['strength']} - {med_data['form']} - Floor: {med_data['floor']} - Pick: {pick_amount}")

            i += 1

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
2. MANDATORY: Each medication MUST have a "floor" field. Look for Device numbers like "6W-1", "8E-2", "9E-1" in the leftmost column
3. The floor/device stays the same for multiple medications until a new device number appears
4. For medication names: Use the generic name (lowercase first letter like "gabapentin", "ceFAZolin")
5. Extract strength with units (e.g., "500 mg", "1 g", "4%")
6. Extract form: tablet, capsule, patch, bag (for IV), vial, packet, nebulizer, syringe, liquid, etc.
7. IMPORTANT: IV bags should have form "bag" not "injection"
8. Extract pick_amount - look for "Pick Amount" column values
9. Handle multi-line medication entries (medication name may span multiple lines)

BD FORMAT STRUCTURE:
Device | Med | Description | Pick Area | Pick Amount | Max | Current
8W-1   | medication1 | details | ... | 25 | ... | ...
       | medication2 | details | ... | 18 | ... | ...
8W-2   | medication3 | details | ... | 10 | ... | ...

Example output format:
{{
  "medications": [
    {{
      "name": "enoxaparin",
      "strength": "30 mg",
      "form": "syringe",
      "floor": "8W-1",
      "pick_amount": 25
    }},
    {{
      "name": "lidocaine",
      "strength": "4%",
      "form": "patch",
      "floor": "8W-1",
      "pick_amount": 18
    }},
    {{
      "name": "ceFAZolin",
      "strength": "1 g",
      "form": "bag",
      "floor": "8W-2",
      "pick_amount": 10
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
