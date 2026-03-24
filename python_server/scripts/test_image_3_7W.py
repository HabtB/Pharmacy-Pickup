#!/usr/bin/env python3
"""
Test the table-aware parser with Image 3: 7W 1&2 NON NARCOTIC
Devices: 7W-1, 7W-2
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from floor_stock_parser import FloorStockParser

# OCR text from Image 3
IMAGE_3_TEXT = """
BD
My Report: 7W 1&2 NON NARCOTIC
REFILL PICK (Pick and Delivery Summary)
Mount Sinai Morningside
Run Time: 10/7/2025 01:15:03
Group By: Device

Device | Med Description | Med ID | Pick Area | Pick Amount | Pick Actual | Max | Current Amount

7W-1

ceFAZolin in iso-
osmotic dextrose
(ANCEF
(DUPLEX)) 2 g
(50 mL) IVPB
PYX99748
8
8
0

enoxaparin
(LOVENOX) 40
mg (0.4 mL)
syringe
PYX23933
12
20
8

furosemide
(LASIX) 40 mg (4
mL) vial
689
14
25
11

ondansetron
(ZOFRAN) 4 mg
(2 mL) vial
002646
10
20
10

7W-2

albuterol 0.083 %
(ALBUTEROL) 2.5
mg (3 mL)
nebulizer
004233
30
30
0

apixaban
(ELIQUIS) 5 mg
tablet
PYX104963
5
25
20

atorvastatin
(LIPITOR) 40 mg
tablet
PYX712
10
24
14

budesonide
(PULMICORT) 0.5
mg (2 mL)
nebulizer
PYX15258
5
10
5

divalproex
(DEPAKOTE
SPRINKLE) 125
mg capsule
PYX19036
10
20
10

donepezil
(ARICEPT) 5 mg
tablet
PYX1979
15
20
5

finasteride
(PROSCAR) 5 mg
tablet
PYX19553
6
10
4
"""

def test_parser():
    print("=" * 80)
    print("TESTING TABLE-AWARE PARSER WITH IMAGE 3: 7W 1&2")
    print("=" * 80)

    parser = FloorStockParser()

    print("\nParsing...")
    medications = parser.parse(IMAGE_3_TEXT)

    print("\n" + "=" * 80)
    print(f"RESULTS: Found {len(medications)} medications")
    print("=" * 80)

    if medications:
        # Group by device for display
        devices = {}
        for med in medications:
            floor = med['floor']
            if floor not in devices:
                devices[floor] = []
            devices[floor].append(med)

        i = 1
        for floor in sorted(devices.keys()):
            print(f"\n--- Device: {floor} ---")
            for med in devices[floor]:
                print(f"\n{i}. {med['name']}")
                print(f"   Strength: {med['strength']}")
                print(f"   Form: {med['form']}")
                print(f"   Pick Amount: {med['pick_amount']}")
                i += 1
    else:
        print("\n⚠️  No medications found!")

    # Expected results
    print("\n" + "=" * 80)
    print("EXPECTED MEDICATIONS:")
    print("=" * 80)

    expected_7w1 = [
        ("ceFAZolin in iso-osmotic dextrose", "2 g", "IVPB", 8),
        ("enoxaparin", "40 mg", "syringe", 12),
        ("furosemide", "40 mg", "vial", 14),
        ("ondansetron", "4 mg", "vial", 10),
    ]

    expected_7w2 = [
        ("albuterol", "0.083 %", "nebulizer", 30),
        ("apixaban", "5 mg", "tablet", 5),
        ("atorvastatin", "40 mg", "tablet", 10),
        ("budesonide", "0.5 mg", "nebulizer", 5),
        ("divalproex", "125 mg", "capsule", 10),
        ("donepezil", "5 mg", "tablet", 15),
        ("finasteride", "5 mg", "tablet", 6),
    ]

    total_expected = len(expected_7w1) + len(expected_7w2)

    print(f"\nExpected: {total_expected} medications (7W-1: {len(expected_7w1)}, 7W-2: {len(expected_7w2)})")
    print(f"Found: {len(medications)} medications")

    if len(medications) == total_expected:
        print("✅ Correct count!")
    else:
        print(f"❌ Count mismatch (expected {total_expected}, got {len(medications)})")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    test_parser()
