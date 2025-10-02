#!/usr/bin/env python3
"""
medspaCy-based medication parser for pharmacy labels
Replaces custom regex patterns with clinical NLP
"""

import medspacy
from medspacy.ner import TargetRule
import logging

logger = logging.getLogger(__name__)

class MedspacyMedicationParser:
    def __init__(self):
        """Initialize medspaCy model with medication extraction rules"""
        try:
            # Load medspacy model
            self.nlp = medspacy.load()
            logger.info("medspaCy model loaded successfully")
            
            # Get the target matcher component
            self.target_matcher = self.nlp.get_pipe("medspacy_target_matcher")
            
            # Define medication extraction rules
            self._setup_medication_rules()
            
        except Exception as e:
            logger.error(f"Error initializing medspaCy parser: {e}")
            raise
    
    def _setup_medication_rules(self):
        """Setup medication extraction rules for pharmacy labels"""
        
        # Dynamic medication pattern rules (no hardcoding)
        medication_rules = [
            # Generic medication patterns - matches any word that looks like a medication
            TargetRule("medication", "MEDICATION", pattern=[
                {"IS_ALPHA": True, "LENGTH": {">=": 4}, "IS_LOWER": True}
            ]),
            
            # Dosage patterns
            TargetRule("dosage", "DOSAGE", pattern=[
                {"LIKE_NUM": True}, 
                {"LOWER": {"IN": ["mg", "mcg", "g", "ml", "gma", "rng"]}}
            ]),
            
            # Forms
            TargetRule("tablet", "FORM"),
            TargetRule("capsule", "FORM"),
            TargetRule("liquid", "FORM"),
            TargetRule("injection", "FORM"),
            
            # Handle OCR errors for tablet
            TargetRule("tablet", "FORM", pattern=[{"LOWER": {"IN": ["tabiel", "tabiet", "tabiets"]}}]),
            
            # Quantities
            TargetRule("quantity", "QUANTITY", pattern=[
                {"LIKE_NUM": True},
                {"LOWER": {"IN": ["tablet", "tablets", "capsule", "capsules", "tabiel", "tabiets"]}}
            ]),
            
            # Instructions
            TargetRule("daily", "FREQUENCY"),
            TargetRule("twice daily", "FREQUENCY"),
            TargetRule("as needed", "FREQUENCY"),
            TargetRule("bedtime", "FREQUENCY"),
        ]
        
        # Add all rules to the target matcher
        self.target_matcher.add(medication_rules)
        logger.info(f"Added {len(medication_rules)} medication extraction rules")
    
    def parse_medications(self, text):
        """
        Parse medications from OCR text using medspaCy
        
        Args:
            text (str): OCR extracted text from medication label
            
        Returns:
            list: List of medication dictionaries with extracted information
        """
        try:
            logger.info(f"Parsing text with medspaCy: '{text[:100]}...'")
            
            # Process text with medspaCy
            doc = self.nlp(text)
            
            # Extract entities
            medications = []
            medication_info = {}
            
            # Group entities by type
            for ent in doc.ents:
                logger.info(f"Found entity: '{ent.text}' -> {ent.label_}")
                
                if ent.label_ == "MEDICATION":
                    medication_info["name"] = ent.text
                elif ent.label_ == "DOSAGE":
                    medication_info["strength"] = ent.text
                elif ent.label_ == "FORM":
                    medication_info["form"] = ent.text
                elif ent.label_ == "QUANTITY":
                    medication_info["quantity"] = ent.text
                elif ent.label_ == "FREQUENCY":
                    medication_info["frequency"] = ent.text
            
            # If we found medication information, create a medication object
            if medication_info:
                # Set defaults for missing fields
                medication_info.setdefault("name", "Unknown")
                medication_info.setdefault("form", "tablet")
                medication_info.setdefault("strength", "Unknown")
                
                medications.append(medication_info)
                logger.info(f"Extracted medication: {medication_info}")
            
            # Also try to extract from individual sentences/lines
            for sent in doc.sents:
                sent_text = sent.text.strip()
                if sent_text and len(sent_text) > 5:  # Skip very short lines
                    sent_meds = self._parse_line_with_patterns(sent_text)
                    for med in sent_meds:
                        if med not in medications:
                            medications.append(med)
            
            logger.info(f"Total medications extracted: {len(medications)}")
            return medications
            
        except Exception as e:
            logger.error(f"Error parsing medications with medspaCy: {e}")
            return []
    
    def _parse_line_with_patterns(self, line):
        """
        Parse individual lines with medical context and fuzzy matching
        
        Args:
            line (str): Single line of text
            
        Returns:
            list: List of medication dictionaries
        """
        medications = []
        
        # Process line with medspaCy
        doc = self.nlp(line)
        
        # Look for medication + dosage + form patterns
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        
        # Simple pattern: if we have medication and dosage in same line
        med_name = None
        dosage = None
        form = None
        
        for text, label in entities:
            if label == "MEDICATION":
                med_name = text
            elif label == "DOSAGE":
                dosage = text
            elif label == "FORM":
                form = text
        
        # If no medication found by medspaCy, try intelligent word analysis
        if not med_name:
            med_name = self._find_medication_in_text(line, doc)
        
        if med_name and (dosage or form):
            medication = {
                "name": med_name,
                "strength": dosage or "Unknown",
                "form": form or "tablet"
            }
            medications.append(medication)
            logger.info(f"Line pattern match: {medication}")
        
        return medications
    
    def _find_medication_in_text(self, line, doc):
        """
        Intelligently find medication names using medical context and patterns
        
        Args:
            line (str): Text line to analyze
            doc: spaCy processed document
            
        Returns:
            str or None: Medication name if found
        """
        import re
        
        # Look for words that have medical/pharmaceutical characteristics
        words = line.split()
        
        for word in words:
            # Clean the word
            clean_word = re.sub(r'[^a-zA-Z]', '', word).lower()
            
            # Skip very short words or common non-medication words
            if len(clean_word) < 4:
                continue
                
            # Skip common non-medication words
            if clean_word in ['medication', 'dose', 'admin', 'daily', 'tablet', 'capsule', 'image']:
                continue
            
            # Check if word has pharmaceutical characteristics
            if self._looks_like_medication(clean_word):
                logger.info(f"Found potential medication: '{clean_word}' from '{word}'")
                return clean_word
        
        return None
    
    def _looks_like_medication(self, word):
        """
        Determine if a word looks like a medication name using precise pharmaceutical patterns
        
        Args:
            word (str): Word to analyze
            
        Returns:
            bool: True if word looks like a medication
        """
        word_lower = word.lower()
        
        # Exclude common non-medication words first
        excluded_words = {
            'tablet', 'capsule', 'liquid', 'injection', 'cream', 'ointment',
            'image', 'medication', 'dose', 'admin', 'daily', 'morning', 'evening',
            'patient', 'doctor', 'pharmacy', 'hospital', 'mount', 'sinai', 'morningside',
            'tech', 'label', 'prescription', 'refill'
        }
        
        if word_lower in excluded_words:
            return False
        
        # Common pharmaceutical suffixes (more specific)
        pharma_suffixes = ['pril', 'statin', 'olol', 'pine', 'zole', 'mycin', 'cillin', 'oxin', 'azole']
        
        # Check for pharmaceutical suffixes
        for suffix in pharma_suffixes:
            if word_lower.endswith(suffix) and len(word) >= len(suffix) + 2:
                return True
        
        # Common pharmaceutical patterns within words
        pharma_patterns = ['pril', 'statin', 'mycin', 'cillin', 'zole', 'olol']
        for pattern in pharma_patterns:
            if pattern in word_lower and len(word) >= 6:
                return True
        
        # Check for typical medication characteristics
        if len(word) >= 6 and word.isalpha():
            # Medications often have specific letter patterns
            vowel_count = sum(1 for c in word_lower if c in 'aeiou')
            
            # Good vowel distribution and reasonable length
            if 0.25 <= vowel_count / len(word) <= 0.5 and len(word) <= 15:
                # Additional checks for medication-like characteristics
                has_double_letters = any(word_lower[i] == word_lower[i+1] for i in range(len(word_lower)-1))
                has_common_endings = word_lower.endswith(('in', 'ol', 'al', 'an', 'on', 'il'))
                
                if has_common_endings or not has_double_letters:
                    return True
        
        return False

# Global parser instance
_parser = None

def get_medspacy_parser():
    """Get or create medspaCy parser instance"""
    global _parser
    if _parser is None:
        _parser = MedspacyMedicationParser()
    return _parser

def parse_medications_with_medspacy(text):
    """
    Parse medications from text using medspaCy
    
    Args:
        text (str): OCR extracted text
        
    Returns:
        list: List of medication dictionaries
    """
    parser = get_medspacy_parser()
    return parser.parse_medications(text)
