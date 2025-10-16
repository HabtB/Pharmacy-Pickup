#!/usr/bin/env python3
"""
Test LLM correction mechanism for incomplete medication names
"""
import requests
import base64
import json

# Test with 8E 1-2 image (has magnesium, sulfate, chloride issues)
IMAGE_PATH = "/Users/habtamu/Downloads/8E 1-2 NON NARCOTIC PICK.jpg"

def test_floor_stock_parsing():
    print("=== Testing LLM Correction Mechanism ===\n")

    # Read and encode image
    with open(IMAGE_PATH, 'rb') as f:
        image_data = f.read()

    image_b64 = base64.b64encode(image_data).decode('utf-8')
    print(f"Image size: {len(image_data)} bytes")
    print(f"Base64 size: {len(image_b64)} chars\n")

    # Send to server
    url = "http://localhost:5003/parse-document"
    payload = {
        "image_base64": image_b64,
        "mode": "floor_stock"
    }

    print("Sending request to server...")
    response = requests.post(url, json=payload, timeout=60)

    if response.status_code == 200:
        result = response.json()

        print(f"\n✓ Server returned {response.status_code}")
        print(f"Success: {result.get('success')}")
        print(f"Method: {result.get('method')}")
        print(f"Medications found: {len(result.get('medications', []))}\n")

        print("=== MEDICATIONS EXTRACTED ===")
        for i, med in enumerate(result.get('medications', []), 1):
            print(f"{i}. {med['name']}")
            print(f"   Strength: {med.get('strength', 'N/A')}")
            print(f"   Form: {med.get('form', 'N/A')}")
            print(f"   Floor: {med.get('floor', 'N/A')}")
            print(f"   Pick: {med.get('pick_amount', 'N/A')}")
            print()

        # Check for expected medications
        med_names = [m['name'].lower() for m in result.get('medications', [])]

        print("=== CHECKING FOR EXPECTED MEDICATIONS ===")
        expected = [
            'magnesium sulfate',
            'potassium chloride',
            'acetaminophen'
        ]

        for exp in expected:
            found = any(exp in name for name in med_names)
            status = "✓ FOUND" if found else "✗ MISSING"
            print(f"{status}: {exp}")

    else:
        print(f"✗ Server error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_floor_stock_parsing()
