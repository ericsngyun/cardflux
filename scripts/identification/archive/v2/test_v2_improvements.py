#!/usr/bin/env python3
"""
Test Suite for V2 Identifier Improvements

Compares V1 (baseline) vs V2 (enhanced) performance.

Usage:
    python test_v2_improvements.py

Author: Senior Principal Engineer
Date: 2025-10-21
"""
import sys
import json
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from identifier_version_manager import IdentifierVersionManager

# Test images (from production test suite)
TEST_IMAGES = [
    "test_images/bege.png",
    "test_images/blackbeard.png",
    "test_images/yellow_event.png",
    "test_images/blackbeard-db.jpg",
]

# Expected results (ground truth)
GROUND_TRUTH = {
    "bege.png": {
        "name": "Capone\"Gang\"Bege",
        "number": "ST02-004"
    },
    "blackbeard-db.jpg": {
        "name": "Marshall.D.Teach (093) (Manga)",
        "number": "OP09-093"
    },
    "yellow_event.png": {
        "name": "You're the One Who Should Disappear",
        "number": "OP06-115"
    },
    # blackbeard.png is unknown - need to verify ground truth
}


def test_single_frame_comparison():
    """Test V1 vs V2 on single frames."""
    print("\n" + "="*80)
    print("TEST 1: SINGLE FRAME IDENTIFICATION (V1 vs V2)")
    print("="*80)

    # Initialize version manager
    manager = IdentifierVersionManager(default_version="v2", enable_fallback=True)

    results = {
        'v1': [],
        'v2': [],
        'v2_with_fallback': []
    }

    for image_path in TEST_IMAGES:
        if not Path(image_path).exists():
            print(f"[WARN] Skipping {image_path} (not found)")
            continue

        image_name = Path(image_path).name
        truth = GROUND_TRUTH.get(image_name, {})

        print(f"\n{'─'*80}")
        print(f"Testing: {image_name}")
        if truth:
            print(f"Expected: {truth['name']} ({truth['number']})")
        print(f"{'─'*80}")

        # Test V1
        print(f"\n[V1 Baseline]")
        start = time.time()
        v1_result = manager.identify(image_path, version="v1", fallback_on_low_confidence=False)
        v1_time = time.time() - start

        print(f"  Result: {v1_result['best_match']['name']}")
        print(f"  Confidence: {v1_result['confidence']}")
        print(f"  Score: {v1_result['best_match']['final_score']:.4f}")
        print(f"  Time: {v1_time*1000:.0f}ms")

        # Test V2 without fallback
        print(f"\n[V2 Enhanced - No Fallback]")
        start = time.time()
        v2_result = manager.identify(image_path, version="v2", fallback_on_low_confidence=False)
        v2_time = time.time() - start

        print(f"  Result: {v2_result['best_match']['name']}")
        print(f"  Confidence: {v2_result['confidence']}")
        print(f"  Score: {v2_result['best_match']['final_score']:.4f}")
        print(f"  Time: {v2_time*1000:.0f}ms")

        # Test V2 with fallback
        print(f"\n[V2 Enhanced - With Fallback]")
        start = time.time()
        v2_fb_result = manager.identify(image_path, version="v2", fallback_on_low_confidence=True)
        v2_fb_time = time.time() - start

        fallback_used = v2_fb_result.get('fallback_used', False)
        actual_version = v2_fb_result.get('version', 'v2')

        print(f"  Result: {v2_fb_result['best_match']['name']}")
        print(f"  Confidence: {v2_fb_result['confidence']}")
        print(f"  Score: {v2_fb_result['best_match']['final_score']:.4f}")
        print(f"  Time: {v2_fb_time*1000:.0f}ms")
        print(f"  Fallback Used: {'YES (v2→v1)' if fallback_used else 'NO'}")
        print(f"  Actual Version: {actual_version}")

        # Check correctness
        if truth:
            v1_correct = v1_result['best_match']['number'] == truth['number']
            v2_correct = v2_result['best_match']['number'] == truth['number']
            v2_fb_correct = v2_fb_result['best_match']['number'] == truth['number']

            print(f"\n  Correctness:")
            print(f"    V1: {('[OK] CORRECT' if v1_correct else '[X] WRONG')}")
            print(f"    V2: {('[OK] CORRECT' if v2_correct else '[X] WRONG')}")
            print(f"    V2+FB: {('[OK] CORRECT' if v2_fb_correct else '[X] WRONG')}")
        else:
            v1_correct = v2_correct = v2_fb_correct = None

        # Store results
        results['v1'].append({
            'image': image_name,
            'card': v1_result['best_match']['name'],
            'confidence': v1_result['confidence'],
            'score': v1_result['best_match']['final_score'],
            'time_ms': v1_time * 1000,
            'correct': v1_correct
        })

        results['v2'].append({
            'image': image_name,
            'card': v2_result['best_match']['name'],
            'confidence': v2_result['confidence'],
            'score': v2_result['best_match']['final_score'],
            'time_ms': v2_time * 1000,
            'correct': v2_correct
        })

        results['v2_with_fallback'].append({
            'image': image_name,
            'card': v2_fb_result['best_match']['name'],
            'confidence': v2_fb_result['confidence'],
            'score': v2_fb_result['best_match']['final_score'],
            'time_ms': v2_fb_time * 1000,
            'correct': v2_fb_correct,
            'fallback_used': fallback_used,
            'actual_version': actual_version
        })

    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    for version_name, version_results in results.items():
        print(f"\n{version_name.upper()}:")

        # Calculate metrics
        total = len(version_results)
        avg_time = sum(r['time_ms'] for r in version_results) / total if total > 0 else 0
        high_conf = sum(1 for r in version_results if r['confidence'] == 'HIGH')
        correct = sum(1 for r in version_results if r['correct'] is True)
        known = sum(1 for r in version_results if r['correct'] is not None)

        print(f"  Avg Time: {avg_time:.0f}ms")
        print(f"  HIGH Confidence: {high_conf}/{total} ({high_conf/total*100:.1f}%)")
        if known > 0:
            print(f"  Accuracy: {correct}/{known} ({correct/known*100:.1f}%)")

        if version_name == 'v2_with_fallback':
            fallback_count = sum(1 for r in version_results if r.get('fallback_used', False))
            print(f"  Fallback Used: {fallback_count}/{total} ({fallback_count/total*100:.1f}%)")

    # Get metrics from version manager
    print(f"\n{'='*80}")
    print("VERSION MANAGER METRICS")
    print(f"{'='*80}")
    manager.print_metrics()

    return results


def test_multi_frame_fusion():
    """Test multi-frame fusion (V2 only feature)."""
    print(f"\n{'='*80}")
    print("TEST 2: MULTI-FRAME FUSION (V2 Feature)")
    print(f"{'='*80}")

    # We would need to capture multiple frames of the same card
    # For now, simulate by using the same image 3 times
    test_image = "test_images/bege.png"

    if not Path(test_image).exists():
        print(f"[WARN] Test image not found: {test_image}")
        return

    print(f"\nTesting multi-frame fusion with: {Path(test_image).name}")
    print(f"(Simulating 3 frames of the same card)")

    manager = IdentifierVersionManager(default_version="v2")

    # Single frame (baseline)
    start = time.time()
    single_result = manager.identify(test_image, version="v2")
    single_time = time.time() - start

    print(f"\n[Single Frame]")
    print(f"  Result: {single_result['best_match']['name']}")
    print(f"  Confidence: {single_result['confidence']}")
    print(f"  Score: {single_result['best_match']['final_score']:.4f}")
    print(f"  Time: {single_time*1000:.0f}ms")

    # Multi-frame (simulated)
    start = time.time()
    multi_result = manager.identify_multi_frame(
        [test_image, test_image, test_image],  # Simulated 3 frames
        version="v2"
    )
    multi_time = time.time() - start

    print(f"\n[Multi-Frame Fusion (3 frames)]")
    print(f"  Result: {multi_result['best_match']['name']}")
    print(f"  Confidence: {multi_result['confidence']}")
    print(f"  Score: {multi_result['best_match']['final_score']:.4f}")
    print(f"  Fusion Votes: {multi_result.get('fusion_votes', 0):.1f}")
    print(f"  Agreement: {multi_result.get('fusion_agreement_rate', 0)*100:.1f}%")
    print(f"  Confidence Boost: {multi_result.get('fusion_confidence_boost', False)}")
    print(f"  Time: {multi_time*1000:.0f}ms (avg {multi_time/3*1000:.0f}ms/frame)")

    return single_result, multi_result


def main():
    """Run all tests."""
    print("="*80)
    print("CardFlux V2 Identifier - Comprehensive Test Suite")
    print("="*80)
    print()
    print("Testing improvements:")
    print("  [+] Adaptive preprocessing")
    print("  [+] Adaptive quality thresholds")
    print("  [+] Multi-frame fusion")
    print("  [+] Automatic V1 fallback")
    print()

    try:
        # Test 1: Single frame comparison
        single_frame_results = test_single_frame_comparison()

        # Test 2: Multi-frame fusion
        multi_frame_results = test_multi_frame_fusion()

        # Save results
        output_file = "v2_test_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                'single_frame': single_frame_results,
                'multi_frame': {
                    'single': multi_frame_results[0] if multi_frame_results else None,
                    'multi': multi_frame_results[1] if multi_frame_results else None
                },
                'timestamp': time.time()
            }, f, indent=2)

        print(f"\n{'='*80}")
        print(f"[OK] Test results saved to: {output_file}")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
