#!/usr/bin/env python3
"""
Visual Test Report - Detailed Analysis of Card Identification

Shows top matches with confidence scores for manual verification.
"""
import sys
import json
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from identify_card_production import ProductionCardIdentifier

def run_visual_tests():
    """Run tests and generate detailed visual report."""

    test_images_dir = Path("test-images/one-piece")
    test_images = list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpg"))
    test_images = [img for img in test_images if img.name != "README.txt"]

    print("=" * 100)
    print("VISUAL TEST REPORT - CARD IDENTIFICATION ACCURACY")
    print("=" * 100)
    print(f"\nFound {len(test_images)} test images\n")

    # Initialize system
    print("Initializing system...")
    identifier = ProductionCardIdentifier()
    print()

    all_results = []

    for img_path in sorted(test_images):
        print("=" * 100)
        print(f"TEST IMAGE: {img_path.name}")
        print("=" * 100)

        # Run identification
        start = time.time()
        result = identifier.identify(str(img_path), top_k=20)
        elapsed = (time.time() - start) * 1000

        best = result['best_match']
        scores = result['scores']

        print(f"\n[BEST MATCH]")
        print(f"  Card: {best['name']}")
        print(f"  Number: {best.get('number', 'N/A')}")
        print(f"  Set: {best.get('set', 'N/A')}")
        print(f"  Rarity: {best.get('rarity', 'N/A')}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Time: {elapsed:.0f}ms")

        print(f"\n[SCORES]")
        print(f"  Visual Score:    {scores['visual']:.4f} (70% weight)")
        print(f"  Geometric Score: {scores['geometric']:.4f} (30% weight)")
        print(f"  Final Score:     {scores['final']:.4f}")
        print(f"  Margin:          {scores['margin']:.4f}")

        print(f"\n[TOP 5 MATCHES]")
        print(f"{'Rank':<6} {'Card Name':<50} {'Number':<12} {'Visual':<8} {'Geometric':<10} {'Final':<8}")
        print("-" * 100)

        for i, match in enumerate(result['matches'][:5], 1):
            name = match['name'][:47] + "..." if len(match['name']) > 50 else match['name']
            number = match.get('number', 'N/A')
            visual = match['visual_score']
            geometric = match['geometric_score']
            final = match['final_score']

            print(f"{i:<6} {name:<50} {number:<12} {visual:<8.4f} {geometric:<10.4f} {final:<8.4f}")

        print(f"\n[ANALYSIS]")

        # Confidence analysis
        if result['confidence'] == 'HIGH':
            print(f"  [OK] HIGH confidence - Strong match detected")
        elif result['confidence'] == 'MODERATE':
            print(f"  [WARN] MODERATE confidence - Acceptable but not perfect")
        else:
            print(f"  [WARN] LOW confidence - Manual verification recommended")

        # Performance analysis
        if elapsed < 500:
            print(f"  [OK] Performance: {elapsed:.0f}ms (EXCELLENT)")
        elif elapsed < 700:
            print(f"  [OK] Performance: {elapsed:.0f}ms (GOOD)")
        else:
            print(f"  [WARN] Performance: {elapsed:.0f}ms (SLOW)")

        # Visual vs Geometric analysis
        if scores['visual'] >= 0.75:
            print(f"  [OK] Visual match is strong ({scores['visual']:.4f})")
        elif scores['visual'] >= 0.65:
            print(f"  [WARN] Visual match is moderate ({scores['visual']:.4f})")
        else:
            print(f"  [WARN] Visual match is weak ({scores['visual']:.4f})")

        if scores['geometric'] >= 0.20:
            print(f"  [OK] Geometric verification confirms match ({scores['geometric']:.4f})")
        elif scores['geometric'] > 0:
            print(f"  [WARN] Geometric verification is weak ({scores['geometric']:.4f})")
        else:
            print(f"  [WARN] No geometric features matched ({scores['geometric']:.4f})")

        # Margin analysis
        if scores['margin'] >= 0.10:
            print(f"  [OK] Clear winner with {scores['margin']:.4f} margin")
        elif scores['margin'] >= 0.05:
            print(f"  [WARN] Moderate margin of {scores['margin']:.4f}")
        else:
            print(f"  [WARN] Close competition - margin only {scores['margin']:.4f}")

        all_results.append({
            'image': img_path.name,
            'best_match': best['name'],
            'number': best.get('number', 'N/A'),
            'confidence': result['confidence'],
            'visual': scores['visual'],
            'geometric': scores['geometric'],
            'final': scores['final'],
            'margin': scores['margin'],
            'time_ms': elapsed,
            'top_5': [
                {
                    'name': m['name'],
                    'number': m.get('number', 'N/A'),
                    'visual': m['visual_score'],
                    'geometric': m['geometric_score'],
                    'final': m['final_score']
                }
                for m in result['matches'][:5]
            ]
        })

        print()

    # Summary
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)

    high_conf = sum(1 for r in all_results if r['confidence'] == 'HIGH')
    mod_conf = sum(1 for r in all_results if r['confidence'] == 'MODERATE')
    low_conf = sum(1 for r in all_results if r['confidence'] == 'LOW')

    avg_time = sum(r['time_ms'] for r in all_results) / len(all_results)
    avg_visual = sum(r['visual'] for r in all_results) / len(all_results)
    avg_geometric = sum(r['geometric'] for r in all_results) / len(all_results)

    print(f"\nConfidence Distribution:")
    print(f"  HIGH:     {high_conf}/{len(all_results)} ({high_conf/len(all_results)*100:.1f}%)")
    print(f"  MODERATE: {mod_conf}/{len(all_results)} ({mod_conf/len(all_results)*100:.1f}%)")
    print(f"  LOW:      {low_conf}/{len(all_results)} ({low_conf/len(all_results)*100:.1f}%)")

    print(f"\nAverage Scores:")
    print(f"  Visual:    {avg_visual:.4f}")
    print(f"  Geometric: {avg_geometric:.4f}")
    print(f"  Time:      {avg_time:.0f}ms")

    print(f"\nPer-Image Results:")
    print(f"{'Image':<30} {'Match':<40} {'Conf':<10} {'Visual':<8} {'Geometric':<10} {'Time':<8}")
    print("-" * 100)
    for r in all_results:
        img_name = r['image'][:27] + "..." if len(r['image']) > 30 else r['image']
        match_name = r['best_match'][:37] + "..." if len(r['best_match']) > 40 else r['best_match']
        print(f"{img_name:<30} {match_name:<40} {r['confidence']:<10} {r['visual']:<8.4f} {r['geometric']:<10.4f} {r['time_ms']:<8.0f}")

    # Export detailed results
    output_file = Path("visual_test_results.json")
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n[OK] Detailed results exported to {output_file}")
    print("=" * 100)

    return all_results


if __name__ == "__main__":
    run_visual_tests()
