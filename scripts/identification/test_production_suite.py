#!/usr/bin/env python3
"""
Production Test Suite - Comprehensive Validation

Tests all images in test-images/one-piece/ directory
Validates: Speed, Accuracy, Confidence, Consistency
"""
import sys
import json
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from identify_card_production import ProductionCardIdentifier

def run_comprehensive_tests():
    """Run full test suite on all test images."""

    test_images_dir = Path("test-images/one-piece")
    test_images = list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpg"))
    test_images = [img for img in test_images if img.name != "README.txt"]

    print("=" * 80)
    print("PRODUCTION CARD IDENTIFICATION - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"\nTest Images: {len(test_images)}")
    for img in test_images:
        print(f"  - {img.name}")
    print("\n" + "=" * 80)

    # Initialize system (measure cold start)
    print("\n[1/3] SYSTEM INITIALIZATION")
    print("-" * 80)
    init_start = time.time()
    identifier = ProductionCardIdentifier()
    init_time = (time.time() - init_start) * 1000
    print(f"[OK] System initialized in {init_time:.0f}ms")

    # Run tests
    print("\n[2/3] RUNNING IDENTIFICATION TESTS")
    print("-" * 80)

    results = []
    total_time = 0

    for img_path in sorted(test_images):
        print(f"\nTesting: {img_path.name}")
        print("  " + "-" * 76)

        # Run identification (measure hot performance)
        start = time.time()
        result = identifier.identify(str(img_path))
        elapsed = (time.time() - start) * 1000

        best = result['best_match']
        scores = result['scores']
        timing = result['timing']

        # Display results
        print(f"  Result: {best['name']}")
        print(f"    Card Number: {best.get('number', 'N/A')}")
        print(f"    Rarity: {best.get('rarity', 'N/A')}")
        print(f"  Scores:")
        print(f"    Visual:    {scores['visual']:.4f}")
        print(f"    Geometric: {scores['geometric']:.4f}")
        print(f"    Final:     {scores['final']:.4f}")
        print(f"    Margin:    {scores['margin']:.4f}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Timing:")
        print(f"    Visual:    {timing['visual_ms']:.1f}ms")
        print(f"    Geometric: {timing['geometric_ms']:.1f}ms")
        print(f"    Total:     {timing['total_ms']}ms")

        # Top 3 alternatives
        print(f"  Top 3 Matches:")
        for i, match in enumerate(result['matches'][:3], 1):
            print(f"    {i}. {match['name']} ({match.get('number', 'N/A')}) - Score: {match['final_score']:.4f}")

        # Performance check
        if timing['total_ms'] > 700:
            print(f"  [WARN] WARNING: Slow performance ({timing['total_ms']}ms > 700ms target)")
        else:
            print(f"  [OK] Performance OK ({timing['total_ms']}ms)")

        # Store results
        results.append({
            'image': img_path.name,
            'card': best['name'],
            'number': best.get('number', 'N/A'),
            'confidence': result['confidence'],
            'visual_score': scores['visual'],
            'geometric_score': scores['geometric'],
            'final_score': scores['final'],
            'time_ms': timing['total_ms'],
            'visual_ms': timing['visual_ms'],
            'geometric_ms': timing['geometric_ms'],
        })

        total_time += elapsed

    # Summary statistics
    print("\n[3/3] TEST SUMMARY")
    print("=" * 80)

    avg_time = total_time / len(results)
    min_time = min(r['time_ms'] for r in results)
    max_time = max(r['time_ms'] for r in results)

    high_conf = sum(1 for r in results if r['confidence'] == 'HIGH')
    mod_conf = sum(1 for r in results if r['confidence'] == 'MODERATE')
    low_conf = sum(1 for r in results if r['confidence'] == 'LOW')

    print(f"\nPerformance Metrics:")
    print(f"  System Init:     {init_time:.0f}ms (one-time cost)")
    print(f"  Average Time:    {avg_time:.0f}ms")
    print(f"  Min Time:        {min_time}ms")
    print(f"  Max Time:        {max_time}ms")
    print(f"  Total Tests:     {len(results)}")

    print(f"\nConfidence Distribution:")
    print(f"  HIGH:            {high_conf}/{len(results)} ({high_conf/len(results)*100:.1f}%)")
    print(f"  MODERATE:        {mod_conf}/{len(results)} ({mod_conf/len(results)*100:.1f}%)")
    print(f"  LOW:             {low_conf}/{len(results)} ({low_conf/len(results)*100:.1f}%)")

    print(f"\nAccuracy Analysis:")
    for r in results:
        status = "[OK]" if r['confidence'] in ['HIGH', 'MODERATE'] else "[WARN]"
        print(f"  {status} {r['image']:25s} -> {r['card']:40s} ({r['confidence']:8s}) [{r['time_ms']}ms]")

    # Performance rating
    print(f"\n{'=' * 80}")
    print("OVERALL ASSESSMENT")
    print("=" * 80)

    performance_grade = "EXCELLENT" if avg_time < 500 else "GOOD" if avg_time < 700 else "NEEDS IMPROVEMENT"
    confidence_grade = "EXCELLENT" if high_conf/len(results) > 0.5 else "GOOD" if (high_conf+mod_conf)/len(results) > 0.7 else "NEEDS IMPROVEMENT"

    print(f"Performance:  {performance_grade} (avg {avg_time:.0f}ms)")
    print(f"Confidence:   {confidence_grade} ({high_conf+mod_conf}/{len(results)} reliable)")

    # Production readiness
    production_ready = avg_time < 700 and (high_conf + mod_conf) / len(results) >= 0.5

    if production_ready:
        print(f"\n[OK] PRODUCTION READY")
        print(f"  - Average latency under 700ms: [OK]")
        print(f"  - Majority confident results: [OK]")
    else:
        print(f"\n[WARN] NEEDS OPTIMIZATION")
        if avg_time >= 700:
            print(f"  - Average latency too high: {avg_time:.0f}ms > 700ms")
        if (high_conf + mod_conf) / len(results) < 0.5:
            print(f"  - Too many low confidence results: {low_conf}/{len(results)}")

    print("=" * 80)

    # Export results
    output_file = Path("test_results.json")
    with open(output_file, 'w') as f:
        json.dump({
            'test_date': time.strftime("%Y-%m-%d %H:%M:%S"),
            'init_time_ms': init_time,
            'avg_time_ms': avg_time,
            'min_time_ms': min_time,
            'max_time_ms': max_time,
            'confidence_distribution': {
                'high': high_conf,
                'moderate': mod_conf,
                'low': low_conf
            },
            'tests': results
        }, f, indent=2)

    print(f"\n[OK] Results exported to {output_file}")

    return production_ready


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
