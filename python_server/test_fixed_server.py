#!/usr/bin/env python3

import requests
import base64
import json
import os

def test_fixed_server():
    """Test the fixed server on port 5003"""

    # Test with a simple image path
    image_path = "/Users/habtamu/Documents/pharmacy_pickup_app/assets/test_medication_label.jpg"

    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return

    print(f"🧪 Testing Fixed Server with: {os.path.basename(image_path)}")

    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()

    base64_image = base64.b64encode(image_data).decode('utf-8')
    print(f"📊 Image size: {len(image_data)} bytes")

    # Test the fixed server on port 5003
    server_url = 'http://192.168.1.134:5003'

    try:
        print(f"🚀 Sending request to {server_url}/parse-document")

        response = requests.post(
            f'{server_url}/parse-document',
            headers={'Content-Type': 'application/json'},
            json={
                'image_base64': base64_image,
                'mode': 'cart_fill'
            },
            timeout=30
        )

        print(f"📡 Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"🔍 Method used: {data.get('method', 'unknown')}")
            print(f"📄 Success: {data.get('success', False)}")

            medications = data.get('medications', [])
            print(f"💊 Medications found: {len(medications)}")

            for i, med in enumerate(medications, 1):
                print(f"  {i}. {med.get('name', 'Unknown')} - {med.get('dose', '')} {med.get('form', '')}")
                if med.get('patient'):
                    print(f"     Patient: {med['patient']}")

            raw_text = data.get('raw_text', '')
            if raw_text:
                print(f"📝 Raw text preview: {raw_text[:200]}...")

        else:
            print(f"❌ FAILED with status {response.status_code}")
            print(f"🔍 Response: {response.text}")

    except Exception as e:
        print(f"❌ Request error: {e}")

if __name__ == "__main__":
    test_fixed_server()