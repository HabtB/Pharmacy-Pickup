
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from medication_location_lookup import get_location_lookup

def inspect_normalization():
    lookup = get_location_lookup()
    
    inputs = [
        "PANTOPRAZOLE 40 MG TABLET",
        "PANTOPRAZOLE 40 MG VIAL",
        "LEVETIRACETAM 500 MG IV",
        "LEVETIRACETAM 500 MG TABLET"
    ]
    
    print("\n=== INPUT NORMALIZATION ===")
    for i in inputs:
        print(f"'{i}' -> '{lookup._normalize_medication_name(i)}'")
        
    print("\n=== DB KEYS (Pantoprazole/Levetiracetam) ===")
    for key in lookup.location_db:
        if "PANTOPRAZOLE" in key or "LEVETIRACETAM" in key:
            code, desc, _ = lookup.location_db[key]
            print(f"KEY: '{key}' -> {code} ({desc})")

if __name__ == "__main__":
    inspect_normalization()
