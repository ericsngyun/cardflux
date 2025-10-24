#!/usr/bin/env python3
"""
Test V1 + TTA (Test-Time Augmentation)

Compares V1 baseline vs V1+TTA on all test images.

Goal: Verify TTA improves accuracy without regressions
Success Criteria:
- TTA improves scores on MODERATE/LOW images
- TTA does NOT reduce scores on HIGH images
- TTA provides +5-12% average improvement

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
from production_card_identifier_v1_tta import ProductionCardIdentifierV1_TTA


def test_v1_tta():
    """Test V1+TTA vs V1 baseline."""
    print("="*100)
    print("V1 BASELINE vs V1+TTA COMPARISON")
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
    v1_tta = ProductionCardIdentifierV1_TTA(verbose=False)
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

            print(f"{v1_card[:40]:40s} | {v1_conf:8s} | {v1_score:.4f} | {v1_time:.0f}ms")
        except Exception as e:
            print(f"ERROR: {e}")
            v1_card = "ERROR"
            v1_number = "N/A"
            v1_conf = "ERROR"
            v1_score = v1_time = 0

        # Test V1+TTA
        print("  [V1+TTA]      ", end=" ")
        try:
            start = time.time()
            tta_result = v1_tta.identify_with_tta(str(image_path), top_k=50, use_geometric=True)
            tta_time = (time.time() - start) * 1000

            tta_card = tta_result['best_match']['name']
            tta_number = tta_result['best_match']['number']
            tta_conf = tta_result['confidence']
            tta_score = tta_result['best_match']['final_score']
            tta_boost = tta_result.get('tta_boost', 0)
            tta_agreement = tta_result.get('tta_agreement', 0)

            print(f"{tta_card[:40]:40s} | {tta_conf:8s} | {tta_score:.4f} | {tta_time:.0f}ms | Boost: +{tta_boost:.4f} | Agr: {tta_agreement*100:.0f}%")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            tta_card = "ERROR"
            tta_number = "N/A"
            tta_conf = "ERROR"
            tta_score = tta_time = tta_boost = tta_agreement = 0

        # Analysis
        same_card = (v1_number == tta_number and v1_number != "N/A")
        score_change = tta_score - v1_score
        conf_improved = (
            (v1_conf == 'LOW' and tta_conf in ['MODERATE', 'HIGH']) or
            (v1_conf == 'MODERATE' and tta_conf == 'HIGH')
        )
        conf_regressed = (
            (v1_conf == 'HIGH' and tta_conf in ['MODERATE', 'LOW']) or
            (v1_conf == 'MODERATE' and tta_conf == 'LOW')
        )

        print()
        if not same_card:
            print(f"  [WARNING] Different cards: V1={v1_number} vs TTA={tta_number}")
        if conf_improved:
            print(f"  [IMPROVEMENT] Confidence: {v1_conf} -> {tta_conf}")
        if conf_regressed:
            print(f"  [REGRESSION] Confidence: {v1_conf} -> {tta_conf} [WARNING]")
        if score_change > 0.01:
            print(f"  [BOOST] Score: +{score_change:.4f} ({score_change/v1_score*100:.1f}%)")
        elif score_change < -0.01:
            print(f"  [REDUCTION] Score: {score_change:.4f} ({score_change/v1_score*100:.1f}%) [WARNING]")

        print()

        # Store result
        results.append({
            'image': image_path.name,
            'v1': {
                'card': v1_card,
                'number': v1_number,
                'conf': v1_conf,
                'score': v1_score,
                'time': v1_time
            },
            'tta': {
                'card': tta_card,
                'number': tta_number,
                'conf': tta_conf,
                'score': tta_score,
                'time': tta_time,
                'boost': tta_boost,
                'agreement': tta_agreement
            },
            'same_card': same_card,
            'score_change': score_change,
            'conf_improved': conf_improved,
            'conf_regressed': conf_regressed
        })

    # Summary
    print("="*100)
    print("SUMMARY")
    print("="*100)
    print()

    # Table
    table_data = []
    for r in results:
        change_str = f"+{r['score_change']:.3f}" if r['score_change'] >= 0 else f"{r['score_change']:.3f}"
        match_str = "[OK]" if r['same_card'] else "[DIFF]"

        if r['conf_improved']:
            conf_str = f"{r['v1']['conf']} -> {r['tta']['conf']} [UP]"
        elif r['conf_regressed']:
            conf_str = f"{r['v1']['conf']} -> {r['tta']['conf']} [DOWN]"
        else:
            conf_str = r['v1']['conf']

        table_data.append([
            r['image'][:30],
            r['v1']['conf'],
            f"{r['v1']['score']:.3f}",
            r['tta']['conf'],
            f"{r['tta']['score']:.3f}",
            change_str,
            conf_str,
            match_str
        ])

    headers = ["Image", "V1 Conf", "V1 Score", "TTA Conf", "TTA Score", "Change", "Confidence", "Match"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print()

    # Statistics
    total = len(results)
    same_cards = sum(1 for r in results if r['same_card'])
    conf_improvements = sum(1 for r in results if r['conf_improved'])
    conf_regressions = sum(1 for r in results if r['conf_regressed'])

    v1_avg_score = sum(r['v1']['score'] for r in results) / total
    tta_avg_score = sum(r['tta']['score'] for r in results) / total
    avg_score_change = tta_avg_score - v1_avg_score

    v1_high = sum(1 for r in results if r['v1']['conf'] == 'HIGH')
    tta_high = sum(1 for r in results if r['tta']['conf'] == 'HIGH')

    v1_avg_time = sum(r['v1']['time'] for r in results) / total
    tta_avg_time = sum(r['tta']['time'] for r in results) / total

    # Score improvements by confidence level
    high_results = [r for r in results if r['v1']['conf'] == 'HIGH']
    moderate_results = [r for r in results if r['v1']['conf'] == 'MODERATE']
    low_results = [r for r in results if r['v1']['conf'] == 'LOW']

    print("STATISTICS")
    print("-" * 100)
    print(f"Total Images: {total}")
    print(f"Same Card: {same_cards}/{total} ({same_cards/total*100:.1f}%)")
    print()
    print("V1 Baseline:")
    print(f"  Avg Score: {v1_avg_score:.4f}")
    print(f"  HIGH Confidence: {v1_high}/{total} ({v1_high/total*100:.1f}%)")
    print(f"  Avg Time: {v1_avg_time:.0f}ms")
    print()
    print("V1+TTA:")
    print(f"  Avg Score: {tta_avg_score:.4f} ({avg_score_change:+.4f}, {avg_score_change/v1_avg_score*100:+.1f}%)")
    print(f"  HIGH Confidence: {tta_high}/{total} ({tta_high/total*100:.1f}%)")
    print(f"  Avg Time: {tta_avg_time:.0f}ms (+{tta_avg_time-v1_avg_time:.0f}ms overhead)")
    print()
    print("Confidence Changes:")
    print(f"  Improvements: {conf_improvements}/{total}")
    print(f"  Regressions: {conf_regressions}/{total}")
    print()

    if high_results:
        high_avg_change = sum(r['score_change'] for r in high_results) / len(high_results)
        print(f"HIGH Confidence Images ({len(high_results)}):")
        print(f"  Avg Score Change: {high_avg_change:+.4f}")

    if moderate_results:
        moderate_avg_change = sum(r['score_change'] for r in moderate_results) / len(moderate_results)
        print(f"MODERATE Confidence Images ({len(moderate_results)}):")
        print(f"  Avg Score Change: {moderate_avg_change:+.4f}")

    if low_results:
        low_avg_change = sum(r['score_change'] for r in low_results) / len(low_results)
        print(f"LOW Confidence Images ({len(low_results)}):")
        print(f"  Avg Score Change: {low_avg_change:+.4f}")

    print()
    print("VERDICT")
    print("-" * 100)

    success = True
    reasons = []

    if avg_score_change > 0.03:  # >3% improvement
        print(f"[+] TTA improves average score: +{avg_score_change:.4f} ({avg_score_change/v1_avg_score*100:+.1f}%)")
        reasons.append("score_improvement")
    elif avg_score_change > 0:
        print(f"[~] TTA slightly improves average score: +{avg_score_change:.4f} ({avg_score_change/v1_avg_score*100:+.1f}%)")
    else:
        print(f"[-] TTA reduces average score: {avg_score_change:.4f} ({avg_score_change/v1_avg_score*100:+.1f}%)")
        success = False

    if conf_improvements > 0:
        print(f"[+] TTA improved confidence on {conf_improvements} image(s)")
        reasons.append("confidence_improvement")

    if conf_regressions > 0:
        print(f"[!] WARNING: TTA regressed confidence on {conf_regressions} image(s)")
        success = False

    if tta_high > v1_high:
        print(f"[+] TTA increased HIGH confidence count: {v1_high} -> {tta_high}")
        reasons.append("more_high_confidence")

    print()
    if success and len(reasons) >= 2:
        print("[RECOMMENDATION] Deploy V1+TTA - improves accuracy without regressions")
    elif success:
        print("[RECOMMENDATION] Consider V1+TTA - small improvements, acceptable")
    else:
        print("[RECOMMENDATION] Keep V1 baseline - TTA causes regressions")

    print()
    print("="*100)

    # Save results
    output_file = "v1_tta_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"[OK] Results saved to: {output_file}")
    print()

    return 0


def main():
    """Main entry point."""
    try:
        return test_v1_tta()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
