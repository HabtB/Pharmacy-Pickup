#!/usr/bin/env python3
"""
Test the new table-aware parser with text extracted from the real BD image
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from floor_stock_parser import FloorStockParser

# This is the OCR text from the BD pick list image (6E-2_CICU)
REAL_OCR_TEXT = """
BD
MY Report: 6E-2 CICU NON NARCOTIC
PICK (Pick and Delivery Summary)
Mount Sinai Morningside
Run Time: 10/7/2025 01:15:03
Group By: Device
Pick Area
Pick Amount
Pick Actual
Max
Current
Amount
Device
6E-2_CICU
Med
Description
metoprolol
tartrate
(LOPRESSOR)
12.5 mg half
tablet
10
ceFAZolin In iso-
osmotic dextrose
(ANCEF
(DUPLEX)) 2 g
(50 mL) IVPB
12
sodium
bicarbonate 8.4%
(SODIUM
BICARBONATE
8.4%) 50 mEq
(50 mL) vial
6
phenylephrine in
NS
(PHENYLEPHRINE
IV (ADDEASE)) 50
mg (250 mL) mini
bag
2
niCARdipine in NS
(CARDENE IN NS
(ADDEASE)) 25
mg (100 mL)
IVPB
1
ipratropium
0.02%
(ATROVENT
0.02%) (2.5 mL)
nebulizer
15
cefePIME in NS
(MAXIPIME IN NS
(ADDEASE)) 2 g
(100 mL) IVPB
5
furosemide
(LASIX) 20 mg (2
mL) vial
17
acetaminophen
(TYLENOL) 325
mg (10.15 mL) ud
cup
6
"""

def test_parser():
    print("=" * 80)
    print("TESTING TABLE-AWARE PARSER WITH REAL IMAGE OCR TEXT")
    print("=" * 80)

    parser = FloorStockParser()

    print("\nParsing...")
    medications = parser.parse(REAL_OCR_TEXT)

    print("\n" + "=" * 80)
    print(f"RESULTS: Found {len(medications)} medications")
    print("=" * 80)

    if medications:
        for i, med in enumerate(medications, 1):
            print(f"\n{i}. {med['name']}")
            print(f"   Strength: {med['strength']}")
            print(f"   Form: {med['form']}")
            print(f"   Floor: {med['floor']}")
            print(f"   Pick Amount: {med['pick_amount']}")
    else:
        print("\n⚠️  No medications found!")

    # Expected results
    print("\n" + "=" * 80)
    print("EXPECTED MEDICATIONS:")
    print("=" * 80)
    expected = [
        ("Metoprolol tartrate", "12.5 mg", "half tablet", 10),
        ("ceFAZolin In iso-osmotic dextrose", "2 g", "IVPB", 12),
        ("Sodium bicarbonate", "8.4%", "vial", 6),
        ("Phenylephrine in NS", "50 mg", "bag", 2),
        ("niCARdipine in NS", "25 mg", "IVPB", 1),
        ("Ipratropium", "0.02%", "nebulizer", 15),
        ("cefePIME in NS", "2 g", "IVPB", 5),
        ("Furosemide", "20 mg", "vial", 17),
        ("Acetaminophen", "325 mg", "cup", 6),
    ]

    print(f"\nExpected: {len(expected)} medications")
    print(f"Found: {len(medications)} medications")

    if len(medications) == len(expected):
        print("✅ Correct count!")
    else:
        print(f"❌ Count mismatch (expected {len(expected)}, got {len(medications)})")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    test_parser()
