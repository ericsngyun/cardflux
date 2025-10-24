#!/usr/bin/env python3
"""
Test V3 Compressed Image Enhancements

Compares V1 baseline vs V2 vs V3 on compressed/low-quality images.

Focus: Discord screenshots and other compressed images
Expected: V3 should improve scores on compressed images by 10-15%

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
from production_card_identifier_v2 import ProductionCardIdentifierV2
from production_card_identifier_v3 import ProductionCardIdentifierV3


def test_v3_enhancements():
    """Test V3 enhancements vs V1 and V2."""
    print("="*100)
    print("V1 vs V2 vs V3 COMPRESSED IMAGE TEST")
    print("="*100)
    print()

    # Find test images
    test_images_dir = Path(__file__).parent.parent.parent / "test-images" / "one-piece"

    # Focus on compressed images
    compressed_images = [
        test_images_dir / "Screenshot_20251021_085328_Discord.jpg",
        test_images_dir / "Screenshot_20251021_085344_Discord.jpg",
        test_images_dir / "Screenshot_20251021_085357_Discord.jpg",
    ]

    # Also test on regular images to ensure no regression
    regular_images = [
        test_images_dir / "bege.png",
        test_images_dir / "blackbeard.png",
        test_images_dir / "yellow_event.png",
    ]

    all_images = compressed_images + regular_images

    if not all(img.exists() for img in all_images):
        print("[ERROR] Some test images not found")
        return 1

    print(f"Test Images: {len(all_images)}")
    print(f"  Compressed: {len(compressed_images)}")
    print(f"  Regular: {len(regular_images)}")
    print()

    # Initialize identifiers
    print("[INIT] Loading identifiers...")
    v1 = ProductionCardIdentifier(verbose=False)
    v2 = ProductionCardIdentifierV2(verbose=False)
    v3 = ProductionCardIdentifierV3(verbose=False)
    print("[OK] All versions loaded")
    print()

    results = []

    for idx, image_path in enumerate(all_images, 1):
        is_compressed = image_path in compressed_images
        category = "COMPRESSED" if is_compressed else "REGULAR"

        print(f"[{idx}/{len(all_images)}] [{category}] {image_path.name}")
        print("-" * 100)

        # Test V1
        try:
            start = time.time()
            v1_result = v1.identify(str(image_path), top_k=50, use_geometric=True)
            v1_time = (time.time() - start) * 1000

            v1_card = v1_result['best_match']['name']
            v1_number = v1_result['best_match']['number']
            v1_conf = v1_result['confidence']
            v1_score = v1_result['best_match']['final_score']
        except Exception as e:
            print(f"  [V1 ERROR] {e}")
            v1_card = "ERROR"
            v1_number = "N/A"
            v1_conf = "ERROR"
            v1_score = v1_time = 0

        # Test V2
        try:
            start = time.time()
            v2_result = v2.identify(str(image_path), top_k=50, use_geometric=True)
            v2_time = (time.time() - start) * 1000

            v2_card = v2_result['best_match']['name']
            v2_number = v2_result['best_match']['number']
            v2_conf = v2_result['confidence']
            v2_score = v2_result['best_match']['final_score']
        except Exception as e:
            print(f"  [V2 ERROR] {e}")
            v2_card = "ERROR"
            v2_number = "N/A"
            v2_conf = "ERROR"
            v2_score = v2_time = 0

        # Test V3
        try:
            start = time.time()
            # Enable verbose for V3 to see enhancements
            v3_verbose = ProductionCardIdentifierV3(verbose=True)
            v3_result = v3_verbose.identify(str(image_path), top_k=50, use_geometric=True)
            v3_time = (time.time() - start) * 1000

            v3_card = v3_result['best_match']['name']
            v3_number = v3_result['best_match']['number']
            v3_conf = v3_result['confidence']
            v3_score = v3_result['best_match']['final_score']
        except Exception as e:
            print(f"  [V3 ERROR] {e}")
            import traceback
            traceback.print_exc()
            v3_card = "ERROR"
            v3_number = "N/A"
            v3_conf = "ERROR"
            v3_score = v3_time = 0

        print()
        print(f"  V1: {v1_card[:40]:40s} | {v1_conf:8s} | {v1_score:.4f} | {v1_time:.0f}ms")
        print(f"  V2: {v2_card[:40]:40s} | {v2_conf:8s} | {v2_score:.4f} | {v2_time:.0f}ms")
        print(f"  V3: {v3_card[:40]:40s} | {v3_conf:8s} | {v3_score:.4f} | {v3_time:.0f}ms")

        # Calculate improvements
        v3_vs_v1_improvement = ((v3_score - v1_score) / v1_score * 100) if v1_score > 0 else 0
        v3_vs_v2_improvement = ((v3_score - v2_score) / v2_score * 100) if v2_score > 0 else 0

        if v3_vs_v1_improvement > 1:
            print(f"  [V3 IMPROVEMENT] +{v3_vs_v1_improvement:.1f}% vs V1")
        elif v3_vs_v1_improvement < -1:
            print(f"  [V3 REGRESSION] {v3_vs_v1_improvement:.1f}% vs V1")

        print()

        # Store result
        results.append({
            'image': image_path.name,
            'category': category,
            'v1': {'card': v1_card, 'number': v1_number, 'conf': v1_conf, 'score': v1_score, 'time': v1_time},
            'v2': {'card': v2_card, 'number': v2_number, 'conf': v2_conf, 'score': v2_score, 'time': v2_time},
            'v3': {'card': v3_card, 'number': v3_number, 'conf': v3_conf, 'score': v3_score, 'time': v3_time},
            'v3_vs_v1_improvement': v3_vs_v1_improvement,
            'v3_vs_v2_improvement': v3_vs_v2_improvement,
        })

    # Summary
    print("="*100)
    print("SUMMARY")
    print("="*100)
    print()

    # Table
    table_data = []
    for r in results:
        category_marker = "[C]" if r['category'] == "COMPRESSED" else "[R]"
        improvement = f"+{r['v3_vs_v1_improvement']:.1f}%" if r['v3_vs_v1_improvement'] > 0 else f"{r['v3_vs_v1_improvement']:.1f}%"

        table_data.append([
            f"{category_marker} {r['image'][:25]}",
            r['v1']['conf'],
            f"{r['v1']['score']:.3f}",
            r['v2']['conf'],
            f"{r['v2']['score']:.3f}",
            r['v3']['conf'],
            f"{r['v3']['score']:.3f}",
            improvement
        ])

    headers = ["Image", "V1 Conf", "V1 Score", "V2 Conf", "V2 Score", "V3 Conf", "V3 Score", "V3 vs V1"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print()

    # Statistics by category
    print("STATISTICS BY CATEGORY")
    print("-" * 100)

    for category in ["COMPRESSED", "REGULAR"]:
        category_results = [r for r in results if r['category'] == category]
        if not category_results:
            continue

        total = len(category_results)

        v1_avg_score = sum(r['v1']['score'] for r in category_results) / total
        v2_avg_score = sum(r['v2']['score'] for r in category_results) / total
        v3_avg_score = sum(r['v3']['score'] for r in category_results) / total

        v1_high = sum(1 for r in category_results if r['v1']['conf'] == 'HIGH')
        v2_high = sum(1 for r in category_results if r['v2']['conf'] == 'HIGH')
        v3_high = sum(1 for r in category_results if r['v3']['conf'] == 'HIGH')

        v1_avg_time = sum(r['v1']['time'] for r in category_results) / total
        v2_avg_time = sum(r['v2']['time'] for r in category_results) / total
        v3_avg_time = sum(r['v3']['time'] for r in category_results) / total

        avg_improvement = sum(r['v3_vs_v1_improvement'] for r in category_results) / total

        print(f"\n{category} Images ({total}):")
        print(f"  V1: {v1_avg_score:.4f} avg score, {v1_high}/{total} HIGH conf, {v1_avg_time:.0f}ms avg")
        print(f"  V2: {v2_avg_score:.4f} avg score, {v2_high}/{total} HIGH conf, {v2_avg_time:.0f}ms avg")
        print(f"  V3: {v3_avg_score:.4f} avg score, {v3_high}/{total} HIGH conf, {v3_avg_time:.0f}ms avg")
        print(f"  V3 Improvement: {avg_improvement:+.1f}% vs V1")

    # Overall verdict
    print()
    print("VERDICT")
    print("-" * 100)

    compressed_results = [r for r in results if r['category'] == "COMPRESSED"]
    regular_results = [r for r in results if r['category'] == "REGULAR"]

    compressed_improvement = sum(r['v3_vs_v1_improvement'] for r in compressed_results) / len(compressed_results) if compressed_results else 0
    regular_improvement = sum(r['v3_vs_v1_improvement'] for r in regular_results) / len(regular_results) if regular_results else 0

    if compressed_improvement > 5:
        print(f"[+] V3 significantly improves compressed images: +{compressed_improvement:.1f}%")
    elif compressed_improvement > 0:
        print(f"[~] V3 slightly improves compressed images: +{compressed_improvement:.1f}%")
    else:
        print(f"[-] V3 does not improve compressed images: {compressed_improvement:.1f}%")

    if regular_improvement < -2:
        print(f"[!] WARNING: V3 regresses on regular images: {regular_improvement:.1f}%")
    else:
        print(f"[OK] V3 does not regress on regular images: {regular_improvement:+.1f}%")

    print()

    if compressed_improvement > 5 and regular_improvement > -2:
        print("[RECOMMENDATION] Deploy V3 - improves compressed images without regression")
    elif compressed_improvement > 0 and regular_improvement > -5:
        print("[RECOMMENDATION] Consider V3 - small improvements, acceptable trade-offs")
    else:
        print("[RECOMMENDATION] Keep V2 - V3 does not provide sufficient benefit")

    print()
    print("="*100)

    # Save results
    output_file = "v3_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"[OK] Results saved to: {output_file}")
    print()

    return 0


def main():
    """Main entry point."""
    try:
        return test_v3_enhancements()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
