#!/usr/bin/env python3
"""
Comprehensive test comparing all parser versions
Shows the improvement journey from original to refined parser
"""

import base64
from enhanced_medication_parser_backup_working import parse_medication_with_enhanced_model as parse_v1
from enhanced_medication_parser import parse_medication_with_enhanced_model as parse_v2

def test_all_versions():
    """Compare all parser versions"""
    print("🧪 COMPREHENSIVE PARSER COMPARISON TEST")
    print("=" * 60)

    # Load test image
    try:
        with open('../assets/test_medication_label.jpg', 'rb') as f:
            image_data = f.read()
        print(f"✅ Test image loaded: {len(image_data)} bytes")
    except Exception as e:
        print(f"❌ Failed to load test image: {e}")
        return

    # Expected correct results for comparison
    expected = {
        'name': 'Lisinopril',
        'strength': '10 mg',  # Should be 10mg, not 1mg
        'form': 'tablet',
        'quantity': '30',
        'patient': 'John Doe',
        'frequency': 'once daily',
        'rx_number': '123456789'
    }

    print(f"\n📋 EXPECTED RESULTS:")
    for key, value in expected.items():
        print(f"   {key}: {value}")

    # Test V1 (Working Backup)
    print(f"\n🔍 TESTING V1 (Working Backup Parser)")
    print("-" * 40)
    try:
        result_v1 = parse_v1(image_data, 'cart_fill')
        print_results("V1 BACKUP", result_v1, expected)
    except Exception as e:
        print(f"❌ V1 test failed: {e}")

    # Test V2 (Refined Parser)
    print(f"\n🔍 TESTING V2 (Refined Parser)")
    print("-" * 40)
    try:
        result_v2 = parse_v2(image_data, 'cart_fill')
        print_results("V2 REFINED", result_v2, expected)
    except Exception as e:
        print(f"❌ V2 test failed: {e}")

    # Comparison Summary
    print(f"\n📊 COMPARISON SUMMARY")
    print("=" * 60)
    print("| Feature          | V1 Backup | V2 Refined |")
    print("|------------------|-----------|------------|")

    try:
        v1_count = len(result_v1.get('medications', []))
        v2_count = len(result_v2.get('medications', []))
        print(f"| Medications Found| {v1_count:>9} | {v2_count:>10} |")

        v1_strength = get_strength(result_v1)
        v2_strength = get_strength(result_v2)
        print(f"| Strength Reading | {v1_strength:>9} | {v2_strength:>10} |")

        v1_conf = get_confidence(result_v1)
        v2_conf = get_confidence(result_v2)
        print(f"| Confidence      | {v1_conf:>9.2f} | {v2_conf:>10.2f} |")

        print("|------------------|-----------|------------|")

        # Winner determination
        print(f"\n🏆 WINNER ANALYSIS:")

        improvements = []
        if v2_count == 1 and v1_count > 1:
            improvements.append("✅ Better deduplication")
        if '10' in v2_strength and '1' in v1_strength and '10' not in v1_strength:
            improvements.append("✅ Fixed strength reading (10mg vs 1mg)")
        if v2_conf > v1_conf:
            improvements.append("✅ Higher confidence")

        if improvements:
            print("V2 REFINED PARSER WINS! 🎉")
            for improvement in improvements:
                print(f"  {improvement}")
        else:
            print("Both parsers perform similarly")

    except Exception as e:
        print(f"Comparison failed: {e}")

def print_results(version, result, expected):
    """Print detailed results for a parser version"""
    success = result.get('success', False)
    medications = result.get('medications', [])
    raw_text = result.get('raw_text', '')

    print(f"Success: {success}")
    print(f"Raw text: \"{raw_text[:100]}...\"" if len(raw_text) > 100 else f"Raw text: \"{raw_text}\"")
    print(f"Medications found: {len(medications)}")

    if medications:
        for i, med in enumerate(medications, 1):
            print(f"\n  Medication {i}:")

            # Check each expected field
            for field, expected_value in expected.items():
                actual_value = med.get(field, 'Missing')
                status = "✅" if str(actual_value).lower() in str(expected_value).lower() else "❌"
                print(f"    {field}: {actual_value} {status}")

            confidence = med.get('confidence', 0)
            print(f"    confidence: {confidence:.2f}")
    else:
        print("  ❌ No medications parsed")

def get_strength(result):
    """Extract strength from first medication"""
    medications = result.get('medications', [])
    if medications:
        return medications[0].get('strength', 'None')
    return 'None'

def get_confidence(result):
    """Extract confidence from first medication"""
    medications = result.get('medications', [])
    if medications:
        return medications[0].get('confidence', 0)
    return 0

if __name__ == "__main__":
    test_all_versions()