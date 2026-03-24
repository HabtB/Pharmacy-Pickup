
import sys
import os
from dotenv import load_dotenv

# Mock env
os.environ['GROK_API_KEY'] = 'mock_key'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'mock_creds'

print("Attempting to import modules...")
try:
    from floor_stock_parser import FloorStockParser
    print("✓ Import successful: floor_stock_parser")
    
    from enhanced_medication_parser import EnhancedMedicationParser
    print("✓ Import successful: enhanced_medication_parser")
    
    print("Attemping to instantiate FloorStockParser...")
    parser = FloorStockParser()
    print("✓ Instantiation successful")
    
    # Check method existence
    if hasattr(parser, '_extract_row_data_with_llm'):
        print("✓ Method exists: _extract_row_data_with_llm")
    else:
        print("✗ Method MISSING: _extract_row_data_with_llm")
        
except Exception as e:
    print(f"✗ FAIL: {e}")
    import traceback
    traceback.print_exc()
