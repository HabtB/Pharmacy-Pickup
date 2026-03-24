import os
import sys
import io
import json
from enhanced_medication_parser import EnhancedMedicationParser
from dotenv import load_dotenv
from pathlib import Path

# Load env for API keys
# Script is in python_server, so .env is in SAME directory
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

if os.getenv('GOOGLE_API_KEY'):
    print("DEBUG: GOOGLE_API_KEY found in env.")
else:
    print("DEBUG: GOOGLE_API_KEY NOT found in env!")

def analyze_store_images():
    parser = EnhancedMedicationParser()
    
    # Path to new Images directory
    images_dir = "/Users/habtamu/Documents/pharmacy_pickup_app_dev/Images"
    
    # Create results file
    results_file = "store_analysis_results.json"
    all_results = {}
    
    # Get all jpg/jpeg files
    image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg'))]
    image_files.sort()
    
    print(f"Found {len(image_files)} images to analyze.")
    
    for i, img_file in enumerate(image_files):
        print(f"\n[{i+1}/{len(image_files)}] Analyzing {img_file} ...")
        img_path = os.path.join(images_dir, img_file)
        
        try:
            with open(img_path, 'rb') as f:
                image_data = f.read()
                
            # Use 'floor_stock' mode to trigger robust multi-item extraction
            result = parser.parse_medication_label(image_data, mode='floor_stock')
            
            if result['success']:
                meds = result['medications']
                print(f"  ✓ Found {len(meds)} medications")
                
                # Determine location context from filename
                location_context = "Unknown"
                if "Main Pharmacy" in img_file:
                    if "Zone X" in img_file: location_context = "Main Pharmacy - Zone X"
                    elif "Zone Y" in img_file: location_context = "Main Pharmacy - Zone Y"
                    elif "Vit" in img_file: location_context = "Main Pharmacy - Vitamins"
                    else: location_context = "Main Pharmacy"
                elif "Store Location" in img_file:
                    # Extract "Z1", "Z2" etc
                    parts = img_file.split('Z')
                    if len(parts) > 1:
                        zone_num = parts[-1].split('.')[0]
                        location_context = f"Store Room - Zone {zone_num}"
                elif "Fridge" in img_file:
                     location_context = "Fridge"

                all_results[img_file] = {
                    'location_context': location_context,
                    'medications': meds
                }
                
                for med in meds:
                    print(f"    - {med.get('name')} {med.get('strength')}")
            else:
                print(f"  ✗ Failed: {result.get('error')}")
                
        except Exception as e:
            print(f"  Error processing {img_file}: {e}")

    # Save full results
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nAnalysis complete. Results saved to {results_file}")

if __name__ == "__main__":
    analyze_store_images()
