#!/usr/bin/env python3
"""
Test the table-aware parser with the second test image
Device: 6E-2_CICU
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from floor_stock_parser import FloorStockParser

# OCR text from the second test image
IMAGE_2_TEXT = """
Device: 6E-2_CICU

Med Description | Pick Area | Pick Amount | Pick Actual | Max | Current Amount

dextrose 50%
(DEXTROSE 50%)
25 g (50 mL)
syringe
2
3
1

rocuronium
(ROCURONIUM)
10 mg/1 mL (5
mL) vial
4
6
2

albumin 5%
(ALBUTEIN) 12.5
g (250 mL) iv
soln.
4
10
6

midodrine
(PROAMATINE) 5
mg tablet
18
20
2

NORepinephrine
in NS (LEVOPHED
in NS (8mg)) 8
mg (250 mL)
IVPB
2
6
4

lidocaine 4%
(SALONPAS) 1
each patch
6
20
14
"""

def test_parser():
    print("=" * 80)
    print("TESTING TABLE-AWARE PARSER WITH IMAGE 2")
    print("=" * 80)

    parser = FloorStockParser()

    print("\nParsing...")
    medications = parser.parse(IMAGE_2_TEXT)

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
        ("Dextrose 50%", "25 g", "syringe", 2),
        ("Rocuronium", "10 mg/1 mL", "vial", 4),
        ("Albumin 5%", "12.5 g", "iv soln", 4),
        ("Midodrine", "5 mg", "tablet", 18),
        ("NORepinephrine in NS", "8 mg", "IVPB", 2),
        ("Lidocaine 4%", "1 each", "patch", 6),
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
