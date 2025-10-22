#!/usr/bin/env python3
"""
Test AKAZE Hybrid Improvements
Compare ORB-only vs ORB+AKAZE hybrid on distance/compressed images
"""
import sys
import cv2
from pathlib import Path
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from production_card_identifier import ProductionCardIdentifier

def test_geometric_comparison(test_image, reference_card_id="653833"):
    """Test ORB vs AKAZE vs Hybrid on a specific image."""

    print("="*80)
    print(f"TESTING GEOMETRIC MATCHING: {Path(test_image).name}")
    print("="*80)
    print()

    # Load identifier
    print("[1/2] Loading identifier...")
    identifier = ProductionCardIdentifier(game="one-piece", verbose=False)
    print(f"[OK] Identifier loaded\n")

    # Find reference image
    images_dir = Path("data/images/one-piece")
    ref_image = None
    for ext in ['.jpg', '.jpeg', '.png']:
        ref_path = images_dir / f"{reference_card_id}{ext}"
        if ref_path.exists():
            ref_image = str(ref_path)
            break

    if not ref_image:
        print(f"[ERROR] Reference image not found for card {reference_card_id}")
        return

    print(f"Query: {test_image}")
    print(f"Reference: {ref_image}")
    print()

    # Test ORB only
    print("[2/3] Testing ORB only...")
    start = time.time()
    orb_score = identifier._compute_orb_similarity(test_image, ref_image)
    orb_time = (time.time() - start) * 1000
    print(f"  ORB Score: {orb_score:.4f} ({orb_time:.0f}ms)")

    # Test AKAZE only
    print("\n[3/3] Testing AKAZE only...")
    start = time.time()
    akaze_score = identifier._compute_akaze_similarity(test_image, ref_image)
    akaze_time = (time.time() - start) * 1000
    print(f"  AKAZE Score: {akaze_score:.4f} ({akaze_time:.0f}ms)")

    # Test Hybrid
    print("\n[4/3] Testing Hybrid (ORB->AKAZE)...")
    start = time.time()
    hybrid_score = identifier._compute_geometric_similarity_hybrid(test_image, ref_image)
    hybrid_time = (time.time() - start) * 1000
    print(f"  Hybrid Score: {hybrid_score:.4f} ({hybrid_time:.0f}ms)")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"ORB:    {orb_score:.4f} ({orb_time:.0f}ms)")
    print(f"AKAZE:  {akaze_score:.4f} ({akaze_time:.0f}ms)")
    print(f"Hybrid: {hybrid_score:.4f} ({hybrid_time:.0f}ms)")
    print()

    # Verdict
    if akaze_score > orb_score and akaze_score > 0:
        improvement = ((akaze_score - orb_score) / max(orb_score, 0.01)) * 100
        print(f"✅ AKAZE RESCUED! +{improvement:.1f}% improvement ({orb_score:.4f} → {akaze_score:.4f})")
    elif orb_score > 0.10:
        print(f"✅ ORB SUFFICIENT ({orb_score:.4f}), no AKAZE needed")
    else:
        print(f"❌ BOTH FAILED (ORB: {orb_score:.4f}, AKAZE: {akaze_score:.4f})")

    print()

if __name__ == "__main__":
    # Test on compressed Discord screenshots (known ORB failures)
    test_images = [
        "test-images/one-piece/Screenshot_20251021_085328_Discord.jpg",
        "test-images/one-piece/Screenshot_20251021_085344_Discord.jpg",
        "test-images/one-piece/Screenshot_20251021_085357_Discord.jpg",
    ]

    for test_img in test_images:
        if Path(test_img).exists():
            test_geometric_comparison(test_img)
        else:
            print(f"[SKIP] {test_img} not found")

    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)
