#!/usr/bin/env python3
"""
Test script for hybrid floor stock parser
Tests the deterministic + validation approach with real floor stock data
"""

import sys
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from floor_stock_parser import FloorStockParser

# Sample floor stock text (from the problematic 8E-1,2 scan)
SAMPLE_TEXT = """
BD Pick List - Floor Stock
Device: 8E-1
lidocaine
4%
patch
18

gabapentin
(NEURONTIN)
100 mg
capsule
25

Device: 8E-2
enoxaparin
30 mg
syringe
10

magnesium sulfate
1 g
bag
12
"""

def test_hybrid_parser():
    """Test the hybrid parser with sample data"""
    print("=" * 80)
    print("TESTING HYBRID FLOOR STOCK PARSER")
    print("=" * 80)

    parser = FloorStockParser()

    print("\nInput text:")
    print("-" * 80)
    print(SAMPLE_TEXT)
    print("-" * 80)

    print("\nParsing with hybrid approach...")
    medications = parser.parse(SAMPLE_TEXT)

    print("\n" + "=" * 80)
    print(f"RESULTS: Found {len(medications)} validated medications")
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

    print("\n" + "=" * 80)
    print("TEST VALIDATION")
    print("=" * 80)

    # Expected results
    expected = [
        ("Lidocaine", "8E-1", 18),
        ("Gabapentin", "8E-1", 25),
        ("Enoxaparin", "8E-2", 10),
        ("Magnesium Sulfate", "8E-2", 12)
    ]

    print(f"\nExpected: {len(expected)} medications")
    print(f"Found: {len(medications)} medications")

    # Check each expected medication
    for exp_name, exp_floor, exp_amount in expected:
        found = False
        for med in medications:
            if exp_name.lower() in med['name'].lower():
                found = True
                if med['floor'] == exp_floor and med['pick_amount'] == exp_amount:
                    print(f"✅ {exp_name}: Correct (Floor: {exp_floor}, Amount: {exp_amount})")
                else:
                    print(f"⚠️  {exp_name}: Found but data mismatch")
                    print(f"   Expected: Floor={exp_floor}, Amount={exp_amount}")
                    print(f"   Got: Floor={med['floor']}, Amount={med['pick_amount']}")
                break

        if not found:
            print(f"❌ {exp_name}: NOT FOUND (possible false negative)")

    # Check for hallucinations (extra medications)
    for med in medications:
        expected_names = [e[0] for e in expected]
        if not any(exp.lower() in med['name'].lower() for exp in expected_names):
            print(f"⚠️  UNEXPECTED: {med['name']} (possible hallucination?)")

    print("\n" + "=" * 80)
    return medications

if __name__ == '__main__':
    test_hybrid_parser()
