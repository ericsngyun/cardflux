#!/usr/bin/env python3
"""
Comprehensive Test - V1 vs V2 on All Test Images

Tests both V1 and V2 on all available test images and provides detailed comparison.

Usage:
    python test_all_images.py

Author: Senior Principal Engineer
Date: 2025-10-21
"""
import sys
import json
import time
from pathlib import Path
from tabulate import tabulate

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from identifier_version_manager import IdentifierVersionManager


def test_all_images():
    """Test V1 vs V2 on all test images."""

    # Find test images
    test_images_dir = Path(__file__).parent.parent.parent / "test-images" / "one-piece"
    test_images = sorted(list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpg")))

    if not test_images:
        print(f"[ERROR] No test images found in {test_images_dir}")
        return 1

    print("="*100)
    print("CARDFLUX V1 vs V2 COMPREHENSIVE TEST")
    print("="*100)
    print(f"\nTest Images Directory: {test_images_dir}")
    print(f"Total Images: {len(test_images)}")
    print()

    # Initialize version manager
    print("[INIT] Loading V1 and V2 identifiers...")
    manager = IdentifierVersionManager(default_version="v2", enable_fallback=False)

    # Pre-load both versions
    manager.get_identifier("v1")
    manager.get_identifier("v2")
    print("[OK] Both versions loaded\n")

    results = []

    for idx, image_path in enumerate(test_images, 1):
        print(f"[{idx}/{len(test_images)}] Testing: {image_path.name}")
        print("-" * 100)

        # Test V1
        print("  [V1] Identifying...")
        try:
            start = time.time()
            v1_result = manager.identify(str(image_path), version="v1", fallback_on_low_confidence=False)
            v1_time = (time.time() - start) * 1000

            v1_card = v1_result['best_match']['name']
            v1_number = v1_result['best_match']['number']
            v1_conf = v1_result['confidence']
            v1_score = v1_result['best_match']['final_score']
            v1_visual = v1_result['scores']['visual']
            v1_geometric = v1_result['scores']['geometric']

            print(f"       Result: {v1_card}")
            print(f"       Number: {v1_number}")
            print(f"       Confidence: {v1_conf}")
            print(f"       Score: {v1_score:.4f} (visual: {v1_visual:.4f}, geometric: {v1_geometric:.4f})")
            print(f"       Time: {v1_time:.0f}ms")
        except Exception as e:
            print(f"       [ERROR] {e}")
            v1_card = "ERROR"
            v1_number = "N/A"
            v1_conf = "ERROR"
            v1_score = 0
            v1_time = 0
            v1_visual = 0
            v1_geometric = 0

        # Test V2
        print("  [V2] Identifying...")
        try:
            start = time.time()
            v2_result = manager.identify(str(image_path), version="v2", fallback_on_low_confidence=False)
            v2_time = (time.time() - start) * 1000

            v2_card = v2_result['best_match']['name']
            v2_number = v2_result['best_match']['number']
            v2_conf = v2_result['confidence']
            v2_score = v2_result['best_match']['final_score']
            v2_visual = v2_result['scores']['visual']
            v2_geometric = v2_result['scores']['geometric']

            print(f"       Result: {v2_card}")
            print(f"       Number: {v2_number}")
            print(f"       Confidence: {v2_conf}")
            print(f"       Score: {v2_score:.4f} (visual: {v2_visual:.4f}, geometric: {v2_geometric:.4f})")
            print(f"       Time: {v2_time:.0f}ms")
        except Exception as e:
            print(f"       [ERROR] {e}")
            v2_card = "ERROR"
            v2_number = "N/A"
            v2_conf = "ERROR"
            v2_score = 0
            v2_time = 0
            v2_visual = 0
            v2_geometric = 0

        # Compare
        same_card = (v1_number == v2_number and v1_number != "N/A")
        better_version = "SAME"
        if not same_card:
            if v1_score > v2_score:
                better_version = "V1"
            elif v2_score > v1_score:
                better_version = "V2"
            else:
                better_version = "TIE"

        if same_card:
            comparison = "[OK] SAME CARD"
        else:
            comparison = f"[DIFF] Different cards (better: {better_version})"

        print(f"  [CMP] {comparison}")
        print()

        # Store result
        results.append({
            'image': image_path.name,
            'v1_card': v1_card,
            'v1_number': v1_number,
            'v1_conf': v1_conf,
            'v1_score': v1_score,
            'v1_time': v1_time,
            'v2_card': v2_card,
            'v2_number': v2_number,
            'v2_conf': v2_conf,
            'v2_score': v2_score,
            'v2_time': v2_time,
            'same_card': same_card,
            'better': better_version
        })

    # Generate summary
    print("="*100)
    print("SUMMARY")
    print("="*100)
    print()

    # Summary table
    table_data = []
    for r in results:
        table_data.append([
            r['image'],
            f"{r['v1_card'][:30]}..." if len(r['v1_card']) > 30 else r['v1_card'],
            r['v1_conf'],
            f"{r['v1_score']:.3f}",
            f"{r['v1_time']:.0f}ms",
            f"{r['v2_card'][:30]}..." if len(r['v2_card']) > 30 else r['v2_card'],
            r['v2_conf'],
            f"{r['v2_score']:.3f}",
            f"{r['v2_time']:.0f}ms",
            "[OK]" if r['same_card'] else f"[{r['better']}]"
        ])

    headers = [
        "Image",
        "V1 Card",
        "V1 Conf",
        "V1 Score",
        "V1 Time",
        "V2 Card",
        "V2 Conf",
        "V2 Score",
        "V2 Time",
        "Match"
    ]

    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print()

    # Statistics
    total = len(results)
    same_cards = sum(1 for r in results if r['same_card'])
    different_cards = total - same_cards

    v1_high = sum(1 for r in results if r['v1_conf'] == 'HIGH')
    v2_high = sum(1 for r in results if r['v2_conf'] == 'HIGH')

    v1_avg_time = sum(r['v1_time'] for r in results) / total if total > 0 else 0
    v2_avg_time = sum(r['v2_time'] for r in results) / total if total > 0 else 0

    v1_avg_score = sum(r['v1_score'] for r in results) / total if total > 0 else 0
    v2_avg_score = sum(r['v2_score'] for r in results) / total if total > 0 else 0

    print("STATISTICS")
    print("-" * 100)
    print(f"Total Images: {total}")
    print(f"Same Card Identified: {same_cards}/{total} ({same_cards/total*100:.1f}%)")
    print(f"Different Cards: {different_cards}/{total} ({different_cards/total*100:.1f}%)")
    print()
    print("V1 (Baseline):")
    print(f"  HIGH Confidence: {v1_high}/{total} ({v1_high/total*100:.1f}%)")
    print(f"  Avg Score: {v1_avg_score:.4f}")
    print(f"  Avg Time: {v1_avg_time:.0f}ms")
    print()
    print("V2 (Enhanced):")
    print(f"  HIGH Confidence: {v2_high}/{total} ({v2_high/total*100:.1f}%)")
    print(f"  Avg Score: {v2_avg_score:.4f}")
    print(f"  Avg Time: {v2_avg_time:.0f}ms")
    print()

    # Determine winner
    print("VERDICT")
    print("-" * 100)

    v2_wins = 0
    v1_wins = 0

    if v2_high > v1_high:
        print(f"[+] V2 has more HIGH confidence results ({v2_high} vs {v1_high})")
        v2_wins += 1
    elif v1_high > v2_high:
        print(f"[-] V1 has more HIGH confidence results ({v1_high} vs {v2_high})")
        v1_wins += 1
    else:
        print(f"[=] Same HIGH confidence rate ({v1_high}/{total})")

    if v2_avg_score > v1_avg_score:
        print(f"[+] V2 has higher average score ({v2_avg_score:.4f} vs {v1_avg_score:.4f})")
        v2_wins += 1
    elif v1_avg_score > v2_avg_score:
        print(f"[-] V1 has higher average score ({v1_avg_score:.4f} vs {v2_avg_score:.4f})")
        v1_wins += 1
    else:
        print(f"[=] Same average score ({v1_avg_score:.4f})")

    if v2_avg_time < v1_avg_time:
        speedup = (v1_avg_time - v2_avg_time) / v1_avg_time * 100
        print(f"[+] V2 is faster ({v2_avg_time:.0f}ms vs {v1_avg_time:.0f}ms, {speedup:.1f}% speedup)")
        v2_wins += 1
    elif v1_avg_time < v2_avg_time:
        slowdown = (v2_avg_time - v1_avg_time) / v1_avg_time * 100
        print(f"[-] V1 is faster ({v1_avg_time:.0f}ms vs {v2_avg_time:.0f}ms, V2 {slowdown:.1f}% slower)")
        v1_wins += 1
    else:
        print(f"[=] Same speed ({v1_avg_time:.0f}ms)")

    print()
    if v2_wins > v1_wins:
        print(f"[WINNER] V2 Enhanced ({v2_wins} wins vs {v1_wins})")
    elif v1_wins > v2_wins:
        print(f"[WINNER] V1 Baseline ({v1_wins} wins vs {v2_wins})")
    else:
        print(f"[TIE] V1 and V2 are equal ({v1_wins} wins each)")

    print()
    print("="*100)

    # Save results
    output_file = "test_all_images_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'results': results,
            'statistics': {
                'total': total,
                'same_cards': same_cards,
                'different_cards': different_cards,
                'v1': {
                    'high_confidence': v1_high,
                    'avg_score': v1_avg_score,
                    'avg_time_ms': v1_avg_time
                },
                'v2': {
                    'high_confidence': v2_high,
                    'avg_score': v2_avg_score,
                    'avg_time_ms': v2_avg_time
                }
            }
        }, f, indent=2)

    print(f"[OK] Results saved to: {output_file}")
    print()

    return 0


def main():
    """Main entry point."""
    try:
        return test_all_images()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
