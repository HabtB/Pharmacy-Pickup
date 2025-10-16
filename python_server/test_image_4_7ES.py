#!/usr/bin/env python3
"""
Test the table-aware parser with Image 4: 7ES SICU NON NARCOTIC PICK
Device: 7ES_SICU
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from floor_stock_parser import FloorStockParser

# OCR text from Image 4
IMAGE_4_TEXT = """
BD
My Report: 7ES SICU NON NARCOTIC PICK
(Pick and Delivery Summary)
Mount Sinai Morningside
Run Time: 10/7/2025 01:15:03
Group By: Device

Device | Med Description | Pick Area | Pick Amount | Pick Actual | Max | Current Amount

7ES_SICU

atovaquone
(MEPRON) 750
mg (5 mL) oral
suspension
4
10
6

dextrose 50%
(DEXTROSE 50%)
25 g (50 mL)
syringe
2
4
2

insulin regular in
sodium chloride
0.9%
(MYXREDLIN) 100
UNITS (100 mL)
iv soln.
1
3
2

ipratropium 0.5
mg-albuterol 3
mg(2.5 mg
base)/3 mL (DUO
NEB) 1 EA
nebulizer
15
25
10

lactulose
(DUPHALAC) 20 g
(30 mL) ud cup
25
30
5

levETIRAcetam
(KEPPRA) 500 mg
(5 mL) vial
5
15
10

pantoprazole
(PROTONIX) 40
mg vial
11
20
9

phenylephrine in
NS (NEO-
SYNEPHRINE IV
SYRINGE) 1 mg
(10 mL) syringe
2
5
3

piperaCILLIN-
tazobactam in NS
(ZOSYN IN NS
(EXTENDED
INFUSION)
ADDEASE) 4.5 g
(100 mL) IVPB
7
10
3
"""

def test_parser():
    print("=" * 80)
    print("TESTING TABLE-AWARE PARSER WITH IMAGE 4: 7ES SICU")
    print("=" * 80)

    parser = FloorStockParser()

    print("\nParsing...")
    medications = parser.parse(IMAGE_4_TEXT)

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
        ("atovaquone", "750 mg", "oral suspension", 4),
        ("dextrose 50%", "25 g", "syringe", 2),
        ("insulin regular in sodium chloride", "100 UNITS", "iv soln", 1),
        ("ipratropium-albuterol", "0.5 mg-3 mg", "nebulizer", 15),
        ("lactulose", "20 g", "cup", 25),
        ("levETIRAcetam", "500 mg", "vial", 5),
        ("pantoprazole", "40 mg", "vial", 11),
        ("phenylephrine in NS", "1 mg", "syringe", 2),
        ("piperaCILLIN-tazobactam in NS", "4.5 g", "IVPB", 7),
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
