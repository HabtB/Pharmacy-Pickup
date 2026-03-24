"""
Text and table parsing utilities for medication extraction.
"""
import re
import logging

logger = logging.getLogger(__name__)


def extract_medication_data(docling_result, mode='cart_fill'):
    """Extract medication information from Docling result"""
    medications = []

    try:
        doc_dict = docling_result.document.export_to_dict()
        text_content = docling_result.document.export_to_markdown()

        if mode == 'floor_stock':
            medications = parse_floor_stock_data(doc_dict, text_content)
        else:
            medications = parse_cart_fill_data(doc_dict, text_content)

    except Exception as e:
        logger.error(f"Error extracting medication data: {str(e)}")

    return medications


def parse_floor_stock_data(doc_dict, text_content):
    """Parse floor stock pick lists (tabular format)"""
    medications = []

    if 'tables' in doc_dict:
        for table in doc_dict['tables']:
            medications.extend(parse_table_for_medications(table))

    if not medications:
        medications = parse_text_for_floor_stock(text_content)

    return medications


def parse_cart_fill_data(doc_dict, text_content):
    """Parse cart-fill medication labels using medspaCy"""
    from medspacy_parser import parse_medications_with_medspacy

    medications = []

    logger.info("Using medspaCy for medication extraction")

    if 'tables' in doc_dict and doc_dict['tables']:
        for table in doc_dict['tables']:
            table_meds = parse_table_for_medications(table)
            medications.extend(table_meds)

    try:
        medspacy_meds = parse_medications_with_medspacy(text_content)
        medications.extend(medspacy_meds)
        logger.info(f"medspaCy extracted {len(medspacy_meds)} medications")
    except Exception as e:
        logger.error(f"medspaCy parsing failed: {e}")
        medications.extend(parse_text_for_medications(text_content))

    return medications


def parse_table_for_medications(table):
    """Extract medications from table structure"""
    medications = []

    try:
        rows = table.get('rows', [])
        if len(rows) < 2:
            return medications

        headers = [cell.get('text', '').lower() for cell in rows[0].get('cells', [])]

        name_col = find_column_index(headers, ['medication', 'drug', 'name', 'description'])
        dose_col = find_column_index(headers, ['dose', 'strength', 'mg', 'mcg'])
        qty_col = find_column_index(headers, ['quantity', 'qty', 'pick', 'amount'])
        floor_col = find_column_index(headers, ['floor', 'location', 'unit'])

        for row in rows[1:]:
            cells = row.get('cells', [])
            if len(cells) > max(name_col or 0, dose_col or 0):
                med_data = {
                    'name': cells[name_col].get('text', '') if name_col is not None else '',
                    'strength': cells[dose_col].get('text', '') if dose_col is not None else '',
                    'quantity': cells[qty_col].get('text', '1') if qty_col is not None else '1',
                    'floor': cells[floor_col].get('text', '') if floor_col is not None else '',
                    'form': 'tablet'
                }

                if med_data['name']:
                    medications.append(med_data)

    except Exception as e:
        logger.error(f"Error parsing table: {str(e)}")

    return medications


def find_column_index(headers, keywords):
    """Find column index by keywords"""
    for i, header in enumerate(headers):
        for keyword in keywords:
            if keyword in header:
                return i
    return None


def parse_text_for_floor_stock(text):
    """Parse text for floor stock format"""
    medications = []

    lines = text.split('\n')
    for line in lines:
        pattern = r'([A-Za-z\s]+)\s+(\d+\s*(?:mg|mcg|g|mL))\s+(\d+[EW]\d*)\s+(\d+)'
        match = re.search(pattern, line, re.IGNORECASE)

        if match:
            medications.append({
                'name': match.group(1).strip(),
                'strength': match.group(2).strip(),
                'floor': match.group(3).strip(),
                'quantity': match.group(4).strip(),
                'form': 'tablet'
            })

    return medications


def parse_text_for_medications(text):
    """Parse text for individual medications"""
    medications = []

    logger.info(f"Parsing text with {len(text.split())} words")

    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if line:
            logger.info(f"Line {i+1}: '{line}'")
            med_data = parse_medication_text(line)
            if med_data:
                logger.info(f"  -> Found medication: {med_data}")
                medications.append(med_data)
            else:
                logger.info(f"  -> No medication found")

    return medications


def fix_common_ocr_errors(text):
    """Fix common OCR errors in medication text"""
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
    original_text = text
    text = fix_common_ocr_errors(text)

    if text != original_text:
        logger.info(f"OCR correction: '{original_text}' -> '{text}'")

    # Pattern 1: "Medication: Name dose form"
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
    pattern2 = r'#{0,2}\s*([A-Za-z]+)\s*\(([^)]+)\)\s*([A-Za-z]+)\s*(\d+\s*(?:mg|mcg|g|mL))'
    match = re.search(pattern2, text, re.IGNORECASE)

    if match:
        result = {
            'name': match.group(1).strip(),
            'brand': match.group(2).strip(),
            'form': match.group(3).strip(),
            'strength': match.group(4).strip()
        }
        logger.info(f"Pattern 2 match: {result}")
        return result

    # Pattern 3: medication dose form (general)
    pattern3 = r'([A-Za-z][A-Za-z\s]{2,})\s+(\d+\s*(?:mg|mcg|g|mL|Omg))\s*([A-Za-z]{3,})?'
    match = re.search(pattern3, text, re.IGNORECASE)

    if match:
        name = match.group(1).strip()
        strength = match.group(2).strip().replace('Omg', '0mg')
        form = match.group(3).strip() if match.group(3) else 'tablet'

        skip_words = ['patient', 'quantity', 'directions', 'take', 'pharmacy', 'label', 'daily', 'dose', 'admin', 'medication']
        if name.lower() not in skip_words:
            result = {
                'name': name,
                'strength': strength,
                'form': form
            }
            logger.info(f"Pattern 3 match: {result}")
            return result

    # Pattern 4: dose + quantity + form
    pattern4 = r'(\d+\s*(?:mg|mcg|g|mL))\s+(\d+)\s+([A-Za-z]{3,})'
    match = re.search(pattern4, text, re.IGNORECASE)

    if match:
        result = {
            'name': 'Unknown',
            'strength': match.group(1).strip(),
            'quantity': match.group(2).strip(),
            'form': match.group(3).strip()
        }
        logger.info(f"Pattern 4 match: {result}")
        return result

    logger.info(f"No medication pattern matched for: '{text}'")
    return None
