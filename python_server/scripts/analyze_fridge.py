import os
import sys
import logging
import base64

# Setup basic logging to stdout
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add current dir to path
sys.path.append(os.getcwd())

# Set credentials explicitly
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/habtamu/Downloads/my-pharmacy-473609-3071e9bf2d97.json'

from floor_stock_parser import FloorStockParser
from google_vision_ocr import GoogleVisionOCR
from medication_location_lookup import get_location_lookup

def analyze_images():
    base_path = "/Users/habtamu/.gemini/antigravity/brain/497d9011-b76a-45a0-8b50-8c771f698ad1"
    images = [
        "uploaded_image_0_1765094939627.jpg",
        "uploaded_image_1_1765094939627.jpg",
        "uploaded_image_2_1765094939627.jpg",
        "uploaded_image_3_1765094939627.jpg"
    ]
    
    ocr_engine = GoogleVisionOCR()
    parser = FloorStockParser()
    lookup = get_location_lookup()
    
    print("=== STARTING FRIDGE ANALYSIS ===")
    
    for img_name in images:
        full_path = os.path.join(base_path, img_name)
        if not os.path.exists(full_path):
            print(f"File not found: {full_path}")
            continue
            
        print(f"\nScanning: {img_name}")
        try:
            with open(full_path, 'rb') as f:
                image_bytes = f.read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                
            # 1. OCR
            print("  Running OCR...")
            ocr_result = ocr_engine.extract_text_from_image(image_bytes)
            raw_text = ocr_result.get('text', '')
            
            # 2. Parse
            print("  Parsing text...")
            meds = parser.parse(raw_text, ocr_result.get('raw_response'))
            
            if meds:
                print(f"  Found {len(meds)} items:")
                for med in meds:
                    name = med.get('name')
                    # Check location logic
                    loc = lookup.find_location(name, med.get('strength'), med.get('form'))
                    loc_code = loc['location_code'] if loc else "UNKNOWN"
                    print(f"    - {name} -> {loc_code}")
            else:
                print(f"  No medications found by parser.")
                print("  RAW TEXT DUMP:")
                print(raw_text)
                
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    analyze_images()
