#!/usr/bin/env python3
"""
Test Watermark Removal Impact on Identification Accuracy

Compares identification results before and after watermark removal preprocessing.
Tests on all images in test-images/one-piece/ and generates detailed comparison.
"""
import sys
import json
import time
from pathlib import Path
from typing import Dict, List

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from production_card_identifier import ProductionCardIdentifier


def load_baseline_results(baseline_file: str) -> Dict:
    """Load baseline test results (before watermark removal)."""
    with open(baseline_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_with_current_index(test_dir: str = None) -> Dict:
    """Test all images with current index."""
    if test_dir is None:
        test_dir = Path(__file__).parent.parent.parent.parent / "test-images" / "one-piece"
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
    print("WATERMARK REMOVAL IMPACT TEST")
    print("="*80)
    print(f"\nTest Directory: {test_dir}")
    print(f"Total Images: {len(test_images)}\n")

    # Initialize identifier
    print("[1/2] Initializing identifier...")
    start_init = time.time()
    identifier = ProductionCardIdentifier(game="one-piece", verbose=False)
    init_time = (time.time() - start_init) * 1000
    print(f"[OK] Identifier ready ({init_time:.0f}ms)\n")

    # Test each image
    print("[2/2] Testing all images...")
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

            # Print summary
            print(f"  Card: {best['name']}")
            print(f"  Number: {best['number']}")
            print(f"  Confidence: {result['confidence']}")
            print(f"  Final Score: {scores['final']:.4f}")
            print(f"    - Visual: {scores['visual']:.4f}")
            print(f"    - Geometric: {scores['geometric']:.4f}")
            print(f"  Time: {timing['total_ms']}ms")

            # Store result
            results.append({
                'image': image_path.name,
                'card_name': best['name'],
                'card_number': best['number'],
                'confidence': result['confidence'],
                'final_score': scores['final'],
                'visual_score': scores['visual'],
                'geometric_score': scores['geometric'],
                'time_ms': timing['total_ms'],
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

    return {
        'results': results,
        'timestamp': time.time(),
        'total_images': len(test_images)
    }


def compare_results(baseline: Dict, current: Dict) -> None:
    """Compare baseline vs current results."""
    print("\n" + "="*80)
    print("COMPARISON: BASELINE vs WATERMARK REMOVAL")
    print("="*80)

    baseline_results = {r['image']: r for r in baseline.get('results', []) if 'error' not in r}
    current_results = {r['image']: r for r in current.get('results', []) if 'error' not in r}

    # Find common images
    common_images = set(baseline_results.keys()) & set(current_results.keys())

    if not common_images:
        print("\nNO COMMON IMAGES - Cannot compare!")
        return

    print(f"\nComparing {len(common_images)} common images...\n")

    # Statistics
    baseline_high = sum(1 for img in common_images if baseline_results[img]['confidence'] == 'HIGH')
    current_high = sum(1 for img in common_images if current_results[img]['confidence'] == 'HIGH')

    baseline_moderate = sum(1 for img in common_images if baseline_results[img]['confidence'] == 'MODERATE')
    current_moderate = sum(1 for img in common_images if current_results[img]['confidence'] == 'MODERATE')

    baseline_low = sum(1 for img in common_images if baseline_results[img]['confidence'] == 'LOW')
    current_low = sum(1 for img in common_images if current_results[img]['confidence'] == 'LOW')

    # Score improvements
    score_improvements = []
    confidence_upgrades = []
    confidence_downgrades = []
    identification_changes = []

    for img in sorted(common_images):
        baseline_r = baseline_results[img]
        current_r = current_results[img]

        score_diff = current_r['final_score'] - baseline_r['final_score']
        score_improvements.append((img, score_diff))

        # Check confidence change
        conf_map = {'HIGH': 3, 'MODERATE': 2, 'LOW': 1}
        baseline_conf = conf_map[baseline_r['confidence']]
        current_conf = conf_map[current_r['confidence']]

        if current_conf > baseline_conf:
            confidence_upgrades.append((img, baseline_r['confidence'], current_r['confidence'], score_diff))
        elif current_conf < baseline_conf:
            confidence_downgrades.append((img, baseline_r['confidence'], current_r['confidence'], score_diff))

        # Check if identified card changed
        if baseline_r['card_number'] != current_r['card_number']:
            identification_changes.append((
                img,
                baseline_r['card_name'],
                baseline_r['card_number'],
                current_r['card_name'],
                current_r['card_number'],
                score_diff
            ))

    # Print summary
    print("CONFIDENCE DISTRIBUTION:")
    print("-"*80)
    print(f"{'Level':<12} | {'Baseline':<15} | {'Current':<15} | {'Change'}")
    print("-"*80)
    total = len(common_images)
    print(f"{'HIGH':<12} | {baseline_high:>3}/{total} ({baseline_high/total*100:>5.1f}%) | {current_high:>3}/{total} ({current_high/total*100:>5.1f}%) | {current_high - baseline_high:+d} ({(current_high - baseline_high)/total*100:+.1f}%)")
    print(f"{'MODERATE':<12} | {baseline_moderate:>3}/{total} ({baseline_moderate/total*100:>5.1f}%) | {current_moderate:>3}/{total} ({current_moderate/total*100:>5.1f}%) | {current_moderate - baseline_moderate:+d} ({(current_moderate - baseline_moderate)/total*100:+.1f}%)")
    print(f"{'LOW':<12} | {baseline_low:>3}/{total} ({baseline_low/total*100:>5.1f}%) | {current_low:>3}/{total} ({current_low/total*100:>5.1f}%) | {current_low - baseline_low:+d} ({(current_low - baseline_low)/total*100:+.1f}%)")

    # Score statistics
    avg_baseline_score = sum(baseline_results[img]['final_score'] for img in common_images) / len(common_images)
    avg_current_score = sum(current_results[img]['final_score'] for img in common_images) / len(common_images)

    print(f"\nAVERAGE SCORES:")
    print("-"*80)
    print(f"Baseline: {avg_baseline_score:.4f}")
    print(f"Current:  {avg_current_score:.4f}")
    print(f"Change:   {avg_current_score - avg_baseline_score:+.4f} ({(avg_current_score - avg_baseline_score)/avg_baseline_score*100:+.1f}%)")

    # Confidence changes
    if confidence_upgrades:
        print(f"\nCONFIDENCE UPGRADES ({len(confidence_upgrades)}):")
        print("-"*80)
        for img, old_conf, new_conf, score_diff in confidence_upgrades:
            print(f"  ✅ {img}: {old_conf} → {new_conf} (score: {score_diff:+.4f})")

    if confidence_downgrades:
        print(f"\nCONFIDENCE DOWNGRADES ({len(confidence_downgrades)}):")
        print("-"*80)
        for img, old_conf, new_conf, score_diff in confidence_downgrades:
            print(f"  ⚠️  {img}: {old_conf} → {new_conf} (score: {score_diff:+.4f})")

    if identification_changes:
        print(f"\nIDENTIFICATION CHANGES ({len(identification_changes)}):")
        print("-"*80)
        for img, old_name, old_num, new_name, new_num, score_diff in identification_changes:
            print(f"  🔄 {img}:")
            print(f"     OLD: {old_name} ({old_num})")
            print(f"     NEW: {new_name} ({new_num})")
            print(f"     Score change: {score_diff:+.4f}")

    # Top improvements
    print(f"\nTOP 5 SCORE IMPROVEMENTS:")
    print("-"*80)
    top_improvements = sorted(score_improvements, key=lambda x: x[1], reverse=True)[:5]
    for img, score_diff in top_improvements:
        baseline_r = baseline_results[img]
        current_r = current_results[img]
        print(f"  {img}: {baseline_r['final_score']:.4f} → {current_r['final_score']:.4f} ({score_diff:+.4f})")

    # Verdict
    print(f"\n{'='*80}")
    print("VERDICT")
    print("="*80)

    high_improved = current_high > baseline_high
    scores_improved = avg_current_score > avg_baseline_score
    no_downgrades = len(confidence_downgrades) == 0

    if high_improved and scores_improved and no_downgrades:
        verdict = "✅ WATERMARK REMOVAL IS BENEFICIAL - KEEP CHANGES"
        print(f"\n{verdict}")
        print("\nReasons:")
        print(f"  ✅ HIGH confidence improved: {baseline_high} → {current_high} ({current_high - baseline_high:+d})")
        print(f"  ✅ Average score improved: {avg_baseline_score:.4f} → {avg_current_score:.4f} ({avg_current_score - avg_baseline_score:+.4f})")
        print(f"  ✅ No confidence downgrades")
    elif high_improved or scores_improved:
        verdict = "⚠️  WATERMARK REMOVAL SHOWS IMPROVEMENT - REVIEW CHANGES"
        print(f"\n{verdict}")
        print("\nReasons:")
        if high_improved:
            print(f"  ✅ HIGH confidence improved: {baseline_high} → {current_high} ({current_high - baseline_high:+d})")
        if scores_improved:
            print(f"  ✅ Average score improved: {avg_baseline_score:.4f} → {avg_current_score:.4f}")
        if confidence_downgrades:
            print(f"  ⚠️  {len(confidence_downgrades)} confidence downgrades detected")
    else:
        verdict = "❌ WATERMARK REMOVAL NOT BENEFICIAL - REVERT CHANGES"
        print(f"\n{verdict}")
        print("\nReasons:")
        print(f"  ❌ HIGH confidence: {baseline_high} → {current_high} ({current_high - baseline_high:+d})")
        print(f"  ❌ Average score: {avg_baseline_score:.4f} → {avg_current_score:.4f} ({avg_current_score - avg_baseline_score:+.4f})")

    print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test watermark removal impact')
    parser.add_argument('--baseline', type=str,
                        default='scripts/identification/tests/test_all_production_results.json',
                        help='Baseline results file (before watermark removal)')
    parser.add_argument('--test-dir', type=str,
                        default=None,
                        help='Test images directory')

    args = parser.parse_args()

    # Load baseline
    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"ERROR: Baseline file not found: {args.baseline}")
        print("Please run: python scripts/identification/tests/test_all_production_images.py")
        sys.exit(1)

    print("Loading baseline results...")
    baseline = load_baseline_results(str(baseline_path))
    print(f"Loaded {len(baseline.get('results', []))} baseline results\n")

    # Test current
    current = test_with_current_index(args.test_dir)

    # Compare
    compare_results(baseline, current)

    # Save current results
    output_file = Path(__file__).parent / "test_watermark_removal_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(current, f, indent=2)

    print(f"\n[OK] Current results saved to: {output_file}")
    print("="*80)
