from medication_location_lookup import MedicationLocationLookup

def test_fuzzy_matching():
    lookup = MedicationLocationLookup()
    print(f"Loaded {len(lookup.location_db)} locations")

    # Cases from the user logs that FAILED
    failed_cases = [
        # (Name, Strength, Form)
        ("CEFTRIAXONE (ROCEPHIN (ADDEASE))", "2 g", "bag"),
        ("ipratropium (ATROVENT)", "0.02%", "nebulizer"),
        ("METRONIDAZOLE (FLAGYL)", "500 mg", "bag"),
        ("piperacillin-tazobactam (ADDEASE)", "4.5 g", "bag"),
        ("amylase/lipase/protease (CREON)", "3000 units", "capsule")
    ]

    print("\nTesting known failures with fuzzy matching:")
    print("-" * 60)
    
    success_count = 0
    for name, strength, form in failed_cases:
        result = lookup.find_location(name, strength, form)
        if result:
            print(f"✓ {name}: FOUND -> {result['location_code']}")
            success_count += 1
        else:
            print(f"✗ {name}: NOT FOUND")
            # Debug: show normalization
            full_med = f"{name} {strength} {form}"
            normalized = lookup._normalize_medication_name(full_med)
            print(f"  Normalized: {normalized}")

    print(f"\nSuccess Rate: {success_count}/{len(failed_cases)}")

if __name__ == "__main__":
    test_fuzzy_matching()
