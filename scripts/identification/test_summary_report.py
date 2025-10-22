#!/usr/bin/env python3
"""
Generate a clean one-page summary report of test results
"""
import json
from pathlib import Path
from datetime import datetime

def generate_report(results_file="test_all_production_results.json"):
    """Generate a clean one-page summary report."""

    results_path = Path(__file__).parent / results_file

    if not results_path.exists():
        print(f"ERROR: Results file not found: {results_file}")
        print("Please run test_all_production_images.py first")
        return

    with open(results_path, 'r') as f:
        data = json.load(f)

    results = data['results']
    stats = data['statistics']

    # Generate report
    print("=" * 80)
    print("  PRODUCTION CARD IDENTIFIER TEST REPORT")
    print("=" * 80)
    print(f" Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Total Images: {stats['total_images']}")
    print(f" System: Production Card Identifier with AKAZE Hybrid Geometric Matching")
    print("=" * 80)
    print()

    # Overall statistics
    print("-" * 80)
    print(" OVERALL PERFORMANCE")
    print("-" * 80)

    high_rate = stats['high_confidence'] / stats['successful'] * 100
    moderate_rate = stats['moderate_confidence'] / stats['successful'] * 100
    low_rate = stats['low_confidence'] / stats['successful'] * 100

    print(f" Confidence Distribution:")
    print(f"   [HIGH]     {stats['high_confidence']}/{stats['successful']} ({high_rate:.1f}%)")
    print(f"   [MODERATE] {stats['moderate_confidence']}/{stats['successful']} ({moderate_rate:.1f}%)")
    print(f"   [LOW]      {stats['low_confidence']}/{stats['successful']} ({low_rate:.1f}%)")
    print()
    print(f" Average Scores:")
    print(f"   Final Score:    {stats['avg_final_score']:.4f}")
    print(f"   Visual Score:   {stats['avg_visual_score']:.4f}")
    print(f"   Geometric Score: {stats['avg_geometric_score']:.4f}")
    print()
    print(f" Performance:")
    print(f"   Average Time: {stats['avg_time_ms']:.0f}ms")
    print("-" * 80)
    print()

    # Individual test results
    print("=" * 80)
    print(" TEST RESULTS - INDIVIDUAL IMAGES")
    print("=" * 80)

    # Sort by confidence then score
    sorted_results = sorted(
        results,
        key=lambda x: (
            {'HIGH': 3, 'MODERATE': 2, 'LOW': 1}[x['confidence']],
            x['final_score']
        ),
        reverse=True
    )

    for i, r in enumerate(sorted_results, 1):
        # Header for each image
        geom_status = "[G:OK]" if r['geometric_score'] > 0.15 else "[G:WEAK]" if r['geometric_score'] > 0.05 else "[G:FAIL]"

        print()
        print(f"[{i}] {r['image']}")
        print(f"    Confidence: [{r['confidence']}]  {geom_status}")
        print()
        print(f"    Identified Card: {r['card_name']}")
        print(f"    Card Number:     {r['card_number']}")
        print()
        print(f"    Scores:")
        print(f"      Final:     {r['final_score']:.4f}")
        print(f"      Visual:    {r['visual_score']:.4f}")
        print(f"      Geometric: {r['geometric_score']:.4f}")
        print()
        print(f"    Quality:")
        print(f"      Sharpness: {r['sharpness']:.1f}")
        print(f"      Foil:      {'YES' if r['foil_detected'] else 'NO'}")
        print(f"      Time:      {r['time_ms']}ms")
        print()
        print(f"    Top 3 Matches:")

        for j, match in enumerate(r['top_3_matches'], 1):
            print(f"      {j}. {match['name'][:50]:<50s} {match['number']:<10s} {match['score']:.4f}")

        print("    " + "-" * 76)

    print()
    print("=" * 80)
    print(" VERDICT & RECOMMENDATIONS")
    print("=" * 80)

    if high_rate >= 80:
        verdict = "EXCELLENT - Production Ready"
    elif high_rate >= 60:
        verdict = "GOOD - Deploy with Monitoring"
    elif high_rate >= 40:
        verdict = "ACCEPTABLE - Needs Minor Improvements"
    else:
        verdict = "NEEDS IMPROVEMENT - Major Work Required"

    print(f" Overall Assessment: {verdict}")
    print()

    # Recommendations
    if high_rate < 70:
        print(f" Recommendations:")

        # Check geometric failures
        geom_fails = sum(1 for r in results if r['geometric_score'] < 0.05)
        if geom_fails > len(results) * 0.3:
            print(f"   [!] {geom_fails}/{len(results)} images have geometric match failures")
            print(f"       -> Consider: Multi-scale matching or RANSAC filtering")

        # Check low visual scores
        low_visual = sum(1 for r in results if r['visual_score'] < 0.65)
        if low_visual > len(results) * 0.3:
            print(f"   [!] {low_visual}/{len(results)} images have low visual similarity")
            print(f"       -> Consider: Preprocessing enhancements or DINOv2 fine-tuning")

        # Check low quality images
        low_quality = sum(1 for r in results if r['sharpness'] < 2000)
        if low_quality > len(results) * 0.3:
            print(f"   [!] {low_quality}/{len(results)} images are low quality (blurry/compressed)")
            print(f"       -> Consider: Camera upgrades (4K + digital zoom)")
    else:
        print(f" System performing well! Minor optimizations possible:")
        print(f"   - Fine-tune for 90%+ HIGH confidence")
        print(f"   - Optimize speed (target <600ms average)")

    print("=" * 80)
    print()

    # Legend
    print("Legend:")
    print("  Confidence: HIGH (>0.70), MODERATE (>0.55), LOW (<0.55)")
    print("  Geometric:  [G:OK] Strong (>0.15)   [G:WEAK] Weak (0.05-0.15)   [G:FAIL] Failed (<0.05)")
    print()


if __name__ == "__main__":
    generate_report()
