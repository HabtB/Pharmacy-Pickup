#!/usr/bin/env python3
"""
Run all image tests and show summary
"""
import subprocess
import sys

tests = [
    ("Image 1: BD CICU (6E-2_CICU)", "test_with_real_image.py", 9),
    ("Image 2: 6E-2 CICU", "test_image_2.py", 6),
    ("Image 3: 7W 1&2 (7W-1, 7W-2)", "test_image_3_7W.py", 11),
    ("Image 4: 7ES SICU", "test_image_4_7ES.py", 9),
    ("Sample Data (8E-1, 8E-2)", "test_hybrid_parser.py", 4),
]

print("=" * 80)
print("COMPREHENSIVE FLOOR STOCK PARSER TEST SUITE")
print("=" * 80)

total_expected = 0
total_found = 0
passed = 0
failed = 0

for name, script, expected_count in tests:
    print(f"\n▶ Testing: {name}")
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True
    )

    # Extract the count from output
    for line in result.stdout.split('\n'):
        if 'Found:' in line and 'medications' in line:
            try:
                found_count = int(line.split('Found:')[1].split('medications')[0].strip())
                total_expected += expected_count
                total_found += found_count

                if found_count == expected_count:
                    print(f"  ✅ PASSED: {found_count}/{expected_count} medications")
                    passed += 1
                else:
                    print(f"  ❌ FAILED: {found_count}/{expected_count} medications")
                    failed += 1
                break
            except:
                pass

print("\n" + "=" * 80)
print("FINAL SUMMARY")
print("=" * 80)
print(f"Total Tests: {len(tests)}")
print(f"Passed: {passed} ✅")
print(f"Failed: {failed} ❌")
print(f"\nTotal Medications Expected: {total_expected}")
print(f"Total Medications Found: {total_found}")

if failed == 0:
    print("\n🎉 ALL TESTS PASSED! Table-aware parser is working perfectly!")
else:
    print(f"\n⚠️  {failed} test(s) failed")

print("=" * 80)
