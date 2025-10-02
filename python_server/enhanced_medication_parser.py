#!/usr/bin/env python3
"""
Enhanced medication parser using the best available models
Combines Docling OCR + Claude/GPT-4 for maximum accuracy
"""

import os
import json
import logging
import requests
import re
from typing import List, Dict, Optional
from PIL import Image
import base64
import tempfile

logger = logging.getLogger(__name__)

class EnhancedMedicationParser:
    """
    High-accuracy medication parser using state-of-the-art models
    """

    def __init__(self):
        """Initialize with best available API configurations"""
        self.grok_api_key = os.getenv('GROK_API_KEY')

        # API endpoints for different models
        self.grok_url = "https://api.x.ai/v1/chat/completions"  # xAI Grok (fastest)
        self.openai_url = "https://api.openai.com/v1/chat/completions"     # GPT-4 (most accurate)

        logger.info("Enhanced medication parser initialized")

    def parse_medication_label(self, image_data: bytes, mode: str = 'cart_fill') -> Dict:
        """
        Parse medication label using enhanced pipeline

        Args:
            image_data: Raw image bytes
            mode: 'cart_fill' or 'floor_stock'

        Returns:
            Dict with parsed medication data
        """
        try:
            logger.info(f"Starting enhanced parsing for {mode} mode")

            # Step 1: Extract text using multiple methods
            ocr_text = self._extract_text_multi_method(image_data)

            if not ocr_text.strip():
                logger.warning("No text extracted from image")
                return {'success': False, 'error': 'No text extracted', 'medications': []}

            logger.info(f"OCR extracted: '{ocr_text[:200]}...'")

            # Step 2: Parse medications using best LLM
            medications = self._parse_with_best_llm(ocr_text, mode)

            # Step 3: Validate and enhance results
            validated_medications = self._validate_and_enhance(medications, ocr_text)

            logger.info(f"Enhanced parsing complete: {len(validated_medications)} medications found")

            return {
                'success': True,
                'medications': validated_medications,
                'raw_text': ocr_text,
                'method': 'enhanced_llm'
            }

        except Exception as e:
            logger.error(f"Enhanced parsing failed: {e}")
            return {'success': False, 'error': str(e), 'medications': []}

    def _extract_text_multi_method(self, image_data: bytes) -> str:
        """
        Extract text using multiple OCR methods for reliability
        """
        texts = []

        # Method 1: Try Docling (primary)
        try:
            from docling.document_converter import DocumentConverter
            pdf_path = self._convert_image_to_pdf(image_data)

            converter = DocumentConverter()
            result = converter.convert(pdf_path)
            docling_text = result.document.export_to_markdown()

            if docling_text.strip():
                texts.append(('docling', docling_text))
                logger.info(f"Docling extracted: {len(docling_text)} chars")

            os.unlink(pdf_path)  # Clean up

        except Exception as e:
            logger.warning(f"Docling OCR failed: {e}")

        # Method 2: Try Tesseract (backup)
        try:
            import pytesseract
            from PIL import Image
            import io

            image = Image.open(io.BytesIO(image_data))
            tesseract_text = pytesseract.image_to_string(image, config='--psm 6')

            if tesseract_text.strip():
                texts.append(('tesseract', tesseract_text))
                logger.info(f"Tesseract extracted: {len(tesseract_text)} chars")

        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}")

        # Method 3: Try EasyOCR (backup)
        try:
            import easyocr
            reader = easyocr.Reader(['en'])

            # Save image temporarily for EasyOCR
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp.write(image_data)
                tmp_path = tmp.name

            results = reader.readtext(tmp_path)
            easyocr_text = ' '.join([result[1] for result in results])

            if easyocr_text.strip():
                texts.append(('easyocr', easyocr_text))
                logger.info(f"EasyOCR extracted: {len(easyocr_text)} chars")

            os.unlink(tmp_path)  # Clean up

        except Exception as e:
            logger.warning(f"EasyOCR failed: {e}")

        # Return the best result (longest text with meaningful content)
        if texts:
            best_text = max(texts, key=lambda x: len(x[1]) if self._has_medication_keywords(x[1]) else 0)
            logger.info(f"Using {best_text[0]} OCR result")
            return best_text[1]

        return ""

    def _has_medication_keywords(self, text: str) -> bool:
        """Check if text contains medication-related keywords"""
        keywords = ['mg', 'mcg', 'tablet', 'capsule', 'medication', 'dose', 'patient', 'pharmacy', 'prescription']
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)

    def _parse_with_best_llm(self, text: str, mode: str) -> List[Dict]:
        """
        Parse medications using the best available LLM
        """
        # Try models in order of accuracy: GPT-4 > Groq > Fallback

        # Try Groq first (fastest, good accuracy)
        if self.grok_api_key:
            medications = self._parse_with_groq(text, mode)
            if medications:
                logger.info(f"Groq parsing successful: {len(medications)} medications")
                return medications

        # Try regex fallback if LLM fails
        logger.warning("LLM parsing failed, using regex fallback")
        return self._parse_with_regex_fallback(text, mode)

    def _parse_with_groq(self, text: str, mode: str) -> List[Dict]:
        """Parse medications using xAI Grok API with enhanced prompt"""
        try:
            prompt = self._create_enhanced_prompt(text, mode)

            headers = {
                "Authorization": f"Bearer {self.grok_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "messages": [
                    {"role": "system", "content": "You are a pharmacy medication extraction expert."},
                    {"role": "user", "content": prompt}
                ],
                "model": "grok-2-latest",  # xAI Grok model
                "temperature": 0.1,
                "max_tokens": 2000,
                "stream": False
            }

            logger.info("Calling xAI Grok API for medication parsing")
            response = requests.post(self.grok_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # Parse JSON response
            medications = self._parse_llm_json_response(content)
            logger.info(f"xAI Grok parsed {len(medications)} medications")

            return medications

        except Exception as e:
            logger.error(f"xAI Grok parsing failed: {e}")
            return []

    def _create_enhanced_prompt(self, text: str, mode: str) -> str:
        """Create enhanced prompt for medication parsing"""

        if mode == 'cart_fill':
            example = """
Example input: "Lisinopril 10mg Tablet, Patient: John Doe, Quantity: 30 tablets, Directions: Take 1 tablet daily, Rx: 123456789"
Example output: {
  "medications": [
    {
      "name": "Lisinopril",
      "strength": "10 mg",
      "form": "tablet",
      "quantity": "30",
      "patient": "John Doe",
      "directions": "Take 1 tablet daily",
      "frequency": "once daily",
      "rx_number": "123456789"
    }
  ]
}"""
        else:
            example = """
Example input: "Metoprolol 25mg Tab, Floor: 6W, Pick: 15, Current: 8, Max: 50"
Example output: {
  "medications": [
    {
      "name": "Metoprolol",
      "strength": "25 mg",
      "form": "tablet",
      "floor": "6W",
      "pick_amount": 15,
      "current_stock": 8,
      "max_stock": 50
    }
  ]
}"""

        return f"""You are a pharmacy expert. Extract medication information from this pharmacy label/document text and return ONLY valid JSON.

CRITICAL INSTRUCTIONS:
1. Extract EVERY medication mentioned
2. For medication names: Use generic names (e.g., "lisinopril" not "PRINIVIL")
3. For strengths: Include units (e.g., "10 mg", "5 mcg")
4. For forms: Use standard terms (tablet, capsule, liquid, injection)
5. Handle OCR errors intelligently (e.g., "1Omg" → "10 mg", "tabiet" → "tablet")
6. Convert abbreviations: BID→"twice daily", TID→"three times daily", QD→"once daily"

{example}

Text to parse:
{text}

Return ONLY the JSON response, no explanations:"""

    def _parse_llm_json_response(self, content: str) -> List[Dict]:
        """Parse LLM JSON response safely"""
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

            # Validate each medication
            validated = []
            for med in medications:
                if self._validate_medication_data(med):
                    validated.append(med)

            return validated

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            logger.error(f"Raw content: {content}")
            return []
        except Exception as e:
            logger.error(f"LLM response parsing error: {e}")
            return []

    def _validate_medication_data(self, med: Dict) -> bool:
        """Validate medication data structure"""
        # Must have at least a name
        if not med.get('name') or len(str(med['name']).strip()) < 2:
            return False

        name_lower = str(med['name']).lower().strip()

        # Skip obviously wrong names (common non-medication words)
        invalid_names = [
            'patient', 'directions', 'pharmacy', 'label', 'dose', 'admin',
            'tablet', 'capsule', 'solution', 'drop', 'drops', 'medication',
            'order', 'quantity', 'dispense', 'refill', 'tech', 'rph',
            'mount', 'sinai', 'morningside', 'clark', 'lot', 'dob', 'mrn',
            'each', 'eye', 'ophthalmic', 'ose', 'pense', 'qty'
        ]

        if name_lower in invalid_names:
            return False

        # Must have actual letters (not just numbers or symbols)
        if not re.search(r'[a-zA-Z]{3,}', str(med['name'])):
            return False

        # Medication must have either strength or brand to be valid
        if not med.get('strength') and not med.get('brand'):
            return False

        return True

    def _parse_with_regex_fallback(self, text: str, mode: str) -> List[Dict]:
        """Fallback regex parsing for when LLM fails"""
        logger.info("Using regex fallback parsing")
        medications = []

        # Enhanced regex patterns for medication extraction
        patterns = [
            # Pattern 1: "Name-Name (BRAND) strength form" - for hyphenated meds like dorzolamide-timolol
            r'([A-Za-z]+(?:-[A-Za-z]+)+)\s*\(([^)]+)\)\s*([\d.]+(?:[\d/.]+)?\s*(?:mg|mcg|g|mL|unit)(?:/mL)?)',

            # Pattern 2: "Name (BRAND) strength" - prioritize medications with brand names
            r'([A-Za-z][A-Za-z-]{3,})\s*\(([A-Z][A-Z\s]+)\)\s*([\d.]+(?:[\d/.]+)?\s*(?:mg|mcg|g|mL|unit)(?:/mL)?)',

            # Pattern 3: Brand name pattern - "Medication\nName strength"
            r'Medication\s+([A-Za-z][A-Za-z-]{3,})\s+([\d.]+(?:[\d/.]+)?\s*(?:mg|mcg|g|mL|unit)(?:/mL)?)',

            # Pattern 4: Extract any medication-like words (including hyphenated) with common suffixes
            r'\b([A-Za-z]+(?:-[A-Za-z]+)?(?:pril|statin|olol|pine|zole|mycin|cillin|mide|lol|zide|pam|zepam))\b'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()

                # Handle different pattern group structures
                if len(groups) >= 4:  # Pattern 1 with brand
                    med_data = {
                        'name': groups[0].strip(),
                        'brand': groups[1].strip() if groups[1] else None,
                        'strength': groups[2].strip(),
                        'form': groups[3].strip() if groups[3] else 'solution'
                    }
                elif len(groups) >= 3:
                    med_data = {
                        'name': groups[0].strip(),
                        'strength': groups[1].strip() if groups[1] else '',
                        'form': groups[2].strip() if groups[2] else 'tablet'
                    }
                elif len(groups) >= 2:
                    med_data = {
                        'name': groups[0].strip(),
                        'strength': groups[1].strip() if groups[1] else '',
                        'form': 'tablet'
                    }
                else:
                    med_data = {
                        'name': groups[0].strip(),
                        'strength': '',
                        'form': 'tablet'
                    }

                # Additional extraction from context
                self._extract_additional_info(text, med_data)

                if self._validate_medication_data(med_data):
                    medications.append(med_data)
                    logger.info(f"Regex extracted: {med_data}")

        return medications

    def _extract_additional_info(self, text: str, med_data: Dict):
        """Extract additional information from text context"""
        text_lines = text.split('\n')

        for line in text_lines:
            line_lower = line.lower()

            # Extract patient name
            patient_match = re.search(r'([A-Z][a-z]+,\s*[A-Z][a-z]+)', line)
            if patient_match:
                med_data['patient'] = patient_match.group(1).strip()

            # Extract MRN
            mrn_match = re.search(r'MRN[:\s]*(\d+)', line, re.IGNORECASE)
            if mrn_match:
                med_data['mrn'] = mrn_match.group(1)

            # Extract Order number
            order_match = re.search(r'Order\s*#\s*(\d+)', line, re.IGNORECASE)
            if order_match:
                med_data['order_number'] = order_match.group(1)

            # Extract dosing instructions (Admin line)
            admin_match = re.search(r'ose[:\s]*(\d+(?:\.\d+)?)\s*(drop|tablet|capsule)', line, re.IGNORECASE)
            if admin_match:
                med_data['admin'] = f"{admin_match.group(1)} {admin_match.group(2)}"

            # Extract frequency/timing with proper formatting
            frequency_patterns = [
                (r'\bq24h\b|\bonce\s+daily\b|\bdaily\b|\bqd\b', 'Daily'),
                (r'\bbid\b|\btwice\s+daily\b|\btwo\s+times\s+daily\b', 'Twice per day'),
                (r'\btid\b|\bthree\s+times\s+daily\b', 'Three times per day'),
                (r'\bqid\b|\bfour\s+times\s+daily\b', 'Four times per day'),
                (r'\bq4h\b|\bevery\s+4\s+hours\b', 'Every 4 hours'),
                (r'\bq6h\b|\bevery\s+6\s+hours\b', 'Every 6 hours'),
                (r'\bq8h\b|\bevery\s+8\s+hours\b', 'Every 8 hours'),
                (r'\bq12h\b|\bevery\s+12\s+hours\b', 'Every 12 hours'),
                (r'\bqhs\b|\bat\s+bedtime\b|\bbedtime\b', 'At bedtime'),
                (r'\bqam\b|\bin\s+the\s+morning\b|\bmorning\b', 'In the morning'),
                (r'\bqpm\b|\bin\s+the\s+evening\b|\bevening\b', 'In the evening'),
                (r'\bprn\b|\bas\s+needed\b', 'As needed'),
            ]

            for pattern, freq_text in frequency_patterns:
                if re.search(pattern, line_lower):
                    med_data['frequency'] = freq_text
                    break

            # Extract quantity
            qty_match = re.search(r'Qty[:\s]*(\d+(?:\.\d+)?)\s*x\s*(\d+)', line, re.IGNORECASE)
            if qty_match:
                med_data['quantity'] = qty_match.group(1)

    def _smart_medication_extraction(self, text: str) -> List[Dict]:
        """Intelligent medication extraction with context awareness and proper formatting"""
        logger.info("Attempting intelligent medication extraction")

        # Step 1: Extract medication name and strength with context
        medication_name = None
        medication_strength = None
        medication_form = 'Tablet'  # Default

        # Enhanced name patterns with context awareness
        name_strength_patterns = [
            # Pattern 1: "melatonin tablet 1 mg" or "melatonin 1 mg tablet"
            r'([A-Za-z][A-Za-z]{3,})\s*(?:tablet|capsule)\s*(\d+(?:\.\d+)?\s*mg)',
            r'([A-Za-z][A-Za-z]{3,})\s*(\d+(?:\.\d+)?\s*mg)\s*(?:tablet|capsule)',
            # Pattern 2: "Medication\nmelatonin 1 mg tablet"
            r'(?:Medication\s*\n\s*)?([A-Za-z][A-Za-z]{3,})\s*(\d+(?:\.\d+)?\s*mg)\s*(?:tablet|capsule)',
            # Pattern 3: "glipiZIDE (GLUCOTROL) tablet 2.5 mg"
            r'([A-Za-z][A-Za-z]{3,})\s*\([^)]+\)\s*(?:tablet|capsule)\s*(\d+(?:\.\d+)?\s*mg)',
            # Pattern 4: Simple "Name strength" anywhere in text
            r'([A-Za-z][A-Za-z]{3,})\s*(\d+(?:\.\d+)?\s*mg)',
        ]

        for pattern in name_strength_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                medication_name = match.group(1).strip().title()
                medication_strength = match.group(2).strip()
                logger.info(f"Found medication: {medication_name} {medication_strength}")
                break

        if not medication_name:
            logger.info("No medication name found in smart extraction")
            return []

        # Step 2: Extract dose amount (actual prescribed dose)
        dose_amount = None
        dose_patterns = [
            r'Dose[:\s]*(\d+(?:\.\d+)?\s*mg)',
            r'dose[:\s]*(\d+(?:\.\d+)?\s*mg)',
        ]

        for pattern in dose_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dose_amount = match.group(1).strip()
                logger.info(f"Found dose: {dose_amount}")
                break

        # Use strength as fallback for dose
        if not dose_amount and medication_strength:
            dose_amount = medication_strength

        # Step 3: Extract frequency/timing
        frequency = None
        frequency_patterns = [
            (r'Q24H|once\s+daily|daily|QD', 'daily'),
            (r'BID|twice\s+daily|two\s+times\s+daily|every\s+12\s+hours', 'twice daily'),
            (r'TID|three\s+times\s+daily|every\s+8\s+hours', 'three times daily'),
            (r'QID|four\s+times\s+daily|every\s+6\s+hours', 'four times daily'),
            (r'QAM|Before\s+Breakfast|in\s+the\s+morning|morning', 'in the morning'),
            (r'QHS|at\s+bedtime|bedtime', 'at bedtime'),
            (r'QPM|in\s+the\s+evening|evening', 'in the evening'),
            (r'PRN|as\s+needed|when\s+needed', 'as needed'),
            (r'Every\s+8\s+hours', 'three times daily'),
        ]

        for pattern, freq_text in frequency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                frequency = freq_text
                logger.info(f"Found frequency: {frequency}")
                break

        # Step 4: Extract administration amount
        admin_amount = None
        admin_patterns = [
            r'Admin\s*\n\s*(\d+(?:\.\d+)?)\s*tablet',
            r'Admin[:\s]*(\d+(?:\.\d+)?)\s*tablet',
            r'admin\s*\n\s*(\d+(?:\.\d+)?)\s*tablet',
            r'admin[:\s]*(\d+(?:\.\d+)?)\s*tablet',
            r'Take\s+(\d+(?:\.\d+)?)\s*tablet',
        ]

        for pattern in admin_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                admin_amount = match.group(1).strip()
                logger.info(f"Found admin: {admin_amount}")
                break

        # Step 5: Detect form (tablet/capsule)
        form_match = re.search(r'(tablet|capsule)', text, re.IGNORECASE)
        if form_match:
            medication_form = form_match.group(1).title()

        # Step 6: Format output exactly as requested
        # Name: Melatonin 1mg Tablet
        formatted_name = f"{medication_name} {medication_strength} {medication_form}"

        # Dose: 1mg daily (or just 1mg if no frequency)
        formatted_dose = dose_amount
        if frequency:
            formatted_dose += f" {frequency}"

        # Admin: 1 tablet (or see directions if not found)
        formatted_admin = f"{admin_amount} tablet" if admin_amount else "See directions"

        # Create the final medication object
        consolidated_med = {
            'name': formatted_name,
            'dose': formatted_dose,
            'admin': formatted_admin,
            'strength': medication_strength,
            'form': medication_form.lower(),
            'frequency': frequency,
            'confidence': 0.95,
            'consolidated': True,
            'extraction_method': 'intelligent_context'
        }

        logger.info(f"✓ Intelligent extraction successful!")
        logger.info(f"  Name: {formatted_name}")
        logger.info(f"  Dose: {formatted_dose}")
        logger.info(f"  Admin: {formatted_admin}")

        return [consolidated_med]

    def _validate_and_enhance(self, medications: List[Dict], raw_text: str) -> List[Dict]:
        """Final validation and enhancement of parsed medications"""
        enhanced = []
        seen_names = set()

        # If no medications found, try intelligent extraction first
        if not medications and self._has_medication_keywords(raw_text):
            logger.info("No medications found, trying intelligent extraction")
            intelligent_meds = self._smart_medication_extraction(raw_text)
            if intelligent_meds:
                medications = intelligent_meds

        for med in medications:
            # Clean and standardize medication name
            if 'name' in med:
                med['name'] = self._clean_medication_name(med['name'])

            # Skip if we've already seen this medication name (avoid duplicates)
            name_key = med['name'].lower()
            if name_key in seen_names:
                logger.info(f"Skipping duplicate medication: {med['name']}")
                continue

            # Standardize strength format
            if 'strength' in med:
                med['strength'] = self._clean_strength(med['strength'])

            # Standardize form
            if 'form' in med:
                med['form'] = self._standardize_form(med['form'])

            # Format the dose field properly: "strength frequency"
            dose_parts = []
            if med.get('strength'):
                dose_parts.append(med['strength'])
            if med.get('frequency'):
                dose_parts.append(med['frequency'])

            med['dose'] = ' '.join(dose_parts) if dose_parts else med.get('strength', '')

            # Ensure admin field is properly formatted
            if not med.get('admin') and med.get('form'):
                # Default to "1 <form>" if no admin specified
                med['admin'] = f"1 {med['form']}"

            # Calculate 24-hour pick amount based on frequency and admin
            pick_amount = self._calculate_24hr_pick_amount(
                med.get('frequency', ''),
                med.get('admin', '1')
            )
            med['pick_amount'] = pick_amount
            med['quantity'] = pick_amount  # For backwards compatibility

            # Add confidence score
            med['confidence'] = self._calculate_confidence(med, raw_text)

            # Only add if passes validation
            if self._validate_medication_data(med):
                enhanced.append(med)
                seen_names.add(name_key)
                logger.info(f"✓ Added medication: {med['name']} - {med.get('strength', '')} - {med.get('form', '')}")
            else:
                logger.info(f"✗ Rejected invalid medication: {med.get('name', 'Unknown')}")

        # Sort by confidence (highest first)
        enhanced.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        logger.info(f"Final medication count: {len(enhanced)} (filtered from {len(medications)} candidates)")
        return enhanced

    def _clean_medication_name(self, name: str) -> str:
        """Clean and standardize medication name"""
        # Remove special characters and extra spaces
        clean_name = re.sub(r'[^\w\s]', '', str(name)).strip()
        clean_name = re.sub(r'\s+', ' ', clean_name)

        # Common OCR corrections
        corrections = {
            'isinopril': 'lisinopril',
            'metoproloi': 'metoprolol',
            'gabapentln': 'gabapentin'
        }

        clean_lower = clean_name.lower()
        for error, correction in corrections.items():
            if error in clean_lower:
                clean_name = correction
                break

        return clean_name.title()

    def _clean_strength(self, strength: str) -> str:
        """Clean and standardize strength format"""
        if not strength:
            return ""

        # Remove extra spaces and standardize
        clean = re.sub(r'\s+', ' ', str(strength)).strip()

        # OCR corrections
        clean = clean.replace('1O', '10').replace('O', '0')
        clean = clean.replace('rng', 'mg').replace('rnL', 'mL')

        return clean

    def _standardize_form(self, form: str) -> str:
        """Standardize medication form"""
        if not form:
            return "tablet"

        form_lower = str(form).lower()

        if 'tab' in form_lower:
            return 'tablet'
        elif 'cap' in form_lower:
            return 'capsule'
        elif 'liquid' in form_lower or 'susp' in form_lower:
            return 'liquid'
        elif 'inject' in form_lower:
            return 'injection'
        elif 'cream' in form_lower or 'ointment' in form_lower:
            return 'topical'

        return form_lower

    def _calculate_24hr_pick_amount(self, frequency: str, admin: str) -> int:
        """
        Calculate 24-hour pick amount based on frequency and admin amount

        Args:
            frequency: e.g., "Daily", "Twice per day", "Every 4 hours"
            admin: e.g., "1 tablet", "0.5 tablet", "2 drops"

        Returns:
            Total quantity needed for 24 hours
        """
        # Extract numeric amount from admin string
        admin_amount = 1.0
        admin_match = re.search(r'(\d+(?:\.\d+)?)', admin)
        if admin_match:
            admin_amount = float(admin_match.group(1))

        # Map frequency to times per day
        frequency_lower = frequency.lower() if frequency else ''

        times_per_day = 1  # Default

        if 'every 4 hours' in frequency_lower or 'q4h' in frequency_lower:
            times_per_day = 6
        elif 'every 6 hours' in frequency_lower or 'q6h' in frequency_lower:
            times_per_day = 4
        elif 'every 8 hours' in frequency_lower or 'q8h' in frequency_lower:
            times_per_day = 3
        elif 'every 12 hours' in frequency_lower or 'q12h' in frequency_lower:
            times_per_day = 2
        elif 'four times per day' in frequency_lower or 'qid' in frequency_lower:
            times_per_day = 4
        elif 'three times per day' in frequency_lower or 'tid' in frequency_lower:
            times_per_day = 3
        elif 'twice per day' in frequency_lower or 'bid' in frequency_lower:
            times_per_day = 2
        elif 'daily' in frequency_lower or 'once' in frequency_lower or 'qd' in frequency_lower:
            times_per_day = 1
        elif 'bedtime' in frequency_lower or 'qhs' in frequency_lower:
            times_per_day = 1
        elif 'morning' in frequency_lower or 'qam' in frequency_lower:
            times_per_day = 1
        elif 'evening' in frequency_lower or 'qpm' in frequency_lower:
            times_per_day = 1
        elif 'as needed' in frequency_lower or 'prn' in frequency_lower:
            times_per_day = 1  # PRN defaults to 1 unless specified otherwise

        # Calculate total 24-hour amount
        total_amount = admin_amount * times_per_day

        # Always return as integer (round up if needed for 24-hour supply)
        import math
        return int(math.ceil(total_amount))

    def _calculate_confidence(self, med: Dict, raw_text: str) -> float:
        """Calculate confidence score for medication parsing"""
        score = 0.0

        # Base score for having required fields
        if med.get('name'):
            score += 0.4
        if med.get('strength'):
            score += 0.3
        if med.get('form'):
            score += 0.1

        # Bonus for additional fields
        if med.get('patient'):
            score += 0.1
        if med.get('quantity'):
            score += 0.05
        if med.get('frequency'):
            score += 0.05

        # Check if medication name appears in text
        if med.get('name') and med['name'].lower() in raw_text.lower():
            score += 0.2

        return min(score, 1.0)

    def _convert_image_to_pdf(self, image_data: bytes) -> str:
        """Convert image to PDF for Docling processing"""
        try:
            from PIL import Image
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io

            # Open and process image
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Create temporary PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                pdf_path = temp_pdf.name

            # Create PDF
            c = canvas.Canvas(pdf_path, pagesize=letter)

            # Save image temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_img:
                image.save(temp_img.name, 'PNG')
                temp_img_path = temp_img.name

            try:
                # Add image to PDF
                page_width, page_height = letter
                img_width, img_height = image.size

                # Scale to fit page
                scale = min(page_width / img_width, page_height / img_height) * 0.9
                new_width = img_width * scale
                new_height = img_height * scale

                x = (page_width - new_width) / 2
                y = (page_height - new_height) / 2

                c.drawImage(temp_img_path, x, y, width=new_width, height=new_height)
                c.save()

            finally:
                os.unlink(temp_img_path)

            return pdf_path

        except Exception as e:
            logger.error(f"Image to PDF conversion failed: {e}")
            raise


# Global parser instance
_enhanced_parser = None

def get_enhanced_parser():
    """Get or create enhanced parser instance"""
    global _enhanced_parser
    if _enhanced_parser is None:
        _enhanced_parser = EnhancedMedicationParser()
    return _enhanced_parser

def parse_medication_with_enhanced_model(image_data: bytes, mode: str = 'cart_fill') -> Dict:
    """
    Parse medication using enhanced model pipeline

    Args:
        image_data: Raw image bytes
        mode: 'cart_fill' or 'floor_stock'

    Returns:
        Dict with parsing results
    """
    parser = get_enhanced_parser()
    return parser.parse_medication_label(image_data, mode)