#!/usr/bin/env python3
"""
Production Test Suite for Card Identification System

Tests all images and generates comprehensive report.
"""
import sys
import json
import time
from pathlib import Path
from typing import List, Dict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from production_card_identifier import ProductionCardIdentifier

# Test cases with expected results
TEST_CASES = [
    {
        "image": "../../test-images/one-piece/bege.png",
        "expected_card": "Capone\"Gang\"Bege",
        "expected_number": "ST02-004",
        "expected_confidence": "HIGH"
    },
    {
        "image": "../../test-images/one-piece/blackbeard.png",
        "expected_card": "Marshall.D.Teach",
        "expected_number": "OP09-093",
        "expected_confidence": "HIGH"
    },
    {
        "image": "../../test-images/one-piece/blackbeard-db.jpg",
        "expected_card": "Marshall.D.Teach",
        "expected_number": "OP09-093",
        "expected_confidence": "HIGH"
    },
    {
        "image": "../../test-images/one-piece/yellow_event.png",
        "expected_card": "You're the One Who Should Disappear",
        "expected_number": "OP06-115",
        "expected_confidence": "MODERATE"  # Known edge case
    }
]


def run_tests(verbose: bool = True):
    """Run all test cases."""
    print("="*70)
    print("PRODUCTION SYSTEM TEST SUITE")
    print("="*70)
    print()

    # Initialize system once
    print("Initializing system...")
    identifier = ProductionCardIdentifier(game="one-piece", verbose=False)
    print("[OK] System initialized\n")

    results = []
    passed = 0
    failed = 0
    total_time = 0

    for i, test in enumerate(TEST_CASES, 1):
        print(f"[Test {i}/{len(TEST_CASES)}] {Path(test['image']).name}")
        print("-" * 70)

        # Check if image exists
        if not Path(test['image']).exists():
            print(f"  [SKIP] Image not found\n")
            continue

        # Run identification
        start = time.time()
        result = identifier.identify(test['image'], tcg_hint="one-piece")
        elapsed = time.time() - start

        best = result['best_match']
        best_name = best['name']
        best_number = best.get('number', '')
        confidence = result['confidence']

        # Check if correct
        card_correct = test['expected_card'] in best_name
        confidence_ok = confidence in ["HIGH", "MODERATE"]

        test_passed = card_correct and confidence_ok

        if test_passed:
            passed += 1
            status = "[PASS]"
        else:
            failed += 1
            status = "[FAIL]"

        # Print results
        print(f"  Status: {status}")
        print(f"  Expected: {test['expected_card']} ({test['expected_number']})")
        print(f"  Got:      {best_name} ({best_number})")
        print(f"  Confidence: {confidence} (expected: {test['expected_confidence']})")
        print(f"  Score: {result['scores']['final']:.4f}")
        print(f"  Time: {result['time_ms']}ms")

        # Additional info
        if result.get('foil_detected'):
            print(f"  Foil: YES ({result['foil_type']}, {result['foil_confidence']:.3f})")
        if result.get('card_number_extracted'):
            print(f"  Card#: {result['card_number_extracted']}")

        print()

        # Store result
        results.append({
            "test_name": Path(test['image']).name,
            "passed": test_passed,
            "expected": test['expected_card'],
            "got": best_name,
            "confidence": confidence,
            "score": result['scores']['final'],
            "time_ms": result['time_ms'],
        })

        total_time += elapsed

    # Summary
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total tests: {len(TEST_CASES)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {passed/len(TEST_CASES)*100:.1f}%")
    print(f"Average time: {total_time/len(TEST_CASES)*1000:.0f}ms")
    print("="*70)

    # Save report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total": len(TEST_CASES),
            "passed": passed,
            "failed": failed,
            "success_rate": passed/len(TEST_CASES)*100,
            "avg_time_ms": total_time/len(TEST_CASES)*1000
        },
        "results": results
    }

    report_file = Path(__file__).parent.parent.parent / "test_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n[OK] Report saved to: {report_file}")

    return passed == len(TEST_CASES)


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
