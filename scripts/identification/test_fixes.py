#!/usr/bin/env python3
"""
Quick test script to validate identification improvements.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from production_card_identifier import ProductionCardIdentifier

def test_all_images():
    """Test all images in test-images/one-piece/"""
    test_dir = Path("test-images/one-piece")
    test_images = [
        "bege.png",
        "blackbeard.png",
        "blackbeard-db.jpg",
        "yellow_event.png"
    ]

    print("=" * 80)
    print("IDENTIFICATION SYSTEM - POST-FIX VALIDATION")
    print("=" * 80)
    print("\nInitializing system...")

    identifier = ProductionCardIdentifier(verbose=False)

    print(f"Testing {len(test_images)} images...\n")

    results = []
    for img_name in test_images:
        img_path = test_dir / img_name
        if not img_path.exists():
            print(f"[SKIP] {img_name} - not found")
            continue

        print(f"\n{'='*80}")
        print(f"Testing: {img_name}")
        print("=" * 80)

        result = identifier.identify(str(img_path), top_k=50)

        best = result['best_match']
        quality = result['quality_check']

        print(f"\nResult:")
        print(f"  Card:       {best['name']}")
        print(f"  Number:     {best['number']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Final Score: {result['scores']['final']:.4f}")
        print(f"  Visual:      {result['scores']['visual']:.4f}")
        print(f"  Geometric:   {result['scores']['geometric']:.4f}")
        print(f"\nQuality:")
        print(f"  Acceptable:  {quality['is_acceptable']}")
        print(f"  Sharpness:   {quality['sharpness_score']:.1f}")
        print(f"  Brightness:  {quality['brightness']:.1f}")
        if quality['warnings']:
            print(f"  Warnings:    {', '.join(quality['warnings'])}")

        print(f"\nTiming:")
        print(f"  Total: {result['time_ms']}ms")

        results.append({
            'image': img_name,
            'card': best['name'],
            'confidence': result['confidence'],
            'score': result['scores']['final'],
            'time_ms': result['time_ms']
        })

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print("=" * 80)

    high_conf = sum(1 for r in results if r['confidence'] == 'HIGH')
    mod_conf = sum(1 for r in results if r['confidence'] == 'MODERATE')
    low_conf = sum(1 for r in results if r['confidence'] == 'LOW')

    avg_time = sum(r['time_ms'] for r in results) / len(results) if results else 0

    print(f"\nTotal tests: {len(results)}")
    print(f"Confidence distribution:")
    print(f"  HIGH:     {high_conf}/{len(results)} ({high_conf/len(results)*100:.1f}%)")
    print(f"  MODERATE: {mod_conf}/{len(results)} ({mod_conf/len(results)*100:.1f}%)")
    print(f"  LOW:      {low_conf}/{len(results)} ({low_conf/len(results)*100:.1f}%)")
    print(f"\nAverage time: {avg_time:.0f}ms")

    print(f"\nDetailed results:")
    for r in results:
        conf_emoji = "✅" if r['confidence'] in ['HIGH', 'MODERATE'] else "⚠️"
        print(f"  {conf_emoji} {r['image']:25s} -> {r['card']:45s} [{r['confidence']:8s}] ({r['score']:.3f})")

    print("=" * 80)

if __name__ == "__main__":
    test_all_images()
