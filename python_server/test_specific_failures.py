from medication_location_lookup import MedicationLocationLookup

def test_specific_failures():
    lookup = MedicationLocationLookup()
    print(f"Loaded {len(lookup.location_db)} locations")

    # Cases reported by user
    cases = [
        # (Name, Strength, Form, Expected substring in result)
        ("Ceftriaxone", "1 g", "bag", "CEFTRIAXONE"),   
        ("Ceftriaxone", "2 g", "bag", "CEFTRIAXONE"), 
        ("Ceftriaxone", "1 gms", "bag", "CEFTRIAXONE"),   
        ("Ceftriaxone", "2 gms", "bag", "CEFTRIAXONE"),
        ("Ceftriaxone", "2 gms", "bag", "CEFTRIAXONE"),
        # User reported failure from logic logs:
        ("ceftriaxone in D5W (ROCEPHIN (ADDEASE))", "2 g (50 mL)", "bag", "CEFTRIAXONE"),
        ("Meropeneum", "1 g", "vial", "MEROPENEM"), 
        # New reported failures:
        ("EPINEPHRINE in NS (EPINEPHRINE)", "4 mg in NS 250mL (16 mcg/mL)", "iv soln", "EPINEPHRINE"),
        ("insulin regular in sodium chloride 0.9% (MYXREDLIN)", "100 UNITS (100 mL)", "iv soln", "INSULIN"),
        ("amiodarone in D5W (NEXTERONE IV)", "360 mg (200 mL)", "bag", "AMIODARONE"),
        ("meropenem in NS (MERREM)", "1 g (100 mL)", "bag", "MEROPENEM"),
        ("chlorhexidine rinse (PERIDEX)", "15 mL", "ud cup", "CHLORHEXIDINE"),
        # Mannitol failure:
        ("mannitol 20% (MANNITOL 20%)", "(500 mL)", "bag", "MANNITOL"),
        ("amylase/lipase/protease", "3000 units", "capsule", "LIPASE"), 
        ("guaifenesin-dextromethorphan", "100-10 mg", "liquid", "DEXTROMETHORPHAN"), 
        ("dextromethorphan-guaifenesin", "20-200 mg", "liquid", "DEXTROMETHORPHAN"), # Scan: 20/200 (10ml), DB: 10/100 (5ml)
    ]

    print("\nTesting specific user failures:")
    print("-" * 60)
    
    success_count = 0
    for name, strength, form, expected in cases:
        result = lookup.find_location(name, strength, form)
        
        status = "✓ FOUND" if result else "✗ NOT FOUND"
        print(f"{status}: {name} {strength} {form}")
        
        if result:
            print(f"  -> Location: {result['location_code']} ({result['location_desc']})")
            success_count += 1
        else:
            # Debug info
            full_med = f"{name} {strength} {form}"
            normalized = lookup._normalize_medication_name(full_med)
            sorted_key = lookup._get_sorted_words_key(normalized)
            print(f"  Normalized: {normalized}")
            print(f"  Sorted Key: '{sorted_key}'")
            
            # Check if this key exists in index
            if sorted_key in lookup._sorted_index:
                 print(f"  -> Key EXISTS in index! Value: {lookup._sorted_index[sorted_key]}")
            else:
                 print(f"  -> Key NOT FOUND in index.")
                 # Try to find a partial match in index keys
                 print("  -> Similar keys in index:")
                 for k in list(lookup._sorted_index.keys())[:20]: # just random check
                      if 'LIPASE' in k:
                           print(f"     - '{k}'")
            
    print(f"\nSuccess Rate: {success_count}/{len(cases)}")

if __name__ == "__main__":
    test_specific_failures()
