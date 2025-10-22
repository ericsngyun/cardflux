#!/usr/bin/env python3
"""
Comprehensive Test Suite for Production Card Identifier
Tests all images in test-images/one-piece/ directory
"""
import sys
import json
import time
from pathlib import Path
from typing import List, Dict
import warnings

warnings.filterwarnings('ignore')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from production_card_identifier import ProductionCardIdentifier


def test_all_images(test_dir: str = "test-images/one-piece") -> Dict:
    """
    Test all images in the test directory.

    Returns:
        Complete test results with statistics
    """
    test_path = Path(test_dir)

    if not test_path.exists():
        print(f"ERROR: Test directory not found: {test_dir}")
        return {}

    # Find all test images
    image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
    test_images = []

    for ext in image_extensions:
        test_images.extend(test_path.glob(f"*{ext}"))

    test_images = sorted(test_images, key=lambda x: x.name)

    print("="*80)
    print("PRODUCTION CARD IDENTIFIER - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"\nTest Directory: {test_dir}")
    print(f"Total Images: {len(test_images)}")
    print()

    # Initialize identifier (once)
    print("[1/3] Initializing identifier...")
    start_init = time.time()
    identifier = ProductionCardIdentifier(game="one-piece", verbose=False)
    init_time = (time.time() - start_init) * 1000
    print(f"[OK] Identifier ready ({init_time:.0f}ms)\n")

    # Test each image
    print("[2/3] Testing all images...")
    print("="*80)

    results = []

    for i, image_path in enumerate(test_images, 1):
        print(f"\n[{i}/{len(test_images)}] {image_path.name}")
        print("-"*80)

        try:
            result = identifier.identify(
                str(image_path),
                top_k=50,
                use_geometric=True,
                tcg_hint="one-piece"
            )

            best = result['best_match']
            scores = result['scores']
            timing = result['timing']
            quality = result['quality_check']

            # Print summary
            print(f"  Card: {best['name']}")
            print(f"  Number: {best['number']}")
            print(f"  Confidence: {result['confidence']}")
            print(f"  Final Score: {scores['final']:.4f}")
            print(f"    - Visual: {scores['visual']:.4f}")
            print(f"    - Geometric: {scores['geometric']:.4f}")
            if scores.get('card_number_boost', 0) > 0:
                print(f"    - Card# Boost: +{scores['card_number_boost']:.4f}")
            if scores.get('foil_boost', 0) > 0:
                print(f"    - Foil Boost: +{scores['foil_boost']:.4f}")
            print(f"  Quality:")
            if 'resolution' in quality:
                print(f"    - Resolution: {quality['resolution'][0]}x{quality['resolution'][1]}")
            print(f"    - Sharpness: {quality.get('sharpness_score', 0):.1f}")
            print(f"    - Quality Tier: {quality.get('quality_tier', 'unknown')}")
            print(f"  Time: {timing['total_ms']}ms")

            # Top 3 matches
            print(f"  Top 3:")
            for j, match in enumerate(result['matches'][:3], 1):
                print(f"    {j}. {match['name']} ({match['number']}) - "
                      f"Final: {match['final_score']:.4f} (V:{match['visual_score']:.3f} G:{match['geometric_score']:.3f})")

            # Store result
            results.append({
                'image': image_path.name,
                'card_name': best['name'],
                'card_number': best['number'],
                'confidence': result['confidence'],
                'final_score': scores['final'],
                'visual_score': scores['visual'],
                'geometric_score': scores['geometric'],
                'quality_tier': quality.get('quality_tier', 'unknown'),
                'resolution': quality.get('resolution', (0, 0)),
                'sharpness': quality.get('sharpness_score', 0),
                'time_ms': timing['total_ms'],
                'foil_detected': result['foil_detected'],
                'top_3_matches': [
                    {
                        'name': m['name'],
                        'number': m['number'],
                        'score': m['final_score']
                    }
                    for m in result['matches'][:3]
                ]
            })

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                'image': image_path.name,
                'error': str(e)
            })

    print("\n" + "="*80)
    print("[3/3] RESULTS SUMMARY")
    print("="*80)

    # Calculate statistics
    successful_tests = [r for r in results if 'error' not in r]

    if not successful_tests:
        print("\nNo successful tests!")
        return {'results': results}

    # Confidence distribution
    high_conf = sum(1 for r in successful_tests if r['confidence'] == 'HIGH')
    moderate_conf = sum(1 for r in successful_tests if r['confidence'] == 'MODERATE')
    low_conf = sum(1 for r in successful_tests if r['confidence'] == 'LOW')

    print(f"\nConfidence Distribution:")
    print(f"  HIGH:     {high_conf}/{len(successful_tests)} ({high_conf/len(successful_tests)*100:.1f}%)")
    print(f"  MODERATE: {moderate_conf}/{len(successful_tests)} ({moderate_conf/len(successful_tests)*100:.1f}%)")
    print(f"  LOW:      {low_conf}/{len(successful_tests)} ({low_conf/len(successful_tests)*100:.1f}%)")

    # Quality distribution
    high_quality = sum(1 for r in successful_tests if r['quality_tier'] == 'high')
    medium_quality = sum(1 for r in successful_tests if r['quality_tier'] == 'medium')
    low_quality = sum(1 for r in successful_tests if r['quality_tier'] == 'low')

    print(f"\nQuality Distribution:")
    print(f"  High:   {high_quality}/{len(successful_tests)} (sharp, large images)")
    print(f"  Medium: {medium_quality}/{len(successful_tests)} (acceptable quality)")
    print(f"  Low:    {low_quality}/{len(successful_tests)} (compressed/small/blurry)")

    # Score statistics
    avg_final = sum(r['final_score'] for r in successful_tests) / len(successful_tests)
    avg_visual = sum(r['visual_score'] for r in successful_tests) / len(successful_tests)
    avg_geometric = sum(r['geometric_score'] for r in successful_tests) / len(successful_tests)

    print(f"\nAverage Scores:")
    print(f"  Final:     {avg_final:.4f}")
    print(f"  Visual:    {avg_visual:.4f}")
    print(f"  Geometric: {avg_geometric:.4f}")

    # Performance statistics
    avg_time = sum(r['time_ms'] for r in successful_tests) / len(successful_tests)
    min_time = min(r['time_ms'] for r in successful_tests)
    max_time = max(r['time_ms'] for r in successful_tests)

    print(f"\nPerformance:")
    print(f"  Average: {avg_time:.0f}ms")
    print(f"  Min:     {min_time:.0f}ms")
    print(f"  Max:     {max_time:.0f}ms")

    # Quality breakdown
    print(f"\n{'='*80}")
    print("DETAILED BREAKDOWN BY QUALITY")
    print("="*80)

    for tier in ['high', 'medium', 'low']:
        tier_results = [r for r in successful_tests if r['quality_tier'] == tier]

        if not tier_results:
            continue

        tier_high = sum(1 for r in tier_results if r['confidence'] == 'HIGH')
        tier_avg_score = sum(r['final_score'] for r in tier_results) / len(tier_results)
        tier_avg_geom = sum(r['geometric_score'] for r in tier_results) / len(tier_results)

        print(f"\n{tier.upper()} Quality Images ({len(tier_results)} images):")
        print(f"  HIGH confidence: {tier_high}/{len(tier_results)} ({tier_high/len(tier_results)*100:.1f}%)")
        print(f"  Avg final score: {tier_avg_score:.4f}")
        print(f"  Avg geometric:   {tier_avg_geom:.4f}")
        print(f"  Images: {', '.join(r['image'] for r in tier_results)}")

    # Foil detection
    foil_detected = sum(1 for r in successful_tests if r['foil_detected'])
    print(f"\nFoil Detection:")
    print(f"  Detected: {foil_detected}/{len(successful_tests)} images")

    print(f"\n{'='*80}")
    print("INDIVIDUAL RESULTS")
    print("="*80)

    # Sort by confidence and score
    sorted_results = sorted(
        successful_tests,
        key=lambda x: (
            {'HIGH': 3, 'MODERATE': 2, 'LOW': 1}[x['confidence']],
            x['final_score']
        ),
        reverse=True
    )

    for r in sorted_results:
        geom_marker = " [G:OK]" if r['geometric_score'] > 0.15 else " [G:WEAK]" if r['geometric_score'] > 0.05 else " [G:FAIL]"
        quality_marker = f" [{r['quality_tier'][0].upper()}Q]"

        print(f"  {r['confidence']:8s} | {r['final_score']:.4f} | {r['image']:45s} | {r['card_name']}{geom_marker}{quality_marker}")

    # Overall assessment
    print(f"\n{'='*80}")
    print("OVERALL ASSESSMENT")
    print("="*80)

    high_conf_rate = high_conf / len(successful_tests) * 100

    if high_conf_rate >= 80:
        verdict = "EXCELLENT"
    elif high_conf_rate >= 60:
        verdict = "GOOD"
    elif high_conf_rate >= 40:
        verdict = "ACCEPTABLE"
    else:
        verdict = "NEEDS IMPROVEMENT"

    print(f"\nSystem Performance: {verdict}")
    print(f"  HIGH confidence rate: {high_conf_rate:.1f}%")
    print(f"  Average final score: {avg_final:.4f}")
    print(f"  Average speed: {avg_time:.0f}ms")

    if low_quality > 0:
        low_quality_high = sum(1 for r in successful_tests if r['quality_tier'] == 'low' and r['confidence'] == 'HIGH')
        low_quality_rate = low_quality_high / low_quality * 100 if low_quality > 0 else 0
        print(f"\nLow Quality Image Performance:")
        print(f"  HIGH confidence on low quality: {low_quality_high}/{low_quality} ({low_quality_rate:.1f}%)")

        if low_quality_rate < 30:
            print(f"  [RECOMMENDATION] Low quality images need improvement")
            print(f"                   Consider: preprocessing enhancements, fine-tuning, or camera upgrades")

    # Save results
    output_file = Path(__file__).parent / "test_all_production_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'results': results,
            'statistics': {
                'total_images': len(test_images),
                'successful': len(successful_tests),
                'high_confidence': high_conf,
                'moderate_confidence': moderate_conf,
                'low_confidence': low_conf,
                'avg_final_score': avg_final,
                'avg_visual_score': avg_visual,
                'avg_geometric_score': avg_geometric,
                'avg_time_ms': avg_time,
                'quality_distribution': {
                    'high': high_quality,
                    'medium': medium_quality,
                    'low': low_quality
                }
            }
        }, f, indent=2)

    print(f"\n[OK] Results saved to: {output_file}")
    print("="*80)

    return {
        'results': results,
        'statistics': {
            'high_confidence_rate': high_conf_rate,
            'avg_final_score': avg_final,
            'avg_time_ms': avg_time
        }
    }


if __name__ == "__main__":
    test_all_images()
