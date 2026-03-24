#!/usr/bin/env python3

import sys
sys.path.append('/Users/habtamu/Documents/pharmacy_pickup_app/lib/services')

# Test the fixed regex patterns
def test_dart_regex_patterns():
    """Test regex patterns equivalent to the Dart patterns we fixed"""
    import re

    test_text = "Oxybutynin (DITROPAN XL) 5 mg tablet extended release 24hr"

    # Pattern 1: Name (BRAND) strength form [extended release 24hr] - like "Oxybutynin (DITROPAN XL) 5 mg tablet extended release 24hr"
    pattern1 = r'^([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*\(([A-Z\s]+)\)\s*(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit))\s*(tablet|capsule|solution|suspension|injection|cream|ointment|gel|syrup|extended|release)'

    # Pattern 2: Name strength form - like "Lisinopril 10 mg tablet"
    pattern2 = r'^([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit))\s*(tablet|capsule|solution|suspension|injection|cream|ointment|gel|syrup)'

    patterns = [pattern1, pattern2]

    print(f"🧪 Testing text: '{test_text}'")
    print("=" * 50)

    for i, pattern in enumerate(patterns, 1):
        match = re.search(pattern, test_text, re.IGNORECASE)
        if match:
            print(f"✅ Pattern {i} MATCHED!")
            print(f"   Name: '{match.group(1)}'")
            if i == 1:  # Pattern 1 has brand
                print(f"   Brand: '{match.group(2)}'")
                print(f"   Strength: '{match.group(3)}'")
                print(f"   Form: '{match.group(4)}'")
            else:  # Pattern 2
                print(f"   Strength: '{match.group(2)}'")
                print(f"   Form: '{match.group(3)}'")
            return True
        else:
            print(f"❌ Pattern {i} did not match")

    return False

if __name__ == "__main__":
    print("🔬 Testing Flutter App Regex Patterns")
    print("=" * 50)

    success = test_dart_regex_patterns()

    if success:
        print("\n✅ SUCCESS: Regex patterns are working correctly!")
        print("The Flutter app should now be able to parse medication text.")
    else:
        print("\n❌ FAILED: Regex patterns need more work.")