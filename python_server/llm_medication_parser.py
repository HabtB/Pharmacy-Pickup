#!/usr/bin/env python3
"""
LLM-based medication parser using Grok API
Provides intelligent, context-aware medication extraction from pharmacy labels
"""

import os
import json
import logging
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class LLMMedicationParser:
    def __init__(self):
        """Initialize LLM medication parser with Grok API"""
        self.api_key = os.getenv('GROK_API_KEY')
        if not self.api_key:
            logger.error("GROK_API_KEY not found in environment variables")
            raise ValueError("GROK_API_KEY is required for LLM medication parsing")
        
        # Try different possible Grok API endpoints
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"  # Groq endpoint
        # Alternative: self.api_url = "https://api.x.ai/v1/chat/completions"  # X.AI endpoint
        logger.info("LLM medication parser initialized with Grok API")
    
    def parse_medications(self, ocr_text: str) -> List[Dict]:
        """
        Parse medications from OCR text using LLM intelligence
        
        Args:
            ocr_text (str): Raw OCR text from medication label
            
        Returns:
            List[Dict]: List of medication dictionaries with extracted information
        """
        try:
            logger.info(f"Parsing medications with LLM from text: '{ocr_text[:100]}...'")
            
            # Create intelligent prompt for medication extraction
            prompt = self._create_medication_prompt(ocr_text)
            
            # Call Grok API
            response = self._call_grok_api(prompt)
            
            # Parse LLM response
            medications = self._parse_llm_response(response)
            
            logger.info(f"LLM extracted {len(medications)} medications")
            for i, med in enumerate(medications, 1):
                logger.info(f"  {i}. {med}")
            
            return medications
            
        except Exception as e:
            logger.error(f"Error in LLM medication parsing: {e}")
            return []
    
    def _create_medication_prompt(self, ocr_text: str) -> str:
        """
        Create an intelligent prompt for medication extraction
        
        Args:
            ocr_text (str): OCR text to analyze
            
        Returns:
            str: Formatted prompt for LLM
        """
        prompt = f"""You are a medical expert analyzing a pharmacy medication label. Extract medication information from this OCR text and return it as valid JSON.

OCR Text:
{ocr_text}

Instructions:
1. Extract ALL medications mentioned in the text
2. For each medication, provide:
   - name: Generic medication name (prefer generic over brand names)
   - brand: Brand name(s) if mentioned (in parentheses in original)
   - strength: Dosage strength (e.g., "5 mg", "10 mg")
   - form: Medication form (e.g., "tablet", "capsule", "liquid")
   - frequency: How often to take (convert abbreviations: QD→"once daily", BID→"twice daily", TID→"three times daily", QID→"four times daily", QAM→"every morning", QPM→"every evening", PRN→"as needed")
   - quantity: Number of units (e.g., "30 tablets", "1 tablet")
   - instructions: Any additional dosing instructions

3. Handle OCR errors intelligently (e.g., "figinopriL" → "lisinopril")
4. Ignore non-medication text (hospital names, dates, tech info, etc.)
5. Convert medical abbreviations to readable text

Return ONLY valid JSON in this format:
{{
  "medications": [
    {{
      "name": "medication_name",
      "brand": "brand_name_if_any",
      "strength": "dosage",
      "form": "form",
      "frequency": "frequency_description",
      "quantity": "quantity_description",
      "instructions": "additional_instructions"
    }}
  ]
}}

Do not include any explanation, only the JSON response."""

        return prompt
    
    def _call_grok_api(self, prompt: str) -> str:
        """
        Call Grok API with the medication extraction prompt
        
        Args:
            prompt (str): Formatted prompt
            
        Returns:
            str: LLM response text
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": "llama-3.1-70b-versatile",  # Groq model
            "stream": False,
            "temperature": 0.1  # Low temperature for consistent, factual extraction
        }
        
        logger.info("Calling Grok API for medication extraction...")
        
        response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        logger.info(f"Grok API response received: {len(content)} characters")
        return content
    
    def _parse_llm_response(self, response_text: str) -> List[Dict]:
        """
        Parse LLM response and extract medication data
        
        Args:
            response_text (str): Raw LLM response
            
        Returns:
            List[Dict]: Parsed medication list
        """
        try:
            # Clean response text (remove any markdown formatting)
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Parse JSON
            parsed_data = json.loads(clean_text)
            
            medications = parsed_data.get('medications', [])
            
            # Validate and clean medication data
            validated_medications = []
            for med in medications:
                if self._validate_medication(med):
                    validated_medications.append(self._clean_medication_data(med))
            
            return validated_medications
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.error(f"Raw response: {response_text}")
            return []
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return []
    
    def _validate_medication(self, med_data: Dict) -> bool:
        """
        Validate medication data structure
        
        Args:
            med_data (Dict): Medication data to validate
            
        Returns:
            bool: True if valid medication data
        """
        required_fields = ['name']
        
        # Check if medication has at least a name
        if not med_data.get('name') or med_data['name'].lower() in ['unknown', 'none', '']:
            return False
        
        # Skip if name is clearly not a medication
        invalid_names = ['tablet', 'capsule', 'image', 'medication', 'dose', 'admin', 'daily']
        if med_data['name'].lower() in invalid_names:
            return False
        
        return True
    
    def _clean_medication_data(self, med_data: Dict) -> Dict:
        """
        Clean and standardize medication data
        
        Args:
            med_data (Dict): Raw medication data
            
        Returns:
            Dict: Cleaned medication data
        """
        cleaned = {
            'name': med_data.get('name', 'Unknown').strip(),
            'brand': med_data.get('brand', '').strip(),
            'strength': med_data.get('strength', 'Unknown').strip(),
            'form': med_data.get('form', 'tablet').strip().lower(),
            'frequency': med_data.get('frequency', '').strip(),
            'quantity': med_data.get('quantity', '').strip(),
            'instructions': med_data.get('instructions', '').strip()
        }
        
        # Remove empty fields
        cleaned = {k: v for k, v in cleaned.items() if v and v != 'Unknown'}
        
        # Ensure we have at least name and form
        cleaned.setdefault('form', 'tablet')
        
        return cleaned

# Global parser instance
_llm_parser = None

def get_llm_parser():
    """Get or create LLM parser instance"""
    global _llm_parser
    if _llm_parser is None:
        _llm_parser = LLMMedicationParser()
    return _llm_parser

def parse_medications_with_llm(text: str) -> List[Dict]:
    """
    Parse medications from text using LLM
    
    Args:
        text (str): OCR extracted text
        
    Returns:
        List[Dict]: List of medication dictionaries
    """
    parser = get_llm_parser()
    return parser.parse_medications(text)
