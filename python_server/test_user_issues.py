#!/usr/bin/env python3
"""
Test the specific issues user reported
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from floor_stock_parser import FloorStockParser

# Simulated OCR text with user's reported issues
TEST_TEXT = """
Device: 7EM_MICU

Med Description | Pick Area | Pick Amount | Max | Current Amount

PICK (Pick and
Delivery Summary)
0

amiodarone in
D5W (NEXTERONE
IV) 360 mg (200
mL) iv
11

atorvastatin
(LIPITOR) 20 mg
tablet
10

levETIRAcetam
(KEPPRA) 80 mg
tablet
0

ondansetron
5

(ZOFRAN) 4 mg
vial
0

meropenem in
NS
3

(MERREM IVPB) 1
g (100 mL) IVPB
2
"""

def test_user_issues():
    print("=" * 80)
    print("TESTING USER-REPORTED ISSUES")
    print("=" * 80)

    parser = FloorStockParser()
    medications = parser.parse(TEST_TEXT)

    print(f"\n✅ Found {len(medications)} medications\n")

    for i, med in enumerate(medications, 1):
        print(f"{i}. {med['name']}")
        print(f"   Strength: {med['strength']}")
        print(f"   Form: {med['form']}")
        print(f"   Pick Amount: {med['pick_amount']}")
        print()

    print("=" * 80)
    print("VERIFICATION:")
    print("=" * 80)

    # Check each issue
    names = [m['name'] for m in medications]

    # Issue 1: PICK should be filtered
    has_pick = any('PICK' in name and 'Summary' in name for name in names)
    if not has_pick:
        print("✅ Issue 1 FIXED: 'PICK (Pick and Delivery Summary)' is filtered out")
    else:
        print("❌ Issue 1: PICK still appears")

    # Issue 2: Generic names should be displayed
    has_atorvastatin = any('atorvastatin' in name.lower() and 'LIPITOR' in name for name in names)
    if has_atorvastatin:
        print("✅ Issue 2 FIXED: Generic shown as 'atorvastatin (LIPITOR)'")
    else:
        print("❌ Issue 2: Missing generic name for LIPITOR")

    # Issue 3: ondansetron and ZOFRAN should be merged
    separate_ondansetron = sum(1 for name in names if 'ondansetron' in name.lower() or 'ZOFRAN' in name)
    if separate_ondansetron == 1:
        print("✅ Issue 3 FIXED: ondansetron and ZOFRAN merged into one")
    else:
        print(f"❌ Issue 3: ondansetron/ZOFRAN appear as {separate_ondansetron} separate entries")

    # Issue 4: Amiodarone in D5W should be properly parsed
    has_amiodarone = any('amiodarone' in name.lower() and 'D5W' in name for name in names)
    if has_amiodarone:
        print("✅ Issue 4 FIXED: Amiodarone in D5W properly parsed with generic name")
    else:
        print("❌ Issue 4: Amiodarone in D5W not properly parsed")

    print("=" * 80)

if __name__ == '__main__':
    test_user_issues()
