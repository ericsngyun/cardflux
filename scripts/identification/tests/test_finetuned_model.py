#!/usr/bin/env python3
"""
Test Fine-Tuned DINOv2 vs V1 Baseline

Compares accuracy of fine-tuned model against V1 baseline on test images.

Success Criteria:
- Fine-tuned improves average score by +10-20%
- Fine-tuned increases HIGH confidence count
- No regressions on previously HIGH confidence images

Author: Senior Principal Engineer
Date: 2025-10-21
"""
import sys
import json
import time
import torch
from pathlib import Path
from tabulate import tabulate

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from production_card_identifier import ProductionCardIdentifier


class FineTunedCardIdentifier(ProductionCardIdentifier):
    """
    Production identifier using fine-tuned DINOv2 model.
    """

    def __init__(self, finetuned_model_path: str, game: str = 'one-piece', verbose: bool = True):
        """Initialize with fine-tuned model."""
        self.finetuned_model_path = finetuned_model_path
        super().__init__(game=game, verbose=verbose, enable_variant_classifier=True)

    def _load_model(self):
        """Load fine-tuned DINOv2 model instead of pretrained."""
        from transformers import AutoModel
        import torch

        if self.verbose:
            print(f"  Loading FINE-TUNED DINOv2 from: {self.finetuned_model_path}")

        # Load base model architecture
        base_model_name = 'facebook/dinov2-small'
        self.model = AutoModel.from_pretrained(base_model_name)

        # Load fine-tuned weights
        checkpoint = torch.load(self.finetuned_model_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])

        self.model = self.model.to(self.device)
        self.model.eval()

        if self.verbose:
            epoch = checkpoint.get('epoch', 'unknown')
            val_loss = checkpoint.get('val_loss', 'unknown')
            print(f"  Fine-tuned model loaded (epoch {epoch}, val_loss {val_loss})")


def test_finetuned_vs_baseline():
    """Test fine-tuned model vs V1 baseline."""
    print("="*100)
    print("FINE-TUNED DINOV2 vs V1 BASELINE")
    print("="*100)
    print()

    # Find fine-tuned model
    finetuned_path = Path("artifacts/finetuned-models/dinov2-onepiece-best.pt")

    if not finetuned_path.exists():
        print(f"[ERROR] Fine-tuned model not found: {finetuned_path}")
        print("Run finetune_dinov2.py first to train the model.")
        return 1

    # Find test images
    test_images_dir = Path(__file__).parent.parent.parent / "test-images" / "one-piece"
    test_images = sorted(list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpg")))

    if not test_images:
        print(f"[ERROR] No test images found in {test_images_dir}")
        return 1

    print(f"Test Images: {len(test_images)}")
    print(f"Fine-tuned Model: {finetuned_path}")
    print()

    # Initialize identifiers
    print("[INIT] Loading identifiers...")
    v1_baseline = ProductionCardIdentifier(verbose=False)
    finetuned = FineTunedCardIdentifier(str(finetuned_path), verbose=False)
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

        # Test Fine-Tuned
        print("  [FINE-TUNED] ", end=" ")
        try:
            start = time.time()
            ft_result = finetuned.identify(str(image_path), top_k=50, use_geometric=True)
            ft_time = (time.time() - start) * 1000

            ft_card = ft_result['best_match']['name']
            ft_number = ft_result['best_match']['number']
            ft_conf = ft_result['confidence']
            ft_score = ft_result['best_match']['final_score']

            print(f"{ft_card[:40]:40s} | {ft_conf:8s} | {ft_score:.4f} | {ft_time:.0f}ms")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            ft_card = "ERROR"
            ft_number = "N/A"
            ft_conf = "ERROR"
            ft_score = ft_time = 0

        # Analysis
        same_card = (v1_number == ft_number and v1_number != "N/A")
        score_change = ft_score - v1_score
        score_change_pct = (score_change / v1_score * 100) if v1_score > 0 else 0

        conf_improved = (
            (v1_conf == 'LOW' and ft_conf in ['MODERATE', 'HIGH']) or
            (v1_conf == 'MODERATE' and ft_conf == 'HIGH')
        )
        conf_regressed = (
            (v1_conf == 'HIGH' and ft_conf in ['MODERATE', 'LOW']) or
            (v1_conf == 'MODERATE' and ft_conf == 'LOW')
        )

        print()
        if not same_card:
            print(f"  [WARNING] Different cards: V1={v1_number} vs FT={ft_number}")
        if conf_improved:
            print(f"  [IMPROVEMENT] Confidence: {v1_conf} -> {ft_conf}")
        if conf_regressed:
            print(f"  [REGRESSION] Confidence: {v1_conf} -> {ft_conf} [WARNING]")
        if score_change > 0.01:
            print(f"  [BOOST] Score: +{score_change:.4f} ({score_change_pct:+.1f}%)")
        elif score_change < -0.01:
            print(f"  [REDUCTION] Score: {score_change:.4f} ({score_change_pct:.1f}%) [WARNING]")

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
            'finetuned': {
                'card': ft_card,
                'number': ft_number,
                'conf': ft_conf,
                'score': ft_score,
                'time': ft_time
            },
            'same_card': same_card,
            'score_change': score_change,
            'score_change_pct': score_change_pct,
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
        pct_str = f"({r['score_change_pct']:+.1f}%)"
        match_str = "[OK]" if r['same_card'] else "[DIFF]"

        if r['conf_improved']:
            conf_str = f"{r['v1']['conf']} -> {r['finetuned']['conf']} [UP]"
        elif r['conf_regressed']:
            conf_str = f"{r['v1']['conf']} -> {r['finetuned']['conf']} [DOWN]"
        else:
            conf_str = r['v1']['conf']

        table_data.append([
            r['image'][:30],
            r['v1']['conf'],
            f"{r['v1']['score']:.3f}",
            r['finetuned']['conf'],
            f"{r['finetuned']['score']:.3f}",
            f"{change_str} {pct_str}",
            conf_str,
            match_str
        ])

    headers = ["Image", "V1 Conf", "V1 Score", "FT Conf", "FT Score", "Change", "Confidence", "Match"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print()

    # Statistics
    total = len(results)
    same_cards = sum(1 for r in results if r['same_card'])
    conf_improvements = sum(1 for r in results if r['conf_improved'])
    conf_regressions = sum(1 for r in results if r['conf_regressed'])

    v1_avg_score = sum(r['v1']['score'] for r in results) / total
    ft_avg_score = sum(r['finetuned']['score'] for r in results) / total
    avg_score_change = ft_avg_score - v1_avg_score
    avg_score_change_pct = (avg_score_change / v1_avg_score * 100) if v1_avg_score > 0 else 0

    v1_high = sum(1 for r in results if r['v1']['conf'] == 'HIGH')
    ft_high = sum(1 for r in results if r['finetuned']['conf'] == 'HIGH')

    v1_avg_time = sum(r['v1']['time'] for r in results) / total
    ft_avg_time = sum(r['finetuned']['time'] for r in results) / total

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
    print("Fine-Tuned:")
    print(f"  Avg Score: {ft_avg_score:.4f} ({avg_score_change:+.4f}, {avg_score_change_pct:+.1f}%)")
    print(f"  HIGH Confidence: {ft_high}/{total} ({ft_high/total*100:.1f}%)")
    print(f"  Avg Time: {ft_avg_time:.0f}ms ({ft_avg_time-v1_avg_time:+.0f}ms)")
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

    if avg_score_change_pct > 10:  # >10% improvement
        print(f"[+] Fine-tuned significantly improves scores: +{avg_score_change:.4f} ({avg_score_change_pct:+.1f}%)")
        reasons.append("significant_score_improvement")
    elif avg_score_change_pct > 5:  # >5% improvement
        print(f"[+] Fine-tuned improves scores: +{avg_score_change:.4f} ({avg_score_change_pct:+.1f}%)")
        reasons.append("score_improvement")
    elif avg_score_change_pct > 0:
        print(f"[~] Fine-tuned slightly improves scores: +{avg_score_change:.4f} ({avg_score_change_pct:+.1f}%)")
    else:
        print(f"[-] Fine-tuned reduces scores: {avg_score_change:.4f} ({avg_score_change_pct:.1f}%)")
        success = False

    if conf_improvements > 0:
        print(f"[+] Fine-tuned improved confidence on {conf_improvements} image(s)")
        reasons.append("confidence_improvement")

    if conf_regressions > 0:
        print(f"[!] WARNING: Fine-tuned regressed confidence on {conf_regressions} image(s)")
        success = False

    if ft_high > v1_high:
        print(f"[+] Fine-tuned increased HIGH confidence count: {v1_high} -> {ft_high}")
        reasons.append("more_high_confidence")
    elif ft_high < v1_high:
        print(f"[-] Fine-tuned decreased HIGH confidence count: {v1_high} -> {ft_high}")
        success = False

    print()
    if success and avg_score_change_pct > 10:
        print("[RECOMMENDATION] Deploy fine-tuned model - significant improvements!")
    elif success and len(reasons) >= 2:
        print("[RECOMMENDATION] Deploy fine-tuned model - multiple improvements confirmed")
    elif success:
        print("[RECOMMENDATION] Consider fine-tuned model - modest improvements")
    else:
        print("[RECOMMENDATION] Keep V1 baseline - fine-tuning did not improve or caused regressions")

    print()
    print("="*100)

    # Save results
    output_file = "finetuned_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"[OK] Results saved to: {output_file}")
    print()

    return 0


def main():
    """Main entry point."""
    try:
        return test_finetuned_vs_baseline()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
