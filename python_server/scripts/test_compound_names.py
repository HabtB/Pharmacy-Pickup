#!/usr/bin/env python3
"""
Test compound medication names (magnesium sulfate, potassium chloride, etc.)
to verify continuation_words fix
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from floor_stock_parser import FloorStockParser

# Simulated OCR text from 8E 1-2 NON NARCOTIC PICK
TEST_TEXT = """
Device: 8E-1

Med Description | Pick Area | Pick Amount | Max | Current Amount

acetaminophen
(TYLENOL) 325 mg
tablet
10

bacitracin zinc
(BACITRACIN)
ointment
5

heparin sodium
(HEPARIN FLUSH)
10 units/mL vial
8

lidocaine HCl
(XYLOCAINE) 2%
jelly
3

magnesium
hydroxide
(MILK OF
MAGNESIA) oral
suspension
6

magnesium
sulfate in D5W
(MAGNESIUM
SULFATE D5W) 4
g (100 mL) IVPB
12

potassium
chloride (KCL
IVPB) 20 mEq
(100 mL) IVPB
15

tacrolimus
(PROGRAF) 1 mg
capsule
4

Device: 8E-2

celeCOXIB
(CELEBREX) 200
mg capsule
7

donepezil
(ARICEPT) 10 mg
tablet
5

enoxaparin
(LOVENOX) 40
mg syringe
9

sodium zirconium
cyclosilicate
(LOKELMA) 5 g
packet
3
"""

def test_compound_names():
    print("=" * 80)
    print("TESTING COMPOUND MEDICATION NAMES")
    print("=" * 80)

    parser = FloorStockParser()
    medications = parser.parse(TEST_TEXT)

    print(f"\n✅ Found {len(medications)} medications\n")

    for i, med in enumerate(medications, 1):
        print(f"{i}. {med['name']}")
        print(f"   Strength: {med['strength']}")
        print(f"   Form: {med['form']}")
        print(f"   Floor: {med.get('floor', 'N/A')}")
        print(f"   Pick Amount: {med['pick_amount']}")
        print()

    print("=" * 80)
    print("VERIFICATION:")
    print("=" * 80)

    names_lower = [m['name'].lower() for m in medications]

    # Test 1: magnesium sulfate should be one medication
    has_magnesium_sulfate = any('magnesium sulfate' in name for name in names_lower)
    has_standalone_sulfate = any(name.startswith('sulfate') for name in names_lower)

    if has_magnesium_sulfate and not has_standalone_sulfate:
        print("✅ TEST 1 PASSED: 'magnesium sulfate' kept as one medication")
    else:
        print(f"❌ TEST 1 FAILED: magnesium sulfate={has_magnesium_sulfate}, standalone sulfate={has_standalone_sulfate}")

    # Test 2: potassium chloride should be one medication
    has_potassium_chloride = any('potassium chloride' in name or 'potassium' in name for name in names_lower)
    has_standalone_chloride = any(name.startswith('chloride') for name in names_lower)

    if has_potassium_chloride and not has_standalone_chloride:
        print("✅ TEST 2 PASSED: 'potassium chloride' kept as one medication")
    else:
        print(f"❌ TEST 2 FAILED: potassium chloride={has_potassium_chloride}, standalone chloride={has_standalone_chloride}")

    # Test 3: magnesium hydroxide should be one medication
    has_magnesium_hydroxide = any('magnesium hydroxide' in name or ('magnesium' in name and 'milk of magnesia' in name) for name in names_lower)
    has_standalone_hydroxide = any(name.startswith('hydroxide') for name in names_lower)

    if has_magnesium_hydroxide and not has_standalone_hydroxide:
        print("✅ TEST 3 PASSED: 'magnesium hydroxide' kept as one medication")
    else:
        print(f"❌ TEST 3 FAILED: magnesium hydroxide={has_magnesium_hydroxide}, standalone hydroxide={has_standalone_hydroxide}")

    # Test 4: sodium zirconium cyclosilicate should be one medication
    has_sodium_zirconium = any('zirconium' in name or 'lokelma' in name for name in names_lower)
    has_standalone_zirconium = any(name.startswith('zirconium') and 'sodium' not in name for name in names_lower)

    if has_sodium_zirconium and not has_standalone_zirconium:
        print("✅ TEST 4 PASSED: 'sodium zirconium cyclosilicate' kept as one medication")
    else:
        print(f"❌ TEST 4 FAILED: has sodium/zirconium={has_sodium_zirconium}, standalone zirconium={has_standalone_zirconium}")

    # Test 5: Should find expected number of medications (11-13 total)
    expected_min = 11
    expected_max = 13
    if expected_min <= len(medications) <= expected_max:
        print(f"✅ TEST 5 PASSED: Found {len(medications)} medications (expected {expected_min}-{expected_max})")
    else:
        print(f"❌ TEST 5 FAILED: Found {len(medications)} medications (expected {expected_min}-{expected_max})")

    # Test 6: Floor breakdown
    floor_8e1 = [m for m in medications if m.get('floor') == '8E-1']
    floor_8e2 = [m for m in medications if m.get('floor') == '8E-2']

    print(f"\n📊 Floor breakdown:")
    print(f"   8E-1: {len(floor_8e1)} medications")
    print(f"   8E-2: {len(floor_8e2)} medications")

    if len(floor_8e1) >= 7 and len(floor_8e2) >= 3:
        print("✅ TEST 6 PASSED: Floor assignments look correct")
    else:
        print(f"❌ TEST 6 FAILED: Expected ≥7 for 8E-1 and ≥3 for 8E-2")

    print("=" * 80)

if __name__ == '__main__':
    test_compound_names()
