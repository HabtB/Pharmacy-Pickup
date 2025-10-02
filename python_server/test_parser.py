#!/usr/bin/env python3

import requests
import base64
import json
import os

def test_image_parsing(image_path, mode='cart_fill'):
    """Test image parsing with the running server"""

    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return

    print(f"🧪 Testing image: {os.path.basename(image_path)}")
    print(f"📁 Full path: {image_path}")

    # Read and encode image
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()

        base64_image = base64.b64encode(image_data).decode('utf-8')
        print(f"📊 Image size: {len(image_data)} bytes")
        print(f"📊 Base64 size: {len(base64_image)} characters")

    except Exception as e:
        print(f"❌ Error reading image: {e}")
        return

    # Test server
    server_url = 'http://192.168.1.134:5001'

    try:
        # Send request
        print(f"🚀 Sending request to {server_url}/parse-document")

        response = requests.post(
            f'{server_url}/parse-document',
            headers={'Content-Type': 'application/json'},
            json={
                'image_base64': base64_image,
                'mode': mode,
                'strategy': 'enhanced'  # Use enhanced strategy
            },
            timeout=30
        )

        print(f"📡 Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"🔍 Method used: {data.get('method', 'unknown')}")
            print(f"📄 Raw text found: {bool(data.get('raw_text'))}")

            if data.get('raw_text'):
                raw_text = data['raw_text'][:200] + "..." if len(data.get('raw_text', '')) > 200 else data.get('raw_text', '')
                print(f"📝 Text preview: {raw_text}")

            medications = data.get('medications', [])
            print(f"💊 Medications found: {len(medications)}")

            for i, med in enumerate(medications, 1):
                print(f"  {i}. {med.get('name', 'Unknown')} - {med.get('dose', '')} {med.get('form', '')}")
                if med.get('patient'):
                    print(f"     Patient: {med['patient']}")
                if med.get('quantity'):
                    print(f"     Quantity: {med['quantity']}")

        else:
            print(f"❌ FAILED with status {response.status_code}")
            print(f"🔍 Response: {response.text}")

    except Exception as e:
        print(f"❌ Request error: {e}")

if __name__ == "__main__":
    print("🔬 Testing Medication Parser with Local Images")
    print("=" * 50)

    # Test images
    test_images = [
        "/Users/habtamu/Documents/pharmacy_pickup_app/assets/test_medication_label.jpg",
        "/Users/habtamu/Documents/pharmacy_pickup_app/test_png_med.png"
    ]

    for image_path in test_images:
        print()
        test_image_parsing(image_path)
        print("-" * 30)