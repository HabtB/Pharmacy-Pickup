
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from medication_location_lookup import get_location_lookup

def test_med(name, strength="", form=""):
    lookup = get_location_lookup()
    formatted = f"{name} {strength} {form}".strip()
    print(f"\nTesting: {formatted}")
    
    # Check find_location
    result = lookup.find_location(name, strength, form)
    if result:
        print(f"Result: {result['location_code']} - '{result.get('location_desc', '')}'")
        print(f"Image: '{result.get('image_file', '')}'")
    else:
        print("Result: NOT FOUND")

if __name__ == "__main__":
    print("=== DEXTROSE 50% (Should be Store Room - Zone 7) ===")
    test_med("Dextrose", "50%", "Syringe")

    print("\n=== EPLERENONE (Should be Store Room - Zone 1) ===")
    test_med("Eplerenone", "25 mg", "tablet")
    
    print("\n=== PANTOPRAZOLE (Vial -> IV, Tablet -> PHRM) ===")
    test_med("Pantoprazole", "40 mg", "vial")
    test_med("Pantoprazole", "40 mg", "tablet")
    test_med("Pantoprazole", "80 mg", "infusion")

    print("\n=== LEVETIRACETAM (IV -> IV, Tablet -> PHRM) ===")
    test_med("Levetiracetam", "500 mg", "IV")
    test_med("Levetiracetam", "500 mg", "tablet")
    
    print("\n=== LABETALOL (Syringe -> IV, Tablet -> PHRM) ===")
    test_med("Labetalol", "5 mg/ml", "syringe")
    test_med("Labetalol", "100 mg", "tablet")
    
    print("\n=== PHENYLEPHRINE (Syringe -> IV) ===")
    test_med("Phenylephrine", "1 mg", "syringe")
