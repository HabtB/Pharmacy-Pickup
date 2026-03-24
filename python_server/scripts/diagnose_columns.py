#!/usr/bin/env python3
"""
Diagnostic script to analyze column detection issues
Helps identify why wrong quantities are being extracted
"""

# Sample OCR text showing the issue
ocr_text = """
Pick Area
Pick Amount
Pick Actual
Max
Current
Amount

NORepinephrine in NS (LEVOPHED in NS (8mg)) 8 mg (250 mL) IVPB
10
20
20
"""

print("=== OCR TEXT ANALYSIS ===")
print(ocr_text)
print("\n=== EXPECTED BEHAVIOR ===")
print("According to user:")
print("  - App shows: 20")
print("  - Should be: 2")
print("\n=== COLUMN LAYOUT ===")
print("Headers: Pick Area | Pick Amount | Pick Actual | Max | Current | Amount")
print("\nFor medications with 3 numbers (e.g., 10, 20, 20):")
print("  - Which is Pick Amount?")
print("  - Which is Max?")
print("  - Which is Current?")
print("\n=== HYPOTHESIS ===")
print("If app shows 20 instead of 2:")
print("  1. Parser might be reading 'Max' or 'Current' column instead of 'Pick Amount'")
print("  2. OR the coordinate detection is shifting columns")
print("  3. OR there are multiple numbers in the Pick Amount column")
print("\n=== RECOMMENDATION ===")
print("Need to see Google Vision word annotations with X,Y coordinates")
print("to understand exact column boundaries")
