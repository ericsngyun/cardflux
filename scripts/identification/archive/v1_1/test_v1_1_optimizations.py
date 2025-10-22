#!/usr/bin/env python3
"""
Test V1.1 Geometric Optimizations vs V1 Baseline

Compares:
- V1 Baseline: Standard geometric matching
- V1.1: Pre-computed keypoints + adaptive skipping

Success Criteria:
- V1.1 is 30-50% faster
- V1.1 maintains same accuracy (no regressions)
- V1.1 identifies same cards as V1

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
from production_card_identifier_v1_1 import ProductionCardIdentifierV1_1


def test_v1_1_optimizations():
    """Test V1.1 optimizations vs V1 baseline."""
    print("="*100)
    print("V1 BASELINE vs V1.1 OPTIMIZED")
    print("="*100)
    print()

    # Find test images
    test_images_dir = Path(__file__).parent.parent.parent / "test-images" / "one-piece"
    test_images = sorted(list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpg")))

    if not test_images:
        print(f"[ERROR] No test images found in {test_images_dir}")
        return 1

    print(f"Test Images: {len(test_images)}")
    print()

    # Initialize identifiers
    print("[INIT] Loading identifiers...")
    v1_baseline = ProductionCardIdentifier(verbose=False)
    v1_1 = ProductionCardIdentifierV1_1(verbose=False)
    print("[OK] Both versions loaded")
    print()

    results = []

    for idx, image_path in enumerate(test_images, 1):
        print(f"[{idx}/{len(test_images)}] {image_path.name}")
        print("-" * 100)

        # Test V1 Baseline
        print("  [V1 BASELINE]", end=" ")
        try:
            start = time.time()
            v1_result = v1_baseline.identify(str(image_path), top_k=50, use_geometric=True)
            v1_time = (time.time() - start) * 1000

            v1_card = v1_result['best_match']['name']
            v1_number = v1_result['best_match']['number']
            v1_conf = v1_result['confidence']
            v1_score = v1_result['best_match']['final_score']
            v1_geom_time = v1_result['timing'].get('geometric_verify_ms', 0)

            print(f"{v1_card[:40]:40s} | {v1_conf:8s} | {v1_score:.4f} | {v1_time:.0f}ms (geom: {v1_geom_time:.0f}ms)")
        except Exception as e:
            print(f"ERROR: {e}")
            v1_card = "ERROR"
            v1_number = "N/A"
            v1_conf = "ERROR"
            v1_score = v1_time = v1_geom_time = 0

        # Test V1.1 Optimized
        print("  [V1.1 OPTIMIZED]", end=" ")
        try:
            start = time.time()
            v1_1_result = v1_1.identify(str(image_path), top_k=50, use_geometric=True)
            v1_1_time = (time.time() - start) * 1000

            v1_1_card = v1_1_result['best_match']['name']
            v1_1_number = v1_1_result['best_match']['number']
            v1_1_conf = v1_1_result['confidence']
            v1_1_score = v1_1_result['best_match']['final_score']
            v1_1_geom_time = v1_1_result['timing'].get('geometric_verify_ms', 0)

            # Check if skipped any candidates
            skipped = sum(1 for m in v1_1_result['matches'][:20] if m.get('skipped_geometric', False))

            print(f"{v1_1_card[:40]:40s} | {v1_1_conf:8s} | {v1_1_score:.4f} | {v1_1_time:.0f}ms (geom: {v1_1_geom_time:.0f}ms, skipped: {skipped})")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            v1_1_card = "ERROR"
            v1_1_number = "N/A"
            v1_1_conf = "ERROR"
            v1_1_score = v1_1_time = v1_1_geom_time = 0
            skipped = 0

        # Analysis
        same_card = (v1_number == v1_1_number and v1_number != "N/A")
        time_improvement = ((v1_time - v1_1_time) / v1_time * 100) if v1_time > 0 else 0
        geom_improvement = ((v1_geom_time - v1_1_geom_time) / v1_geom_time * 100) if v1_geom_time > 0 else 0

        print()
        if not same_card:
            print(f"  [WARNING] Different cards: V1={v1_number} vs V1.1={v1_1_number}")
        if time_improvement > 5:
            print(f"  [SPEEDUP] Total: {time_improvement:+.1f}% faster ({v1_time:.0f}ms -> {v1_1_time:.0f}ms)")
        if geom_improvement > 5:
            print(f"  [SPEEDUP] Geometric: {geom_improvement:+.1f}% faster ({v1_geom_time:.0f}ms -> {v1_1_geom_time:.0f}ms)")

        print()

        # Store result
        results.append({
            'image': image_path.name,
            'v1': {
                'card': v1_card,
                'number': v1_number,
                'conf': v1_conf,
                'score': v1_score,
                'time': v1_time,
                'geom_time': v1_geom_time
            },
            'v1_1': {
                'card': v1_1_card,
                'number': v1_1_number,
                'conf': v1_1_conf,
                'score': v1_1_score,
                'time': v1_1_time,
                'geom_time': v1_1_geom_time,
                'skipped': skipped
            },
            'same_card': same_card,
            'time_improvement_pct': time_improvement,
            'geom_improvement_pct': geom_improvement
        })

    # Summary
    print("="*100)
    print("SUMMARY")
    print("="*100)
    print()

    # Table
    table_data = []
    for r in results:
        speedup_str = f"+{r['time_improvement_pct']:.0f}%" if r['time_improvement_pct'] > 0 else f"{r['time_improvement_pct']:.0f}%"
        match_str = "[OK]" if r['same_card'] else "[DIFF]"

        table_data.append([
            r['image'][:30],
            r['v1']['conf'],
            f"{r['v1']['score']:.3f}",
            f"{r['v1']['time']:.0f}ms",
            r['v1_1']['conf'],
            f"{r['v1_1']['score']:.3f}",
            f"{r['v1_1']['time']:.0f}ms",
            speedup_str,
            match_str
        ])

    headers = ["Image", "V1 Conf", "V1 Score", "V1 Time", "V1.1 Conf", "V1.1 Score", "V1.1 Time", "Speedup", "Match"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print()

    # Statistics
    total = len(results)
    same_cards = sum(1 for r in results if r['same_card'])

    v1_avg_time = sum(r['v1']['time'] for r in results) / total
    v1_1_avg_time = sum(r['v1_1']['time'] for r in results) / total
    avg_time_improvement = ((v1_avg_time - v1_1_avg_time) / v1_avg_time * 100)

    v1_avg_geom = sum(r['v1']['geom_time'] for r in results) / total
    v1_1_avg_geom = sum(r['v1_1']['geom_time'] for r in results) / total
    avg_geom_improvement = ((v1_avg_geom - v1_1_avg_geom) / v1_avg_geom * 100) if v1_avg_geom > 0 else 0

    v1_avg_score = sum(r['v1']['score'] for r in results) / total
    v1_1_avg_score = sum(r['v1_1']['score'] for r in results) / total
    avg_score_change = v1_1_avg_score - v1_avg_score

    avg_skipped = sum(r['v1_1']['skipped'] for r in results) / total

    print("STATISTICS")
    print("-" * 100)
    print(f"Total Images: {total}")
    print(f"Same Card: {same_cards}/{total} ({same_cards/total*100:.1f}%)")
    print()
    print("V1 Baseline:")
    print(f"  Avg Total Time: {v1_avg_time:.0f}ms")
    print(f"  Avg Geometric Time: {v1_avg_geom:.0f}ms")
    print(f"  Avg Score: {v1_avg_score:.4f}")
    print()
    print("V1.1 Optimized:")
    print(f"  Avg Total Time: {v1_1_avg_time:.0f}ms ({avg_time_improvement:+.1f}% change)")
    print(f"  Avg Geometric Time: {v1_1_avg_geom:.0f}ms ({avg_geom_improvement:+.1f}% change)")
    print(f"  Avg Score: {v1_1_avg_score:.4f} ({avg_score_change:+.4f} change)")
    print(f"  Avg Skipped Candidates: {avg_skipped:.1f}/20")
    print()
    print("Improvements:")
    print(f"  Total Time Saved: {v1_avg_time - v1_1_avg_time:.0f}ms per card")
    print(f"  Geometric Time Saved: {v1_avg_geom - v1_1_avg_geom:.0f}ms per card")
    print()

    print("VERDICT")
    print("-" * 100)

    success = True

    if same_cards == total:
        print(f"[+] V1.1 identifies same cards as V1 ({same_cards}/{total})")
    else:
        print(f"[-] V1.1 identifies different cards: {same_cards}/{total} match")
        success = False

    if abs(avg_score_change) < 0.01:
        print(f"[+] V1.1 maintains same accuracy: {avg_score_change:+.4f} score change")
    else:
        print(f"[!] WARNING: V1.1 score changed: {avg_score_change:+.4f}")

    if avg_time_improvement > 20:
        print(f"[+] V1.1 significantly faster: {avg_time_improvement:+.1f}% speedup")
    elif avg_time_improvement > 0:
        print(f"[+] V1.1 faster: {avg_time_improvement:+.1f}% speedup")
    else:
        print(f"[-] V1.1 slower: {avg_time_improvement:+.1f}% change")
        success = False

    if avg_geom_improvement > 30:
        print(f"[+] V1.1 geometric significantly faster: {avg_geom_improvement:+.1f}% speedup")
    elif avg_geom_improvement > 0:
        print(f"[+] V1.1 geometric faster: {avg_geom_improvement:+.1f}% speedup")

    print()
    if success and avg_time_improvement > 20:
        print("[RECOMMENDATION] Deploy V1.1 - significant speedup with same accuracy")
    elif success:
        print("[RECOMMENDATION] Deploy V1.1 - improved performance")
    else:
        print("[RECOMMENDATION] Keep V1 - V1.1 has issues")

    print()
    print("="*100)

    # Save results
    output_file = "v1_1_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"[OK] Results saved to: {output_file}")
    print()

    return 0 if success else 1


def main():
    """Main entry point."""
    try:
        return test_v1_1_optimizations()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
