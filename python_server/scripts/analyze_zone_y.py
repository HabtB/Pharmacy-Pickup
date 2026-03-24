import os
import sys
from enhanced_medication_parser import EnhancedMedicationParser
from dotenv import load_dotenv

# Load env for API keys
# Load env for API keys
from pathlib import Path
# Script is in python_server, so .env is in SAME directory
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

if os.getenv('GOOGLE_API_KEY'):
    print("DEBUG: GOOGLE_API_KEY found in env.")
else:
    print("DEBUG: GOOGLE_API_KEY NOT found in env!")

def analyze_images():
    parser = EnhancedMedicationParser()
    
    # Path to artifacts directory
    artifacts_dir = "/Users/habtamu/.gemini/antigravity/brain/497d9011-b76a-45a0-8b50-8c771f698ad1"
    
    # Get all jpg files
    image_files = [f for f in os.listdir(artifacts_dir) if f.endswith('.jpg') and f.startswith('uploaded_image')]
    
    print(f"Found {len(image_files)} images to analyze.")
    
    for img_file in image_files:
        print(f"\n--- Analyzing {img_file} ---")
        img_path = os.path.join(artifacts_dir, img_file)
        
        try:
            with open(img_path, 'rb') as f:
                image_data = f.read()
                
            # Use 'floor_stock' mode to trigger Gemini logic if needed, but enhanced parser uses it globally now
            result = parser.parse_medication_label(image_data, mode='floor_stock')
            
            if result['success']:
                print(f"Found {len(result['medications'])} medications:")
                for med in result['medications']:
                    print(f"  - {med.get('name')} {med.get('strength')} {med.get('form')}")
            else:
                print(f"Failed: {result.get('error')}")
                
        except Exception as e:
            print(f"Error processing {img_file}: {e}")

if __name__ == "__main__":
    analyze_images()
