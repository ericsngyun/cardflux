#!/usr/bin/env python3
"""
Quick V2 Test - Verifies V2 system works correctly

Uses the existing production test suite images.

Usage:
    python test_v2_quick.py

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

def main():
    """Quick test of V2 system."""
    print("="*80)
    print("CardFlux V2 Identifier - Quick Verification Test")
    print("="*80)
    print()

    # Find test images from production suite
    test_images_dir = Path(__file__).parent.parent.parent / "test-images" / "one-piece"
    test_images = list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpg"))

    if not test_images:
        print(f"[ERROR] No test images found in {test_images_dir}")
        print("Looking for: *.png and *.jpg")
        return 1

    print(f"Found {len(test_images)} test images")
    print()

    # Initialize version manager
    print("[1/4] Initializing Version Manager...")
    manager = IdentifierVersionManager(default_version="v2", enable_fallback=True)
    print("  [OK] Version Manager initialized (v2 with v1 fallback)")
    print()

    # Test single frame identification with V2
    test_image = test_images[0]
    print(f"[2/4] Testing V2 Single Frame Identification...")
    print(f"  Test image: {test_image.name}")

    try:
        start = time.time()
        result = manager.identify(str(test_image), version="v2", fallback_on_low_confidence=True)
        elapsed = time.time() - start

        print(f"  Result: {result['best_match']['name']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Score: {result['best_match']['final_score']:.4f}")
        print(f"  Time: {elapsed*1000:.0f}ms")
        print(f"  Version used: {result.get('version', 'unknown')}")
        print(f"  Fallback used: {result.get('fallback_used', False)}")
        print("  [OK] V2 identification working!")
    except Exception as e:
        print(f"  [ERROR] V2 identification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print()

    # Test multi-frame fusion
    print(f"[3/4] Testing V2 Multi-Frame Fusion...")
    print(f"  Using 3 frames (simulated as same image)")

    try:
        start = time.time()
        multi_result = manager.identify_multi_frame(
            [str(test_image), str(test_image), str(test_image)],
            version="v2"
        )
        elapsed = time.time() - start

        print(f"  Result: {multi_result['best_match']['name']}")
        print(f"  Confidence: {multi_result['confidence']}")
        print(f"  Score: {multi_result['best_match']['final_score']:.4f}")
        print(f"  Fusion votes: {multi_result.get('fusion_votes', 0):.1f}")
        print(f"  Time: {elapsed*1000:.0f}ms (avg {elapsed/3*1000:.0f}ms/frame)")
        print("  [OK] Multi-frame fusion working!")
    except Exception as e:
        print(f"  [ERROR] Multi-frame fusion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print()

    # Get metrics
    print(f"[4/4] Getting Performance Metrics...")
    try:
        metrics = manager.get_metrics()
        print(f"  V1 calls: {metrics['v1']['calls']}")
        print(f"  V2 calls: {metrics['v2']['calls']}")
        if metrics['v2']['calls'] > 0:
            print(f"  V2 avg time: {metrics['v2']['avg_time_ms']:.0f}ms")
            print(f"  V2 HIGH conf rate: {metrics['v2']['high_confidence_rate']*100:.1f}%")
            print(f"  V2 fallback rate: {metrics['v2']['fallback_rate']*100:.1f}%")
        print("  [OK] Metrics collected successfully!")
    except Exception as e:
        print(f"  [ERROR] Failed to get metrics: {e}")
        return 1

    print()
    print("="*80)
    print("[SUCCESS] All V2 features verified successfully!")
    print("="*80)
    print()
    print("Next steps:")
    print("  1. Test with real card photos")
    print("  2. Compare V1 vs V2 accuracy")
    print("  3. Monitor fallback rate in production")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
