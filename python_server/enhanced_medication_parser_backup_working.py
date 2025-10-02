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
        self.grok_url = "https://api.groq.com/openai/v1/chat/completions"  # Groq (fastest)
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
        """Parse medications using Groq API with enhanced prompt"""
        try:
            prompt = self._create_enhanced_prompt(text, mode)

            headers = {
                "Authorization": f"Bearer {self.grok_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "model": "llama-3.1-70b-versatile",
                "temperature": 0.1,
                "max_tokens": 2000
            }

            logger.info("Calling Groq API for medication parsing")
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

        # Skip obviously wrong names
        invalid_names = ['patient', 'directions', 'pharmacy', 'label', 'dose', 'admin']
        if str(med['name']).lower() in invalid_names:
            return False

        return True

    def _parse_with_regex_fallback(self, text: str, mode: str) -> List[Dict]:
        """Fallback regex parsing for when LLM fails"""
        logger.info("Using regex fallback parsing")
        medications = []

        # Enhanced regex patterns for medication extraction
        patterns = [
            # Pattern 1: "Medication: Name strength form"
            r'(?:medication[:\s]*)?([A-Za-z][A-Za-z\s]{2,}?)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit))\s*(\w+)?',

            # Pattern 2: "Name (BRAND) strength form"
            r'([A-Za-z][A-Za-z\s]{2,}?)\s*\([^)]+\)\s*(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit))\s*(\w+)?',

            # Pattern 3: Simple "Name strength"
            r'([A-Za-z][A-Za-z\s]{2,}?)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit))',

            # Pattern 4: Extract any medication-like words
            r'\b([A-Za-z]{4,}(?:pril|statin|olol|pine|zole|mycin|cillin))\b'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                med_data = {
                    'name': match.group(1).strip(),
                    'strength': match.group(2).strip() if len(match.groups()) > 1 else '',
                    'form': match.group(3).strip() if len(match.groups()) > 2 and match.group(3) else 'tablet'
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
            patient_match = re.search(r'patient[:\s]*([A-Za-z\s,]+)', line, re.IGNORECASE)
            if patient_match:
                med_data['patient'] = patient_match.group(1).strip()

            # Extract quantity
            qty_match = re.search(r'quantity[:\s]*(\d+)', line, re.IGNORECASE)
            if qty_match:
                med_data['quantity'] = qty_match.group(1)

            # Extract directions/frequency
            if 'daily' in line_lower:
                med_data['frequency'] = 'once daily'
            elif 'twice' in line_lower or 'bid' in line_lower:
                med_data['frequency'] = 'twice daily'
            elif 'three times' in line_lower or 'tid' in line_lower:
                med_data['frequency'] = 'three times daily'

            # Extract Rx number
            rx_match = re.search(r'(?:rx|prescription)[:\s#]*([A-Za-z0-9]+)', line, re.IGNORECASE)
            if rx_match:
                med_data['rx_number'] = rx_match.group(1)

    def _validate_and_enhance(self, medications: List[Dict], raw_text: str) -> List[Dict]:
        """Final validation and enhancement of parsed medications"""
        enhanced = []

        for med in medications:
            # Clean and standardize medication name
            if 'name' in med:
                med['name'] = self._clean_medication_name(med['name'])

            # Standardize strength format
            if 'strength' in med:
                med['strength'] = self._clean_strength(med['strength'])

            # Standardize form
            if 'form' in med:
                med['form'] = self._standardize_form(med['form'])

            # Add confidence score
            med['confidence'] = self._calculate_confidence(med, raw_text)

            enhanced.append(med)

        # Sort by confidence (highest first)
        enhanced.sort(key=lambda x: x.get('confidence', 0), reverse=True)

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