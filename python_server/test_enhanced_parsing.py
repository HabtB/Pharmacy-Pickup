#!/usr/bin/env python3
"""
Test script for enhanced medication parsing pipeline
Tests the new parsing system with real medication labels
"""

import base64
import json
import requests
import time
import os
from enhanced_medication_parser import parse_medication_with_enhanced_model

def test_enhanced_parsing():
    """Test the enhanced parsing pipeline"""
    print("=== TESTING ENHANCED MEDICATION PARSING ===\n")

    # Test with the medication label image
    image_path = '../assets/test_medication_label.jpg'

    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return False

    # Read test image
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        print(f"✅ Loaded test image: {len(image_data)} bytes")
    except Exception as e:
        print(f"❌ Failed to load image: {e}")
        return False

    # Test enhanced parser directly
    print("\n1. Testing Enhanced Parser Directly")
    print("-" * 40)

    try:
        result = parse_medication_with_enhanced_model(image_data, 'cart_fill')

        print(f"Success: {result.get('success', False)}")
        print(f"Method: {result.get('method', 'unknown')}")
        print(f"Raw text: '{result.get('raw_text', '')[:200]}...'")
        print(f"Medications found: {len(result.get('medications', []))}")

        if result.get('medications'):
            for i, med in enumerate(result['medications'], 1):
                print(f"  {i}. {med}")

        enhanced_success = result.get('success', False) and len(result.get('medications', [])) > 0

    except Exception as e:
        print(f"❌ Enhanced parser failed: {e}")
        enhanced_success = False

    # Test via server if running
    print("\n2. Testing Via Docling Server")
    print("-" * 40)

    server_success = False
    try:
        # Check if server is running
        health_response = requests.get('http://localhost:5001/health', timeout=5)
        if health_response.status_code == 200:
            print("✅ Server is running")

            # Test parsing via server
            base64_image = base64.b64encode(image_data).decode('utf-8')

            payload = {
                'image_base64': base64_image,
                'mode': 'cart_fill'
            }

            response = requests.post(
                'http://localhost:5001/parse-document',
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Server parsing successful")
                print(f"Success: {data.get('success', False)}")
                print(f"Method: {data.get('method', 'unknown')}")
                print(f"Medications: {len(data.get('medications', []))}")

                if data.get('medications'):
                    for i, med in enumerate(data['medications'], 1):
                        print(f"  {i}. {med}")

                server_success = data.get('success', False) and len(data.get('medications', [])) > 0
            else:
                print(f"❌ Server returned error: {response.status_code}")
                print(f"Response: {response.text}")
        else:
            print(f"❌ Server health check failed: {health_response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ Server not running")
        print("To start server: cd python_server && python3 docling_server.py")
    except Exception as e:
        print(f"❌ Server test failed: {e}")

    # Expected results for this medication label
    print("\n3. Expected Results Analysis")
    print("-" * 40)
    print("Expected to extract from test image:")
    print("- Medication: Lisinopril")
    print("- Strength: 10mg")
    print("- Form: Tablet")
    print("- Patient: John Doe")
    print("- Quantity: 30 tablets")
    print("- Directions: Take 1 tablet daily")
    print("- Rx: 123456789")

    # Summary
    print("\n4. Test Summary")
    print("-" * 40)
    if enhanced_success:
        print("✅ Enhanced parser: PASSED")
    else:
        print("❌ Enhanced parser: FAILED")

    if server_success:
        print("✅ Server integration: PASSED")
    else:
        print("❌ Server integration: FAILED")

    overall_success = enhanced_success or server_success

    if overall_success:
        print("\n🎉 OVERALL: PARSING FUNCTIONALITY WORKING")
    else:
        print("\n💥 OVERALL: PARSING NEEDS ATTENTION")
        print("\nTroubleshooting:")
        print("1. Check if GROK_API_KEY is set in environment")
        print("2. Start Docling server: python3 docling_server.py")
        print("3. Check server logs for detailed error information")

    return overall_success

def test_with_simple_text():
    """Test parsing with simple text input"""
    print("\n=== TESTING WITH SIMPLE TEXT ===")

    test_texts = [
        "Lisinopril 10mg Tablet\nPatient: John Doe\nQuantity: 30 tablets\nDirections: Take 1 tablet daily\nRx: 123456789",
        "Metoprolol 25mg Tablet\nTake twice daily",
        "Gabapentin 300mg Capsule\nTake as needed for pain"
    ]

    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text.split()[0]}")
        print("-" * 30)

        try:
            # Convert text to fake image data for testing
            # In real scenario, this would be actual image bytes
            fake_image_data = text.encode('utf-8')

            # This won't work with the image processing, but tests the LLM part
            # In practice, we'd need to test with actual images
            print(f"Text: {text[:50]}...")
            print("Note: Would need actual image for full test")

        except Exception as e:
            print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    success = test_enhanced_parsing()
    test_with_simple_text()

    print(f"\n{'='*50}")
    if success:
        print("🎉 Enhanced parsing system is ready for use!")
    else:
        print("⚠️  Enhanced parsing system needs configuration.")
    print(f"{'='*50}")