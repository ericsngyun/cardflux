#!/usr/bin/env python3
"""
Ground Truth Validation System for Card Identification

This tool enables systematic validation of the identification system against
known-correct cards to measure actual accuracy and calibrate confidence thresholds.

Workflow:
1. Create template: python ground_truth_validator.py template
2. Collect 100-200 physical cards
3. Photograph each card (multiple conditions: close-up, distance, sleeved, angled)
4. Fill in ground_truth.json with correct card identities
5. Run validation: python ground_truth_validator.py validate
6. Review calibration recommendations

Author: Senior Principal Engineer
Date: 2025-10-23
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import sys
import argparse
from collections import defaultdict

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

try:
    from production_card_identifier import ProductionCardIdentifier
except ImportError:
    print("ERROR: Could not import ProductionCardIdentifier")
    print("Make sure you're running from the correct directory")
    sys.exit(1)


@dataclass
class GroundTruthEntry:
    """Single ground truth entry."""
    image_path: str
    true_product_id: int
    true_name: str
    true_number: str
    capture_type: str  # 'close_up', 'distance_1ft', 'distance_2ft', 'angled', 'sleeved', 'poor_lighting'
    notes: str = ""


@dataclass
class ValidationResult:
    """Result of validating a single image."""
    image_path: str
    true_product_id: int
    true_name: str
    predicted_id: int
    predicted_name: str
    confidence: str
    final_score: float
    is_correct: bool
    capture_type: str
    time_ms: float


def create_ground_truth_template():
    """
    Create template JSON for ground truth data collection.
    """
    template = {
        "version": "1.0",
        "created": "2025-10-23",
        "game": "one-piece",
        "description": "Ground truth dataset for accuracy validation and confidence calibration",
        "instructions": [
            "1. Photograph each card in multiple conditions (close-up, distance, sleeved, etc.)",
            "2. Fill in true_product_id, true_name, true_number for each image",
            "3. Capture types: close_up, distance_1ft, distance_2ft, angled, sleeved, poor_lighting",
            "4. Save as ground_truth.json",
            "5. Run: python ground_truth_validator.py validate"
        ],
        "cards": [
            {
                "image_path": "ground-truth/card_001_closeup.jpg",
                "true_product_id": 123456,
                "true_name": "Monkey.D.Luffy",
                "true_number": "ST01-012",
                "capture_type": "close_up",
                "notes": "Example entry - mint condition, good lighting"
            },
            {
                "image_path": "ground-truth/card_001_distance.jpg",
                "true_product_id": 123456,
                "true_name": "Monkey.D.Luffy",
                "true_number": "ST01-012",
                "capture_type": "distance_1ft",
                "notes": "Same card at 1 foot distance"
            },
            {
                "image_path": "ground-truth/card_002_closeup.jpg",
                "true_product_id": 789012,
                "true_name": "Roronoa Zoro",
                "true_number": "ST01-013",
                "capture_type": "close_up",
                "notes": "Example entry 2"
            }
        ]
    }

    output_path = Path(__file__).parent.parent.parent / "test-images" / "one-piece" / "ground_truth_template.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    print("="*80)
    print("GROUND TRUTH TEMPLATE CREATED")
    print("="*80)
    print(f"\nTemplate saved: {output_path}")
    print("\nNext Steps:")
    print("1. Create directory: test-images/one-piece/ground-truth/")
    print("2. Photograph 100-200 physical cards you own")
    print("3. Copy template to ground_truth.json and fill in real data")
    print("4. Run validation: python ground_truth_validator.py validate")
    print("\nTips for collecting ground truth:")
    print("  - Use cards you can verify on TCGPlayer")
    print("  - Photograph each card in multiple conditions")
    print("  - Include mix of rarities, foils, and card types")
    print("  - Test edge cases: damaged cards, sleeves, poor lighting")
    print("  - Minimum 50 cards recommended, 100+ ideal")


def validate_against_ground_truth(ground_truth_path: str, verbose: bool = False):
    """
    Validate identifier against ground truth dataset.

    Args:
        ground_truth_path: Path to ground_truth.json
        verbose: Print detailed progress

    Returns:
        Validation results dictionary
    """
    # Load ground truth
    gt_path = Path(ground_truth_path)
    if not gt_path.exists():
        print(f"ERROR: Ground truth file not found: {ground_truth_path}")
        print("\nDid you create it? Run: python ground_truth_validator.py template")
        sys.exit(1)

    with open(gt_path, encoding='utf-8') as f:
        data = json.load(f)

    entries = [GroundTruthEntry(**e) for e in data['cards']]
    game = data.get('game', 'one-piece')

    print("="*80)
    print("GROUND TRUTH VALIDATION")
    print("="*80)
    print(f"Game: {game}")
    print(f"Total Images: {len(entries)}")
    print(f"Ground Truth File: {ground_truth_path}")
    print()

    # Initialize identifier
    print("Initializing identifier...")
    start_init = time.time()
    identifier = ProductionCardIdentifier(game=game, verbose=False)
    init_time = (time.time() - start_init) * 1000
    print(f"Identifier ready ({init_time:.0f}ms)\n")

    # Validate each image
    results = []
    stats = {
        'correct': 0,
        'wrong': 0,
        'high_conf_correct': 0,
        'high_conf_wrong': 0,
        'moderate_conf_correct': 0,
        'moderate_conf_wrong': 0,
        'low_conf_correct': 0,
        'low_conf_wrong': 0,
        'by_capture_type': defaultdict(lambda: {'correct': 0, 'wrong': 0}),
        'failures': [],
        'total_time_ms': 0
    }

    print("Validating images...")
    print("="*80)

    for i, entry in enumerate(entries, 1):
        image_name = Path(entry.image_path).name

        # Check if image exists
        image_path = Path(entry.image_path)
        if not image_path.is_absolute():
            # Try relative to ground truth file
            image_path = gt_path.parent / entry.image_path

        if not image_path.exists():
            print(f"\n[{i}/{len(entries)}] {image_name}")
            print(f"  ✗ SKIP: Image not found: {image_path}")
            continue

        if verbose:
            print(f"\n[{i}/{len(entries)}] {image_name}")

        # Identify card
        try:
            start = time.time()
            result = identifier.identify(
                str(image_path),
                top_k=50,
                use_geometric=True,
                tcg_hint=game
            )
            elapsed_ms = (time.time() - start) * 1000
            stats['total_time_ms'] += elapsed_ms

            predicted_id = result['best_match']['product_id']
            predicted_name = result['best_match']['name']
            confidence = result['confidence']
            final_score = result['scores']['final']

            # Check if correct
            is_correct = (predicted_id == entry.true_product_id)

            # Store result
            validation_result = ValidationResult(
                image_path=str(image_path),
                true_product_id=entry.true_product_id,
                true_name=entry.true_name,
                predicted_id=predicted_id,
                predicted_name=predicted_name,
                confidence=confidence,
                final_score=final_score,
                is_correct=is_correct,
                capture_type=entry.capture_type,
                time_ms=elapsed_ms
            )
            results.append(validation_result)

            # Update stats
            if is_correct:
                stats['correct'] += 1
                if not verbose:
                    print(f"[{i}/{len(entries)}] ✓ {image_name} ({confidence})")
                else:
                    print(f"  ✓ CORRECT: {predicted_name} ({confidence}, {elapsed_ms:.0f}ms)")
            else:
                stats['wrong'] += 1
                print(f"[{i}/{len(entries)}] ✗ {image_name} ({confidence})")
                if verbose:
                    print(f"  Expected: {entry.true_name}")
                    print(f"  Got:      {predicted_name}")

                stats['failures'].append({
                    'image': str(image_path),
                    'expected': entry.true_name,
                    'expected_id': entry.true_product_id,
                    'got': predicted_name,
                    'got_id': predicted_id,
                    'confidence': confidence,
                    'score': final_score,
                    'capture_type': entry.capture_type
                })

            # Track by confidence level
            if confidence == 'HIGH':
                if is_correct:
                    stats['high_conf_correct'] += 1
                else:
                    stats['high_conf_wrong'] += 1
            elif confidence == 'MODERATE':
                if is_correct:
                    stats['moderate_conf_correct'] += 1
                else:
                    stats['moderate_conf_wrong'] += 1
            else:
                if is_correct:
                    stats['low_conf_correct'] += 1
                else:
                    stats['low_conf_wrong'] += 1

            # Track by capture type
            if is_correct:
                stats['by_capture_type'][entry.capture_type]['correct'] += 1
            else:
                stats['by_capture_type'][entry.capture_type]['wrong'] += 1

        except Exception as e:
            print(f"\n[{i}/{len(entries)}] {image_name}")
            print(f"  ✗ ERROR: {str(e)}")
            continue

    # Generate report
    print("\n" + "="*80)
    print("VALIDATION REPORT")
    print("="*80)

    total = stats['correct'] + stats['wrong']
    if total == 0:
        print("\nERROR: No valid images processed")
        return stats

    overall_accuracy = (stats['correct'] / total * 100)
    avg_time = stats['total_time_ms'] / total if total > 0 else 0

    print(f"\nOverall Results:")
    print(f"  Total Images:     {total}")
    print(f"  Correct:          {stats['correct']} ({overall_accuracy:.1f}%)")
    print(f"  Wrong:            {stats['wrong']}")
    print(f"  Average Time:     {avg_time:.0f}ms")

    # Confidence-level accuracy
    print(f"\nAccuracy by Confidence Level:")

    high_total = stats['high_conf_correct'] + stats['high_conf_wrong']
    if high_total > 0:
        high_acc = stats['high_conf_correct'] / high_total * 100
        high_pct = high_total / total * 100
        status = "✓ EXCELLENT" if high_acc >= 95 else "⚠️  NEEDS CALIBRATION"
        print(f"  HIGH:     {stats['high_conf_correct']}/{high_total} ({high_acc:.1f}%) - {high_pct:.0f}% of images {status}")
    else:
        print(f"  HIGH:     No images with HIGH confidence")

    mod_total = stats['moderate_conf_correct'] + stats['moderate_conf_wrong']
    if mod_total > 0:
        mod_acc = stats['moderate_conf_correct'] / mod_total * 100
        mod_pct = mod_total / total * 100
        status = "✓ GOOD" if mod_acc >= 85 else "⚠️  NEEDS CALIBRATION"
        print(f"  MODERATE: {stats['moderate_conf_correct']}/{mod_total} ({mod_acc:.1f}%) - {mod_pct:.0f}% of images {status}")
    else:
        print(f"  MODERATE: No images with MODERATE confidence")

    low_total = stats['low_conf_correct'] + stats['low_conf_wrong']
    if low_total > 0:
        low_acc = stats['low_conf_correct'] / low_total * 100
        low_pct = low_total / total * 100
        print(f"  LOW:      {stats['low_conf_correct']}/{low_total} ({low_acc:.1f}%) - {low_pct:.0f}% of images")
    else:
        print(f"  LOW:      No images with LOW confidence")

    # By capture type
    if stats['by_capture_type']:
        print(f"\nAccuracy by Capture Type:")
        for capture_type, ct_stats in sorted(stats['by_capture_type'].items()):
            ct_total = ct_stats['correct'] + ct_stats['wrong']
            ct_acc = ct_stats['correct'] / ct_total * 100 if ct_total > 0 else 0
            print(f"  {capture_type:20s}: {ct_stats['correct']}/{ct_total} ({ct_acc:.1f}%)")

    # Failure cases
    if stats['failures']:
        print(f"\nFailure Cases ({len(stats['failures'])} total):")
        for failure in stats['failures'][:10]:  # Show top 10
            print(f"  - {Path(failure['image']).name} ({failure['capture_type']})")
            print(f"    Expected: {failure['expected']}")
            print(f"    Got:      {failure['got']} ({failure['confidence']}, score={failure['score']:.3f})")

    # Save detailed report
    report_dir = Path(__file__).parent.parent.parent / "test-results" / "current"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / "ground_truth_validation_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total': total,
                'correct': stats['correct'],
                'wrong': stats['wrong'],
                'overall_accuracy': overall_accuracy,
                'avg_time_ms': avg_time
            },
            'by_confidence': {
                'high': {
                    'correct': stats['high_conf_correct'],
                    'wrong': stats['high_conf_wrong'],
                    'total': high_total,
                    'accuracy': high_acc if high_total > 0 else 0
                },
                'moderate': {
                    'correct': stats['moderate_conf_correct'],
                    'wrong': stats['moderate_conf_wrong'],
                    'total': mod_total,
                    'accuracy': mod_acc if mod_total > 0 else 0
                },
                'low': {
                    'correct': stats['low_conf_correct'],
                    'wrong': stats['low_conf_wrong'],
                    'total': low_total,
                    'accuracy': low_acc if low_total > 0 else 0
                }
            },
            'by_capture_type': dict(stats['by_capture_type']),
            'failures': stats['failures'],
            'results': [asdict(r) for r in results]
        }, f, indent=2)

    print(f"\nDetailed report saved: {report_path}")

    # Calibration recommendations
    print("\n" + "="*80)
    print("CALIBRATION RECOMMENDATIONS")
    print("="*80)

    recommendations = []

    if high_total > 0:
        if high_acc < 95:
            recommendations.append(
                f"⚠️  HIGH confidence accuracy is {high_acc:.1f}% (target: 95%+)\n"
                f"    Action: Increase THRESHOLD_HIGH from 0.70 to 0.75"
            )
        else:
            recommendations.append(f"✓  HIGH confidence is {high_acc:.1f}% - EXCELLENT!")

    if mod_total > 0:
        if mod_acc < 85:
            recommendations.append(
                f"⚠️  MODERATE confidence accuracy is {mod_acc:.1f}% (target: 85%+)\n"
                f"    Action: Increase THRESHOLD_MODERATE from 0.55 to 0.60"
            )
        else:
            recommendations.append(f"✓  MODERATE confidence is {mod_acc:.1f}% - GOOD!")

    if overall_accuracy < 90:
        recommendations.append(
            f"⚠️  Overall accuracy is {overall_accuracy:.1f}% (target: 90%+)\n"
            f"    Action: Consider implementing optimizations:\n"
            f"      - OCR hard filter\n"
            f"      - SIFT geometric matching\n"
            f"      - dinov2-base model upgrade"
        )

    if not recommendations:
        recommendations.append("✓  All metrics are within target ranges - system is well-calibrated!")

    for rec in recommendations:
        print(f"\n{rec}")

    print("\n" + "="*80)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ground Truth Validation Tool for Card Identification"
    )
    parser.add_argument(
        'command',
        choices=['template', 'validate'],
        help='Command to run: template (create template) or validate (run validation)'
    )
    parser.add_argument(
        '--ground-truth',
        default='test-images/one-piece/ground_truth.json',
        help='Path to ground truth JSON file (default: test-images/one-piece/ground_truth.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed progress'
    )

    args = parser.parse_args()

    if args.command == 'template':
        create_ground_truth_template()
    elif args.command == 'validate':
        validate_against_ground_truth(args.ground_truth, verbose=args.verbose)
