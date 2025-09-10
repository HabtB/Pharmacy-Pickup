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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

# Initialize Docling converter
converter = DocumentConverter()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'docling-ocr'})

@app.route('/parse-document', methods=['POST'])
def parse_document():
    """
    Parse medication documents using Docling
    Expects: JSON with base64 encoded image or file path
    Returns: Structured medication data
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Handle base64 image data
        if 'image_base64' in data:
            image_data = base64.b64decode(data['image_base64'])
            
            # Convert image to PDF (Docling's preferred format)
            pdf_path = convert_image_to_pdf(image_data)
                
            try:
                # Process with Docling
                result = converter.convert(pdf_path)
                
                # Extract structured data
                structured_data = extract_medication_data(result, data.get('mode', 'cart_fill'))
                
                # Debug logging
                raw_text = result.document.export_to_markdown()
                print(f"\n=== DOCLING OCR RESULT ===")
                print(f"Raw text extracted: '{raw_text}'")
                print(f"Text length: {len(raw_text)} characters")
                print(f"Medications found: {len(structured_data)}")
                if structured_data:
                    for i, med in enumerate(structured_data):
                        print(f"  {i+1}. {med}")
                else:
                    print("  No medications parsed from text")
                print("=========================\n")
                
                logger.info(f"Raw OCR text: {raw_text}")
                logger.info(f"Medications found: {len(structured_data)}")
                if structured_data:
                    for i, med in enumerate(structured_data):
                        logger.info(f"  {i+1}. {med}")
                
                return jsonify({
                    'success': True,
                    'medications': structured_data,
                    'raw_text': raw_text,
                    'document_structure': result.document.export_to_dict()
                })
                
            finally:
                # Clean up temp file
                os.unlink(pdf_path)
                
        # Handle file path
        elif 'file_path' in data:
            file_path = data['file_path']
            if not os.path.exists(file_path):
                return jsonify({'error': 'File not found'}), 404
                
            result = converter.convert(file_path)
            structured_data = extract_medication_data(result, data.get('mode', 'cart_fill'))
            
            return jsonify({
                'success': True,
                'medications': structured_data,
                'raw_text': result.document.export_to_markdown(),
                'document_structure': result.document.export_to_dict()
            })
            
        else:
            return jsonify({'error': 'No image_base64 or file_path provided'}), 400
            
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
    """Parse cart-fill medication labels"""
    medications = []
    
    # Look for structured elements
    if 'elements' in doc_dict:
        for element in doc_dict['elements']:
            if element.get('type') == 'text':
                med_data = parse_medication_text(element.get('text', ''))
                if med_data:
                    medications.append(med_data)
    
    # Fallback to full text parsing
    if not medications:
        medications = parse_text_for_medications(text_content)
    
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

def parse_medication_text(text):
    """Parse a single line for medication info"""
    import re
    
    # Pattern 1: "Medication: Name dose form" (like our test image)
    pattern1 = r'Medication:\s*([A-Za-z\s]+?)\s+(\d+\s*(?:mg|mcg|g|mL|Omg))\s*(\w+)?'
    match = re.search(pattern1, text, re.IGNORECASE)
    
    if match:
        return {
            'name': match.group(1).strip(),
            'strength': match.group(2).strip().replace('Omg', '0mg'),  # Fix OCR error
            'form': match.group(3).strip() if match.group(3) else 'tablet'
        }
    
    # Pattern 2: medication (BRAND) dose form
    pattern2 = r'([A-Za-z]+)\s*\(([^)]+)\)\s*(\d+\s*(?:mg|mcg|g|mL))\s*(\w+)?'
    match = re.search(pattern2, text, re.IGNORECASE)
    
    if match:
        return {
            'name': match.group(1).strip(),
            'brand': match.group(2).strip(),
            'strength': match.group(3).strip(),
            'form': match.group(4).strip() if match.group(4) else 'tablet'
        }
    
    # Pattern 3: medication dose form (general)
    pattern3 = r'([A-Za-z\s]+?)\s+(\d+\s*(?:mg|mcg|g|mL|Omg))\s*(\w+)?'
    match = re.search(pattern3, text, re.IGNORECASE)
    
    if match:
        name = match.group(1).strip()
        # Skip common non-medication words
        if name.lower() not in ['patient', 'quantity', 'directions', 'take', 'pharmacy', 'label']:
            return {
                'name': name,
                'strength': match.group(2).strip().replace('Omg', '0mg'),  # Fix OCR error
                'form': match.group(3).strip() if match.group(3) else 'tablet'
            }
    
    return None

def convert_image_to_pdf(image_data):
    """Convert image bytes to PDF file for Docling processing"""
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_data))
        
        # Handle PNG with transparency
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparent images
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Enhance image for better OCR
        from PIL import ImageEnhance
        
        # Increase contrast for better text recognition
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
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
    print("Starting Docling OCR Server...")
    print("Server will be available at: http://localhost:5001")
    print("Health check: http://localhost:5001/health")
    app.run(host='0.0.0.0', port=5001, debug=True)
