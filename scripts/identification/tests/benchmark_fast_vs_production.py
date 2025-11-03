#!/usr/bin/env python3
"""
Comprehensive Benchmark: Fast vs Production Identifier

Tests both identifiers on all test images and compares:
- Speed (average, p50, p95, p99)
- Accuracy (top-1, top-3, confidence match)
- Consistency (score differences)

Usage:
    python benchmark_fast_vs_production.py

Output:
    - Detailed comparison report
    - Speed analysis
    - Accuracy validation
    - Recommendation for demo
"""
import sys
import time
import json
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.production_card_identifier import ProductionCardIdentifier
from core.fast_card_identifier import FastCardIdentifier


@dataclass
class BenchmarkResult:
    """Result from a single identification."""
    image_name: str
    card_name: str
    confidence: str
    final_score: float
    visual_score: float
    geometric_score: float
    time_ms: float
    top_3_names: List[str]


def benchmark_identifier(identifier, image_paths: List[Path], name: str) -> List[BenchmarkResult]:
    """Run benchmark on an identifier."""
    print(f"\n{'='*70}")
    print(f"BENCHMARKING: {name}")
    print(f"{'='*70}")

    results = []
    times = []

    for i, image_path in enumerate(image_paths, 1):
        print(f"\n[{i}/{len(image_paths)}] {image_path.name}...", end=" ", flush=True)

        try:
            start = time.time()
            result = identifier.identify(str(image_path), top_k=20, use_geometric=True)
            elapsed_ms = (time.time() - start) * 1000

            best_match = result['best_match']

            benchmark_result = BenchmarkResult(
                image_name=image_path.name,
                card_name=best_match['name'],
                confidence=result['confidence'],
                final_score=result['scores']['final'],
                visual_score=result['scores']['visual'],
                geometric_score=result['scores']['geometric'],
                time_ms=elapsed_ms,
                top_3_names=[m['name'] for m in result['matches'][:3]]
            )

            results.append(benchmark_result)
            times.append(elapsed_ms)

            print(f"{elapsed_ms:.0f}ms - {result['confidence']}")

        except Exception as e:
            print(f"ERROR: {e}")
            continue

    # Print summary
    print(f"\n{'='*70}")
    print(f"SUMMARY: {name}")
    print(f"{'='*70}")
    print(f"Images processed: {len(results)}")
    print(f"Average time: {statistics.mean(times):.0f}ms")
    print(f"Median time: {statistics.median(times):.0f}ms")
    print(f"P95 time: {sorted(times)[int(len(times)*0.95)]:.0f}ms" if len(times) > 1 else f"P95 time: N/A")
    print(f"Min time: {min(times):.0f}ms")
    print(f"Max time: {max(times):.0f}ms")

    confidence_counts = {}
    for r in results:
        confidence_counts[r.confidence] = confidence_counts.get(r.confidence, 0) + 1

    for conf, count in sorted(confidence_counts.items()):
        print(f"{conf}: {count}/{len(results)} ({count/len(results)*100:.0f}%)")

    return results


def compare_results(prod_results: List[BenchmarkResult], fast_results: List[BenchmarkResult]):
    """Compare production vs fast results."""
    print(f"\n{'='*70}")
    print(f"COMPARISON: PRODUCTION vs FAST")
    print(f"{'='*70}")

    # Speed comparison
    prod_times = [r.time_ms for r in prod_results]
    fast_times = [r.time_ms for r in fast_results]

    prod_avg = statistics.mean(prod_times)
    fast_avg = statistics.mean(fast_times)
    speedup = (prod_avg - fast_avg) / prod_avg * 100

    print(f"\n[SPEED ANALYSIS]")
    print(f"{'='*70}")
    print(f"Production Average: {prod_avg:.0f}ms")
    print(f"Fast Average:       {fast_avg:.0f}ms")
    print(f"Speedup:            {speedup:+.1f}% {'+OK' if speedup > 0 else 'FAIL'}")
    print(f"Time saved per card: {prod_avg - fast_avg:.0f}ms")

    # Detailed speed breakdown
    print(f"\nDetailed Timing:")
    print(f"{'Metric':<20} {'Production':<15} {'Fast':<15} {'Delta':<10}")
    print(f"{'-'*60}")
    print(f"{'Average':<20} {prod_avg:>10.0f}ms    {fast_avg:>10.0f}ms    {prod_avg-fast_avg:>+7.0f}ms")
    print(f"{'Median':<20} {statistics.median(prod_times):>10.0f}ms    {statistics.median(fast_times):>10.0f}ms    {statistics.median(prod_times)-statistics.median(fast_times):>+7.0f}ms")
    print(f"{'Min':<20} {min(prod_times):>10.0f}ms    {min(fast_times):>10.0f}ms    {min(prod_times)-min(fast_times):>+7.0f}ms")
    print(f"{'Max':<20} {max(prod_times):>10.0f}ms    {max(fast_times):>10.0f}ms    {max(prod_times)-max(fast_times):>+7.0f}ms")

    # Accuracy comparison
    print(f"\n[ACCURACY ANALYSIS]")
    print(f"{'='*70}")

    # Top-1 match rate
    top1_matches = sum(1 for p, f in zip(prod_results, fast_results)
                      if p.card_name == f.card_name)
    top1_rate = top1_matches / len(prod_results) * 100

    # Confidence match rate
    confidence_matches = sum(1 for p, f in zip(prod_results, fast_results)
                            if p.confidence == f.confidence)
    confidence_rate = confidence_matches / len(prod_results) * 100

    # Score differences
    score_diffs = [abs(p.final_score - f.final_score)
                   for p, f in zip(prod_results, fast_results)]
    avg_score_diff = statistics.mean(score_diffs)
    max_score_diff = max(score_diffs)

    print(f"Top-1 Match Rate:   {top1_matches}/{len(prod_results)} ({top1_rate:.1f}%) {'PASS' if top1_rate >= 95 else 'WARN'}")
    print(f"Confidence Match:   {confidence_matches}/{len(prod_results)} ({confidence_rate:.1f}%) {'PASS' if confidence_rate >= 90 else 'WARN'}")
    print(f"Avg Score Diff:     {avg_score_diff:.4f} {'PASS' if avg_score_diff < 0.05 else 'WARN'}")
    print(f"Max Score Diff:     {max_score_diff:.4f} {'PASS' if max_score_diff < 0.10 else 'WARN'}")

    # Detailed per-image comparison
    print(f"\n[PER-IMAGE COMPARISON]")
    print(f"{'='*70}")
    print(f"{'Image':<25} {'Match?':<8} {'Conf Match?':<12} {'Time Delta':<12} {'Score Delta':<12}")
    print(f"{'-'*70}")

    for p, f in zip(prod_results, fast_results):
        match_icon = "MATCH" if p.card_name == f.card_name else "DIFF"
        conf_match_icon = "SAME" if p.confidence == f.confidence else "DIFF"
        time_diff = f.time_ms - p.time_ms
        score_diff = f.final_score - p.final_score

        print(f"{p.image_name:<25} {match_icon:<8} {conf_match_icon:<12} {time_diff:>+10.0f}ms {score_diff:>+11.4f}")

    # Divergences (where results differ)
    divergences = [(p, f) for p, f in zip(prod_results, fast_results)
                   if p.card_name != f.card_name]

    if divergences:
        print(f"\n[WARNING] DIVERGENCES ({len(divergences)} found)")
        print(f"{'='*70}")
        for p, f in divergences:
            print(f"\n{p.image_name}:")
            print(f"  Production: {p.card_name} ({p.confidence}, {p.final_score:.4f})")
            print(f"  Fast:       {f.card_name} ({f.confidence}, {f.final_score:.4f})")
            print(f"  Difference: Score Delta {f.final_score - p.final_score:+.4f}")
    else:
        print(f"\n[SUCCESS] NO DIVERGENCES - Perfect top-1 accuracy match!")

    # Final verdict
    print(f"\n{'='*70}")
    print(f"FINAL VERDICT")
    print(f"{'='*70}")

    # Criteria for acceptance
    speed_ok = speedup > 20  # At least 20% faster
    accuracy_ok = top1_rate >= 95  # At least 95% top-1 match
    consistency_ok = avg_score_diff < 0.05  # Scores within 0.05

    if speed_ok and accuracy_ok and consistency_ok:
        print(f"[APPROVED] FAST IDENTIFIER READY FOR DEMO")
        print(f"\nReasons:")
        print(f"  - {speedup:.0f}% faster (target: 20%+)")
        print(f"  - {top1_rate:.0f}% top-1 accuracy (target: 95%+)")
        print(f"  - {avg_score_diff:.4f} avg score diff (target: <0.05)")
        print(f"\nRecommendation: Use FAST identifier for demo")
    elif speed_ok and not accuracy_ok:
        print(f"[WARNING] FAST IDENTIFIER NEEDS REVIEW")
        print(f"\nReasons:")
        print(f"  - Speed: {speedup:.0f}% faster [PASS]")
        print(f"  - Accuracy: {top1_rate:.0f}% (below 95% target) [FAIL]")
        print(f"\nRecommendation: Fix accuracy issues before demo")
    elif not speed_ok:
        print(f"[FAIL] FAST IDENTIFIER NOT FASTER")
        print(f"\nReasons:")
        print(f"  - Speed: {speedup:.0f}% (below 20% target) [FAIL]")
        print(f"\nRecommendation: Use PRODUCTION identifier for demo")
    else:
        print(f"[WARNING] MIXED RESULTS")
        print(f"\nRecommendation: Review results before deciding")

    return {
        'speedup_pct': speedup,
        'top1_rate': top1_rate,
        'confidence_rate': confidence_rate,
        'avg_score_diff': avg_score_diff,
        'max_score_diff': max_score_diff,
        'divergences': len(divergences)
    }


def main():
    """Run comprehensive benchmark."""
    print("="*70)
    print("COMPREHENSIVE BENCHMARK: FAST vs PRODUCTION")
    print("="*70)

    # Find test images
    test_images_dir = Path(__file__).parent.parent.parent.parent / "test-images" / "one-piece"

    if not test_images_dir.exists():
        print(f"ERROR: Test images directory not found: {test_images_dir}")
        return

    image_paths = sorted(test_images_dir.glob("*.png")) + sorted(test_images_dir.glob("*.jpg"))

    if not image_paths:
        print(f"ERROR: No test images found in {test_images_dir}")
        return

    print(f"\nTest images: {len(image_paths)}")
    for img in image_paths:
        print(f"  • {img.name}")

    # Initialize identifiers
    print(f"\nInitializing identifiers...")

    print(f"\n[1/2] Production Identifier...")
    prod_identifier = ProductionCardIdentifier(verbose=False)

    print(f"\n[2/2] Fast Identifier...")
    fast_identifier = FastCardIdentifier(verbose=False, use_gpu=True)

    # Run benchmarks
    prod_results = benchmark_identifier(prod_identifier, image_paths, "PRODUCTION")
    fast_results = benchmark_identifier(fast_identifier, image_paths, "FAST")

    # Compare results
    comparison = compare_results(prod_results, fast_results)

    # Save results to JSON
    output_file = Path(__file__).parent / "benchmark_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'production': [
                {
                    'image': r.image_name,
                    'card': r.card_name,
                    'confidence': r.confidence,
                    'score': r.final_score,
                    'time_ms': r.time_ms
                }
                for r in prod_results
            ],
            'fast': [
                {
                    'image': r.image_name,
                    'card': r.card_name,
                    'confidence': r.confidence,
                    'score': r.final_score,
                    'time_ms': r.time_ms
                }
                for r in fast_results
            ],
            'comparison': comparison
        }, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
