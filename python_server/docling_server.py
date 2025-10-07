#!/usr/bin/env python3
"""
Docling-based OCR server for Pharmacy Picker Flutter app
Provides advanced document parsing for medication labels and pick lists
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import base64
from docling.document_converter import DocumentConverter
import json
import logging
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Google Vision OCR
from google_vision_ocr import GoogleVisionOCR

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

# Initialize Google Vision OCR (will auto-detect credentials)
google_vision = GoogleVisionOCR()
logger.info("Google Vision OCR initialized")

# Initialize Docling converter with explicit OCR configuration
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.models.ocr_mac_model import OcrMacOptions
from docling.models.tesseract_ocr_model import TesseractOcrOptions
from medspacy_parser import parse_medications_with_medspacy

# Configure pipeline options for better OCR
pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True  # Ensure OCR is enabled
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True

# Use Google Cloud Vision OCR if credentials are available
if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
    logger.info("Using Google Cloud Vision OCR engine")
    try:
        from docling.models.gcs_ocr_model import GcsOcrOptions
        ocr_options = GcsOcrOptions()
        pipeline_options.ocr_options = ocr_options
        logger.info("✓ Google Cloud Vision OCR configured successfully")
    except ImportError:
        logger.warning("Google Cloud Vision OCR not available, falling back to default")
        # Continue to fallback options below
    except Exception as e:
        logger.warning(f"Could not configure Google Cloud Vision OCR: {e}")
        # Continue to fallback options below

if not hasattr(pipeline_options, 'ocr_options') or pipeline_options.ocr_options is None:
    # Try to use the best available local OCR engine
    try:
        # Prefer Tesseract OCR for better text recognition
        ocr_options = TesseractOcrOptions()
        pipeline_options.ocr_options = ocr_options
        logger.info("Using Tesseract OCR engine")
    except Exception as e:
        logger.warning(f"Could not configure Tesseract OCR: {e}")
        try:
            # Fallback to Mac OCR if available
            ocr_options = OcrMacOptions()
            pipeline_options.ocr_options = ocr_options
            logger.info("Using Mac OCR engine")
        except Exception as e2:
            logger.warning(f"Could not configure Mac OCR: {e2}")
            logger.info("Using default OCR configuration")

# Initialize converter with OCR-focused configuration
format_options = {
    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
}

converter = DocumentConverter(
    format_options=format_options
)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'docling-ocr'})

@app.route('/parse-document', methods=['POST'])
def parse_document():
    """
    Parse medication documents using Enhanced Medication Parser
    Expects: JSON with base64 encoded image and mode
    Returns: Structured medication data
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Handle base64 image data
        if 'image_base64' in data:
            image_data = base64.b64decode(data['image_base64'])
            mode = data.get('mode', 'cart_fill')
            strategy = data.get('strategy', 'google_vision')

            logger.info(f"=== STARTING OCR WITH GOOGLE VISION ===")
            logger.info(f"Mode: {mode}, Image size: {len(image_data)} bytes")

            # Step 1: Extract text using Google Vision
            ocr_result = google_vision.extract_text_from_image(image_data)

            if not ocr_result['success']:
                logger.error(f"Google Vision OCR failed: {ocr_result.get('error', 'Unknown error')}")
                return jsonify({
                    'success': False,
                    'error': f"OCR failed: {ocr_result.get('error', 'Unknown error')}",
                    'medications': [],
                    'raw_text': ''
                }), 500

            raw_text = ocr_result['text']
            logger.info(f"✓ OCR extracted {len(raw_text)} characters")
            logger.info(f"  Text preview: {raw_text[:200]}...")

            # Step 2: Parse medications from extracted text
            if mode == 'floor_stock':
                # Use dedicated floor stock parser for BD pick lists
                from floor_stock_parser import FloorStockParser
                parser = FloorStockParser()
                validated_medications = parser.parse(raw_text)
            else:
                # Use enhanced medication parser for cart-fill labels
                from enhanced_medication_parser import EnhancedMedicationParser
                parser = EnhancedMedicationParser()

                # Use parser's validation and enhancement
                medications = parser._parse_with_best_llm(raw_text, mode)

                # If LLM parsing fails, try regex fallback
                if not medications:
                    logger.info("LLM parsing returned no results, trying regex fallback")
                    medications = parser._parse_with_regex_fallback(raw_text, mode)

                # Validate and enhance results
                validated_medications = parser._validate_and_enhance(medications, raw_text)

            logger.info(f"✓ Parsing complete: {len(validated_medications)} medications found")
            if validated_medications:
                for i, med in enumerate(validated_medications):
                    logger.info(f"  {i+1}. {med.get('name', 'Unknown')} - {med.get('strength', '')} - {med.get('form', '')} - Pick: {med.get('pick_amount', 'N/A')}")

            return jsonify({
                'success': True,
                'medications': validated_medications,
                'raw_text': raw_text,
                'method': 'google_vision',
                'ocr_confidence': ocr_result.get('confidence', 0.95),
                'word_count': ocr_result.get('word_count', 0)
            })

        else:
            return jsonify({'error': 'No image_base64 provided'}), 400

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return jsonify({'error': str(e)}), 500

def extract_medication_data(docling_result, mode='cart_fill'):
    """
    Extract medication information from Docling result
    """
    medications = []
    
    try:
        # Get document structure
        doc_dict = docling_result.document.export_to_dict()
        
        # Extract text content
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
    
    # Look for table structures in document
    if 'tables' in doc_dict:
        for table in doc_dict['tables']:
            medications.extend(parse_table_for_medications(table))
    
    # Fallback to text parsing
    if not medications:
        medications = parse_text_for_floor_stock(text_content)
    
    return medications

def parse_cart_fill_data(doc_dict, text_content):
    """Parse cart-fill medication labels using medspaCy"""
    medications = []
    
    logger.info("Using medspaCy for medication extraction")
    
    # Try table parsing first
    if 'tables' in doc_dict and doc_dict['tables']:
        for table in doc_dict['tables']:
            table_meds = parse_table_for_medications(table)
            medications.extend(table_meds)
    
    # Use medspaCy for text parsing (primary method)
    try:
        medspacy_meds = parse_medications_with_medspacy(text_content)
        medications.extend(medspacy_meds)
        logger.info(f"medspaCy extracted {len(medspacy_meds)} medications")
    except Exception as e:
        logger.error(f"medspaCy parsing failed: {e}")
        # Fallback to custom parsing if medspaCy fails
        medications.extend(parse_text_for_medications(text_content))
    
    return medications

def parse_table_for_medications(table):
    """Extract medications from table structure"""
    medications = []
    
    try:
        rows = table.get('rows', [])
        if len(rows) < 2:  # Need header + data
            return medications
            
        # Assume first row is header
        headers = [cell.get('text', '').lower() for cell in rows[0].get('cells', [])]
        
        # Find relevant columns
        name_col = find_column_index(headers, ['medication', 'drug', 'name', 'description'])
        dose_col = find_column_index(headers, ['dose', 'strength', 'mg', 'mcg'])
        qty_col = find_column_index(headers, ['quantity', 'qty', 'pick', 'amount'])
        floor_col = find_column_index(headers, ['floor', 'location', 'unit'])
        
        # Process data rows
        for row in rows[1:]:
            cells = row.get('cells', [])
            if len(cells) > max(name_col or 0, dose_col or 0):
                med_data = {
                    'name': cells[name_col].get('text', '') if name_col is not None else '',
                    'strength': cells[dose_col].get('text', '') if dose_col is not None else '',
                    'quantity': cells[qty_col].get('text', '1') if qty_col is not None else '1',
                    'floor': cells[floor_col].get('text', '') if floor_col is not None else '',
                    'form': 'tablet'  # Default
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
    import re
    medications = []
    
    lines = text.split('\n')
    for line in lines:
        # Pattern for: medication dose floor quantity
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
    import re
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
    
    # Pattern 2: medication (BRAND) dose form - handle ## prefix and multiple brands
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

def convert_image_to_pdf(image_data):
    """Convert image bytes to PDF file for Docling processing"""
    try:
        logger.info(f"Converting image to PDF, input size: {len(image_data)} bytes")
        
        # Open image from bytes
        image = Image.open(io.BytesIO(image_data))
        logger.info(f"Original image: {image.size} pixels, mode: {image.mode}")
        
        # Handle PNG with transparency
        if image.mode in ('RGBA', 'LA', 'P'):
            logger.info(f"Converting {image.mode} to RGB with white background")
            # Create white background for transparent images
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            logger.info(f"Converting {image.mode} to RGB")
            image = image.convert('RGB')
        
        # Auto-rotate image based on EXIF data (important for mobile photos)
        try:
            from PIL import ImageOps
            image = ImageOps.exif_transpose(image)
            logger.info("Applied EXIF rotation correction")
        except Exception as e:
            logger.warning(f"Could not apply EXIF rotation: {e}")
        
        # Enhance image for better OCR
        from PIL import ImageEnhance, ImageFilter
        
        # Increase contrast more aggressively for mobile photos
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)  # Increased from 1.2
        
        # Increase sharpness more for mobile photos
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)  # Increased from 1.1
        
        # Apply slight denoising
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Ensure minimum resolution for OCR
        min_width, min_height = 1200, 1600  # Minimum resolution for good OCR
        if image.size[0] < min_width or image.size[1] < min_height:
            # Calculate scale factor to reach minimum resolution
            scale_x = min_width / image.size[0] if image.size[0] < min_width else 1
            scale_y = min_height / image.size[1] if image.size[1] < min_height else 1
            scale = max(scale_x, scale_y)
            
            new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Upscaled image to {new_size} for better OCR")
        
        logger.info(f"Final processed image: {image.size} pixels")
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            pdf_path = temp_pdf.name
        
        # Create PDF with image
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Get image dimensions and scale to fit page
        img_width, img_height = image.size
        page_width, page_height = letter
        
        # Calculate scaling to fit page while maintaining aspect ratio
        scale_x = page_width / img_width
        scale_y = page_height / img_height
        scale = min(scale_x, scale_y) * 0.9  # 90% of page to leave margins
        
        new_width = img_width * scale
        new_height = img_height * scale
        
        # Center image on page
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2
        
        # Save image to temporary file for PDF creation
        # Use PNG for better quality preservation, especially for text
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_img:
            image.save(temp_img.name, 'PNG')
            temp_img_path = temp_img.name
        
        try:
            # Add image to PDF
            c.drawImage(temp_img_path, x, y, width=new_width, height=new_height)
            c.save()
        finally:
            # Clean up temporary image file
            os.unlink(temp_img_path)
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"Error converting image to PDF: {str(e)}")
        raise

if __name__ == '__main__':
    print("Starting Enhanced OCR Server with Google Vision...")
    print("Server will be available at: http://localhost:5003")
    print("Health check: http://localhost:5003/health")
    app.run(host='0.0.0.0', port=5003, debug=True)
