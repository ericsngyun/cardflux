#!/usr/bin/env python3
"""
Test V2.1 Geometric & Preprocessing Improvements

Compares V1 baseline vs V2.1 enhanced on all test images.

Key V2.1 improvements:
- Enhanced ORB (2000 features, 12 levels, HARRIS scoring)
- Glare detection and removal
- Adaptive confidence thresholds

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

from production_card_identifier import ProductionCardIdentifier
from production_card_identifier_v2_1 import ProductionCardIdentifierV2_1


def test_v2_1_improvements():
    """Test V2.1 improvements vs V1 baseline."""
    print("="*100)
    print("V1 BASELINE vs V2.1 ENHANCED COMPARISON")
    print("="*100)
    print()

    # Find test images
    test_images_dir = Path(__file__).parent.parent.parent / "test-images" / "one-piece"
    test_images = sorted(list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpg")))

    if not test_images:
        print(f"[ERROR] No test images found in {test_images_dir}")
        return 1

    print(f"Test Images: {len(test_images)}")
    print(f"Directory: {test_images_dir}")
    print()

    # Initialize identifiers
    print("[INIT] Loading V1 baseline...")
    v1 = ProductionCardIdentifier(verbose=False)
    print("[OK] V1 loaded")
    print()

    print("[INIT] Loading V2.1 enhanced...")
    v2_1 = ProductionCardIdentifierV2_1(verbose=True)
    print("[OK] V2.1 loaded")
    print()

    results = []

    for idx, image_path in enumerate(test_images, 1):
        print(f"[{idx}/{len(test_images)}] Testing: {image_path.name}")
        print("-" * 100)

        # Test V1
        print("  [V1 BASELINE]", end=" ")
        try:
            start = time.time()
            v1_result = v1.identify(str(image_path), top_k=50, use_geometric=True)
            v1_time = (time.time() - start) * 1000

            v1_card = v1_result['best_match']['name']
            v1_number = v1_result['best_match']['number']
            v1_conf = v1_result['confidence']
            v1_score = v1_result['best_match']['final_score']
            v1_visual = v1_result['scores']['visual']
            v1_geometric = v1_result['scores']['geometric']

            print(f"{v1_card[:40]:40s} | {v1_conf:8s} | {v1_score:.4f} | {v1_time:.0f}ms")
        except Exception as e:
            print(f"ERROR: {e}")
            v1_card = "ERROR"
            v1_number = "N/A"
            v1_conf = "ERROR"
            v1_score = v1_visual = v1_geometric = v1_time = 0

        # Test V2.1
        print("  [V2.1 ENHANCED]", end=" ")
        try:
            start = time.time()
            v2_1_result = v2_1.identify(str(image_path), top_k=50, use_geometric=True)
            v2_1_time = (time.time() - start) * 1000

            v2_1_card = v2_1_result['best_match']['name']
            v2_1_number = v2_1_result['best_match']['number']
            v2_1_conf = v2_1_result['confidence']
            v2_1_score = v2_1_result['best_match']['final_score']
            v2_1_visual = v2_1_result['scores']['visual']
            v2_1_geometric = v2_1_result['scores']['geometric']

            conf_adj = v2_1_result.get('confidence_adjustment', '')
            adj_str = f" [{conf_adj}]" if conf_adj else ""

            print(f"{v2_1_card[:40]:40s} | {v2_1_conf:8s} | {v2_1_score:.4f} | {v2_1_time:.0f}ms{adj_str}")
        except Exception as e:
            print(f"ERROR: {e}")
            v2_1_card = "ERROR"
            v2_1_number = "N/A"
            v2_1_conf = "ERROR"
            v2_1_score = v2_1_visual = v2_1_geometric = v2_1_time = 0

        # Compare
        same_card = (v1_number == v2_1_number and v1_number != "N/A")
        if same_card:
            print("  [MATCH] Same card identified")
        else:
            print(f"  [DIFF] V1: {v1_number} vs V2.1: {v2_1_number}")

        # Improvements
        improvements = []
        if v2_1_geometric > v1_geometric:
            improvements.append(f"Geometric: +{(v2_1_geometric - v1_geometric):.4f}")
        if v2_1_score > v1_score:
            improvements.append(f"Score: +{(v2_1_score - v1_score):.4f}")
        if v2_1_conf == 'HIGH' and v1_conf != 'HIGH':
            improvements.append("Confidence: UP")

        if improvements:
            print(f"  [IMPROVEMENT] {', '.join(improvements)}")

        print()

        # Store result
        results.append({
            'image': image_path.name,
            'v1': {
                'card': v1_card,
                'number': v1_number,
                'confidence': v1_conf,
                'score': v1_score,
                'visual': v1_visual,
                'geometric': v1_geometric,
                'time_ms': v1_time
            },
            'v2_1': {
                'card': v2_1_card,
                'number': v2_1_number,
                'confidence': v2_1_conf,
                'score': v2_1_score,
                'visual': v2_1_visual,
                'geometric': v2_1_geometric,
                'time_ms': v2_1_time
            },
            'same_card': same_card
        })

    # Summary
    print("="*100)
    print("SUMMARY")
    print("="*100)
    print()

    # Table
    table_data = []
    for r in results:
        table_data.append([
            r['image'][:30],
            r['v1']['confidence'],
            f"{r['v1']['score']:.3f}",
            f"{r['v1']['geometric']:.3f}",
            r['v2_1']['confidence'],
            f"{r['v2_1']['score']:.3f}",
            f"{r['v2_1']['geometric']:.3f}",
            "[OK]" if r['same_card'] else "[DIFF]"
        ])

    headers = ["Image", "V1 Conf", "V1 Score", "V1 Geo", "V2.1 Conf", "V2.1 Score", "V2.1 Geo", "Match"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print()

    # Stats
    total = len(results)
    same_cards = sum(1 for r in results if r['same_card'])

    v1_high = sum(1 for r in results if r['v1']['confidence'] == 'HIGH')
    v2_1_high = sum(1 for r in results if r['v2_1']['confidence'] == 'HIGH')

    v1_avg_score = sum(r['v1']['score'] for r in results) / total
    v2_1_avg_score = sum(r['v2_1']['score'] for r in results) / total

    v1_avg_geo = sum(r['v1']['geometric'] for r in results) / total
    v2_1_avg_geo = sum(r['v2_1']['geometric'] for r in results) / total

    print("STATISTICS")
    print("-" * 100)
    print(f"Total Images: {total}")
    print(f"Same Card: {same_cards}/{total} ({same_cards/total*100:.1f}%)")
    print()
    print("V1 Baseline:")
    print(f"  HIGH Confidence: {v1_high}/{total} ({v1_high/total*100:.1f}%)")
    print(f"  Avg Score: {v1_avg_score:.4f}")
    print(f"  Avg Geometric: {v1_avg_geo:.4f}")
    print()
    print("V2.1 Enhanced:")
    print(f"  HIGH Confidence: {v2_1_high}/{total} ({v2_1_high/total*100:.1f}%)")
    print(f"  Avg Score: {v2_1_avg_score:.4f}")
    print(f"  Avg Geometric: {v2_1_avg_geo:.4f}")
    print()

    # Verdict
    print("VERDICT")
    print("-" * 100)

    improvements = 0
    if v2_1_high > v1_high:
        print(f"[+] V2.1 has more HIGH confidence ({v2_1_high} vs {v1_high})")
        improvements += 1
    elif v1_high > v2_1_high:
        print(f"[-] V1 has more HIGH confidence ({v1_high} vs {v2_1_high})")

    if v2_1_avg_geo > v1_avg_geo:
        improvement = ((v2_1_avg_geo - v1_avg_geo) / v1_avg_geo * 100) if v1_avg_geo > 0 else 0
        print(f"[+] V2.1 has better geometric matching ({v2_1_avg_geo:.4f} vs {v1_avg_geo:.4f}, +{improvement:.1f}%)")
        improvements += 1
    else:
        print(f"[-] V1 has better geometric matching ({v1_avg_geo:.4f} vs {v2_1_avg_geo:.4f})")

    if v2_1_avg_score > v1_avg_score:
        improvement = ((v2_1_avg_score - v1_avg_score) / v1_avg_score * 100)
        print(f"[+] V2.1 has higher average score ({v2_1_avg_score:.4f} vs {v1_avg_score:.4f}, +{improvement:.1f}%)")
        improvements += 1
    else:
        print(f"[-] V1 has higher average score ({v1_avg_score:.4f} vs {v2_1_avg_score:.4f})")

    print()
    if improvements >= 2:
        print(f"[WINNER] V2.1 Enhanced ({improvements}/3 improvements)")
    elif improvements == 0:
        print("[WINNER] V1 Baseline (no improvements)")
    else:
        print("[TIE] Mixed results")

    print()
    print("="*100)

    # Save results
    output_file = "v2_1_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"[OK] Results saved to: {output_file}")
    print()

    return 0


def main():
    """Main entry point."""
    try:
        return test_v2_1_improvements()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
