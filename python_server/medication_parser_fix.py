def fix_common_ocr_errors(text):
    """Fix common OCR errors in medication text"""
    import re
    # Common OCR character substitutions
    ocr_fixes = {
        'isinopnl': 'lisinopril',
        'tabiel': 'tablet',
        'tabiet': 'tablet', 
        'tabiets': 'tablets',
        'gma': 'mg',
        'Omg': '0mg',
        'tT': '1',
        'Acmin': 'Admin',
        'rng': 'mg',
        'rnL': 'mL',
        'mcq': 'mcg'
    }
    
    result = text
    for error, correction in ocr_fixes.items():
        result = re.sub(r'\b' + re.escape(error) + r'\b', correction, result, flags=re.IGNORECASE)
    
    return result

def parse_medication_text(text):
    """Parse a single line for medication info - enhanced for OCR errors"""
    import re
    import logging
    logger = logging.getLogger(__name__)
    
    # Clean up common OCR errors first
    original_text = text
    text = fix_common_ocr_errors(text)
    
    if text != original_text:
        logger.info(f"OCR correction: '{original_text}' -> '{text}'")
    
    # Pattern 1: "Medication: Name dose form" (like our test image)
    pattern1 = r'Medication[:\s]*([A-Za-z\s]+?)\s+(\d+\s*(?:mg|mcg|g|mL|Omg))\s*(\w+)?'
    match = re.search(pattern1, text, re.IGNORECASE)
    
    if match:
        result = {
            'name': match.group(1).strip(),
            'strength': match.group(2).strip().replace('Omg', '0mg'),
            'form': match.group(3).strip() if match.group(3) else 'tablet'
        }
        logger.info(f"Pattern 1 match: {result}")
        return result
    
    # Pattern 2: medication (BRAND) dose form
    pattern2 = r'([A-Za-z]+)\s*\(([^)]+)\)\s*(\d+\s*(?:mg|mcg|g|mL))\s*(\w+)?'
    match = re.search(pattern2, text, re.IGNORECASE)
    
    if match:
        result = {
            'name': match.group(1).strip(),
            'brand': match.group(2).strip(),
            'strength': match.group(3).strip(),
            'form': match.group(4).strip() if match.group(4) else 'tablet'
        }
        logger.info(f"Pattern 2 match: {result}")
        return result
    
    # Pattern 3: medication dose form (general) - more flexible
    pattern3 = r'([A-Za-z][A-Za-z\s]{2,})\s+(\d+\s*(?:mg|mcg|g|mL|Omg))\s*([A-Za-z]{3,})?'
    match = re.search(pattern3, text, re.IGNORECASE)
    
    if match:
        name = match.group(1).strip()
        strength = match.group(2).strip().replace('Omg', '0mg')
        form = match.group(3).strip() if match.group(3) else 'tablet'
        
        # Skip common non-medication words
        skip_words = ['patient', 'quantity', 'directions', 'take', 'pharmacy', 'label', 'daily', 'dose', 'admin', 'medication']
        if name.lower() not in skip_words:
            result = {
                'name': name,
                'strength': strength,
                'form': form
            }
            logger.info(f"Pattern 3 match: {result}")
            return result
    
    # Pattern 4: dose + quantity + form (like "5mg 1 tablet")
    pattern4 = r'(\d+\s*(?:mg|mcg|g|mL))\s+(\d+)\s+([A-Za-z]{3,})'
    match = re.search(pattern4, text, re.IGNORECASE)
    
    if match:
        result = {
            'name': 'Unknown',  # Will need to be filled from context
            'strength': match.group(1).strip(),
            'quantity': match.group(2).strip(),
            'form': match.group(3).strip()
        }
        logger.info(f"Pattern 4 match: {result}")
        return result
    
    logger.info(f"No medication pattern matched for: '{text}'")
    return None
