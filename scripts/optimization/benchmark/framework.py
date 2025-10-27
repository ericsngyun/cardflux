#!/usr/bin/env python3
"""
Benchmark Framework for TCG Card Identification System
Provides comprehensive testing, metrics, and comparison capabilities
"""
import sys
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "identification" / "core"))


@dataclass
class TestCase:
    """Represents a single test image with ground truth"""
    image_path: str
    ground_truth_card_id: Optional[str] = None
    ground_truth_name: Optional[str] = None
    ground_truth_number: Optional[str] = None
    tags: List[str] = None  # e.g., ["watermarked", "angled", "poor_lighting"]

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class IdentificationResult:
    """Results from a single identification"""
    test_case: TestCase
    predicted_card_id: str
    predicted_name: str
    predicted_number: str
    confidence: str
    final_score: float
    visual_score: float
    geometric_score: float
    time_ms: int
    rank: int  # What rank was the ground truth (1 = top-1 correct)
    top_k_matches: List[Dict]
    correct: bool

    def to_dict(self):
        d = asdict(self)
        d['test_case'] = asdict(self.test_case)
        return d


@dataclass
class BenchmarkMetrics:
    """Comprehensive metrics for a benchmark run"""
    # Accuracy metrics
    top_1_accuracy: float
    top_3_accuracy: float
    top_5_accuracy: float
    mean_reciprocal_rank: float

    # Performance metrics
    avg_time_ms: float
    min_time_ms: int
    max_time_ms: int
    median_time_ms: float
    throughput_per_sec: float

    # Confidence distribution
    high_confidence_rate: float
    moderate_confidence_rate: float
    low_confidence_rate: float

    # Score statistics
    avg_final_score: float
    avg_visual_score: float
    avg_geometric_score: float

    # Robustness metrics (by tag)
    accuracy_by_tag: Dict[str, float]
    avg_score_by_tag: Dict[str, float]

    # Error analysis
    false_positives: int
    false_negatives: int
    confusion_pairs: List[Tuple[str, str, int]]  # (predicted, actual, count)

    # Per-card analysis
    per_card_accuracy: Dict[str, float]
    problematic_cards: List[str]  # Cards with <80% accuracy

    def to_dict(self):
        return asdict(self)


class BenchmarkFramework:
    """
    Comprehensive benchmark framework for card identification system
    """

    def __init__(self, identifier, test_cases: List[TestCase], verbose: bool = True):
        """
        Args:
            identifier: ProductionCardIdentifier instance
            test_cases: List of test cases with ground truth
            verbose: Print progress messages
        """
        self.identifier = identifier
        self.test_cases = test_cases
        self.verbose = verbose

    def run_benchmark(self, top_k: int = 50, use_geometric: bool = True) -> Tuple[List[IdentificationResult], BenchmarkMetrics]:
        """
        Run complete benchmark on all test cases

        Returns:
            (results, metrics) tuple
        """
        if self.verbose:
            print("="*80)
            print("BENCHMARK FRAMEWORK - COMPREHENSIVE TESTING")
            print("="*80)
            print(f"\nTotal test cases: {len(self.test_cases)}")
            print(f"Top-K: {top_k}, Geometric: {use_geometric}")
            print()

        results = []
        start_time = time.time()

        for i, test_case in enumerate(self.test_cases, 1):
            if self.verbose:
                print(f"[{i}/{len(self.test_cases)}] Testing: {Path(test_case.image_path).name}")

            try:
                # Run identification
                raw_result = self.identifier.identify(
                    test_case.image_path,
                    top_k=top_k,
                    use_geometric=use_geometric,
                    tcg_hint="one-piece"
                )

                # Find rank of ground truth
                rank = None
                correct = False

                if test_case.ground_truth_number:
                    for idx, match in enumerate(raw_result['matches'], 1):
                        if match['number'] == test_case.ground_truth_number:
                            rank = idx
                            correct = (idx == 1)
                            break

                # Create result object
                result = IdentificationResult(
                    test_case=test_case,
                    predicted_card_id=raw_result['best_match']['card_id'],
                    predicted_name=raw_result['best_match']['name'],
                    predicted_number=raw_result['best_match']['number'],
                    confidence=raw_result['confidence'],
                    final_score=raw_result['scores']['final'],
                    visual_score=raw_result['scores']['visual'],
                    geometric_score=raw_result['scores']['geometric'],
                    time_ms=raw_result['time_ms'],
                    rank=rank if rank else 999,
                    top_k_matches=raw_result['matches'][:10],
                    correct=correct
                )

                results.append(result)

                if self.verbose:
                    status = "[OK] CORRECT" if correct else f"[X] WRONG (GT rank: {rank if rank else 'N/A'})"
                    print(f"  {status} - {result.predicted_name} (conf: {result.confidence}, score: {result.final_score:.4f})")

            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()

        total_time = time.time() - start_time

        # Calculate metrics
        metrics = self._calculate_metrics(results, total_time)

        if self.verbose:
            print("\n" + "="*80)
            self._print_metrics(metrics)

        return results, metrics

    def _calculate_metrics(self, results: List[IdentificationResult], total_time: float) -> BenchmarkMetrics:
        """Calculate comprehensive metrics from results"""

        # Filter results with ground truth
        results_with_gt = [r for r in results if r.test_case.ground_truth_number]

        if not results_with_gt:
            raise ValueError("No test cases with ground truth found!")

        # Accuracy metrics
        top_1_correct = sum(1 for r in results_with_gt if r.rank == 1)
        top_3_correct = sum(1 for r in results_with_gt if r.rank <= 3)
        top_5_correct = sum(1 for r in results_with_gt if r.rank <= 5)

        top_1_accuracy = top_1_correct / len(results_with_gt)
        top_3_accuracy = top_3_correct / len(results_with_gt)
        top_5_accuracy = top_5_correct / len(results_with_gt)

        # Mean reciprocal rank
        mrr = np.mean([1.0 / r.rank if r.rank < 999 else 0.0 for r in results_with_gt])

        # Performance metrics
        times = [r.time_ms for r in results]
        avg_time_ms = np.mean(times)
        min_time_ms = min(times)
        max_time_ms = max(times)
        median_time_ms = np.median(times)
        throughput = len(results) / total_time

        # Confidence distribution
        high_conf = sum(1 for r in results if r.confidence == 'HIGH')
        moderate_conf = sum(1 for r in results if r.confidence == 'MODERATE')
        low_conf = sum(1 for r in results if r.confidence == 'LOW')

        high_conf_rate = high_conf / len(results)
        moderate_conf_rate = moderate_conf / len(results)
        low_conf_rate = low_conf / len(results)

        # Score statistics
        avg_final_score = np.mean([r.final_score for r in results])
        avg_visual_score = np.mean([r.visual_score for r in results])
        avg_geometric_score = np.mean([r.geometric_score for r in results])

        # Robustness metrics by tag
        accuracy_by_tag = {}
        avg_score_by_tag = {}

        # Group by tag
        for tag in set(tag for r in results_with_gt for tag in r.test_case.tags):
            tag_results = [r for r in results_with_gt if tag in r.test_case.tags]
            if tag_results:
                tag_correct = sum(1 for r in tag_results if r.rank == 1)
                accuracy_by_tag[tag] = tag_correct / len(tag_results)
                avg_score_by_tag[tag] = np.mean([r.final_score for r in tag_results])

        # Error analysis
        false_positives = sum(1 for r in results_with_gt if not r.correct and r.confidence == 'HIGH')
        false_negatives = sum(1 for r in results_with_gt if not r.correct and r.rank > 5)

        # Confusion pairs
        confusion_counts = defaultdict(int)
        for r in results_with_gt:
            if not r.correct:
                pair = (r.predicted_number, r.test_case.ground_truth_number)
                confusion_counts[pair] += 1

        confusion_pairs = sorted(
            [(pred, gt, count) for (pred, gt), count in confusion_counts.items()],
            key=lambda x: x[2],
            reverse=True
        )[:10]

        # Per-card accuracy
        card_results = defaultdict(list)
        for r in results_with_gt:
            card_results[r.test_case.ground_truth_number].append(r.correct)

        per_card_accuracy = {
            card: sum(results) / len(results)
            for card, results in card_results.items()
        }

        problematic_cards = [
            card for card, acc in per_card_accuracy.items()
            if acc < 0.8
        ]

        return BenchmarkMetrics(
            top_1_accuracy=top_1_accuracy,
            top_3_accuracy=top_3_accuracy,
            top_5_accuracy=top_5_accuracy,
            mean_reciprocal_rank=mrr,
            avg_time_ms=avg_time_ms,
            min_time_ms=min_time_ms,
            max_time_ms=max_time_ms,
            median_time_ms=median_time_ms,
            throughput_per_sec=throughput,
            high_confidence_rate=high_conf_rate,
            moderate_confidence_rate=moderate_conf_rate,
            low_confidence_rate=low_conf_rate,
            avg_final_score=avg_final_score,
            avg_visual_score=avg_visual_score,
            avg_geometric_score=avg_geometric_score,
            accuracy_by_tag=accuracy_by_tag,
            avg_score_by_tag=avg_score_by_tag,
            false_positives=false_positives,
            false_negatives=false_negatives,
            confusion_pairs=confusion_pairs,
            per_card_accuracy=per_card_accuracy,
            problematic_cards=problematic_cards
        )

    def _print_metrics(self, metrics: BenchmarkMetrics):
        """Pretty print metrics"""
        print("BENCHMARK RESULTS")
        print("="*80)

        print("\n[ACCURACY METRICS]")
        print(f"  Top-1 Accuracy:  {metrics.top_1_accuracy*100:.2f}%")
        print(f"  Top-3 Accuracy:  {metrics.top_3_accuracy*100:.2f}%")
        print(f"  Top-5 Accuracy:  {metrics.top_5_accuracy*100:.2f}%")
        print(f"  Mean Reciprocal Rank: {metrics.mean_reciprocal_rank:.4f}")

        print("\n[PERFORMANCE METRICS]")
        print(f"  Avg Time:     {metrics.avg_time_ms:.0f}ms")
        print(f"  Min Time:     {metrics.min_time_ms}ms")
        print(f"  Max Time:     {metrics.max_time_ms}ms")
        print(f"  Median Time:  {metrics.median_time_ms:.0f}ms")
        print(f"  Throughput:   {metrics.throughput_per_sec:.2f} cards/sec")

        print("\n[CONFIDENCE DISTRIBUTION]")
        print(f"  HIGH:     {metrics.high_confidence_rate*100:.1f}%")
        print(f"  MODERATE: {metrics.moderate_confidence_rate*100:.1f}%")
        print(f"  LOW:      {metrics.low_confidence_rate*100:.1f}%")

        print("\n[SCORE STATISTICS]")
        print(f"  Avg Final Score:     {metrics.avg_final_score:.4f}")
        print(f"  Avg Visual Score:    {metrics.avg_visual_score:.4f}")
        print(f"  Avg Geometric Score: {metrics.avg_geometric_score:.4f}")

        if metrics.accuracy_by_tag:
            print("\n[ROBUSTNESS BY TAG]")
            for tag, acc in sorted(metrics.accuracy_by_tag.items(), key=lambda x: x[1]):
                avg_score = metrics.avg_score_by_tag.get(tag, 0)
                print(f"  {tag:20s}: {acc*100:.1f}% accuracy (avg score: {avg_score:.4f})")

        print("\n[ERROR ANALYSIS]")
        print(f"  False Positives (HIGH conf but wrong): {metrics.false_positives}")
        print(f"  False Negatives (GT not in top-5):     {metrics.false_negatives}")

        if metrics.confusion_pairs:
            print("\n  Top Confusion Pairs:")
            for pred, gt, count in metrics.confusion_pairs[:5]:
                print(f"    Predicted {pred} instead of {gt}: {count} times")

        if metrics.problematic_cards:
            print(f"\n  Problematic Cards (<80% accuracy): {len(metrics.problematic_cards)}")
            for card in metrics.problematic_cards[:5]:
                acc = metrics.per_card_accuracy[card]
                print(f"    {card}: {acc*100:.1f}%")

        print("\n" + "="*80)

    def compare_configurations(self, config_a_results: List[IdentificationResult],
                              config_b_results: List[IdentificationResult],
                              config_a_name: str = "Config A",
                              config_b_name: str = "Config B") -> Dict:
        """
        Statistically compare two configurations

        Returns:
            Comparison report with significance tests
        """
        from scipy import stats

        # Extract metrics for comparison
        a_scores = [r.final_score for r in config_a_results]
        b_scores = [r.final_score for r in config_b_results]

        a_times = [r.time_ms for r in config_a_results]
        b_times = [r.time_ms for r in config_b_results]

        a_correct = [r.correct for r in config_a_results if r.test_case.ground_truth_number]
        b_correct = [r.correct for r in config_b_results if r.test_case.ground_truth_number]

        # Statistical tests
        score_ttest = stats.ttest_ind(a_scores, b_scores)
        time_ttest = stats.ttest_ind(a_times, b_times)

        # Accuracy comparison
        a_accuracy = sum(a_correct) / len(a_correct) if a_correct else 0
        b_accuracy = sum(b_correct) / len(b_correct) if b_correct else 0

        comparison = {
            'config_a_name': config_a_name,
            'config_b_name': config_b_name,
            'accuracy': {
                'config_a': a_accuracy,
                'config_b': b_accuracy,
                'improvement': b_accuracy - a_accuracy,
                'improvement_pct': ((b_accuracy - a_accuracy) / a_accuracy * 100) if a_accuracy > 0 else 0
            },
            'score': {
                'config_a_mean': np.mean(a_scores),
                'config_b_mean': np.mean(b_scores),
                'improvement': np.mean(b_scores) - np.mean(a_scores),
                'p_value': score_ttest.pvalue,
                'significant': score_ttest.pvalue < 0.05
            },
            'speed': {
                'config_a_mean_ms': np.mean(a_times),
                'config_b_mean_ms': np.mean(b_times),
                'speedup': (np.mean(a_times) - np.mean(b_times)) / np.mean(a_times),
                'p_value': time_ttest.pvalue,
                'significant': time_ttest.pvalue < 0.05
            }
        }

        if self.verbose:
            print("\n" + "="*80)
            print("CONFIGURATION COMPARISON")
            print("="*80)
            print(f"\n{config_a_name} vs {config_b_name}")
            print(f"\n📊 ACCURACY")
            print(f"  {config_a_name}: {comparison['accuracy']['config_a']*100:.2f}%")
            print(f"  {config_b_name}: {comparison['accuracy']['config_b']*100:.2f}%")
            print(f"  Improvement: {comparison['accuracy']['improvement_pct']:.2f}%")

            print(f"\n📈 SCORE")
            print(f"  {config_a_name}: {comparison['score']['config_a_mean']:.4f}")
            print(f"  {config_b_name}: {comparison['score']['config_b_mean']:.4f}")
            print(f"  Improvement: {comparison['score']['improvement']:.4f}")
            print(f"  Significant: {comparison['score']['significant']} (p={comparison['score']['p_value']:.4f})")

            print(f"\n⚡ SPEED")
            print(f"  {config_a_name}: {comparison['speed']['config_a_mean_ms']:.0f}ms")
            print(f"  {config_b_name}: {comparison['speed']['config_b_mean_ms']:.0f}ms")
            print(f"  Speedup: {comparison['speed']['speedup']*100:.1f}%")
            print(f"  Significant: {comparison['speed']['significant']} (p={comparison['speed']['p_value']:.4f})")

        return comparison

    def save_results(self, results: List[IdentificationResult], metrics: BenchmarkMetrics,
                    output_path: str):
        """Save results and metrics to JSON"""
        output = {
            'results': [r.to_dict() for r in results],
            'metrics': metrics.to_dict(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'num_test_cases': len(results)
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        if self.verbose:
            print(f"\n[OK] Results saved to: {output_path}")


def load_test_cases_from_directory(test_dir: str, ground_truth_file: Optional[str] = None) -> List[TestCase]:
    """
    Load test cases from a directory

    Args:
        test_dir: Directory containing test images
        ground_truth_file: Optional JSON file with ground truth labels
            Format: {"image_name": {"card_number": "XX-YYY", "name": "...", "tags": [...]}}

    Returns:
        List of TestCase objects
    """
    test_path = Path(test_dir)

    # Load ground truth if provided
    ground_truth = {}
    if ground_truth_file and Path(ground_truth_file).exists():
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)

    # Find all images
    image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
    test_images = []

    for ext in image_extensions:
        test_images.extend(test_path.glob(f"*{ext}"))

    test_images = sorted(test_images)

    # Create test cases
    test_cases = []
    for img_path in test_images:
        img_name = img_path.name
        gt = ground_truth.get(img_name, {})

        test_case = TestCase(
            image_path=str(img_path),
            ground_truth_card_id=gt.get('card_id'),
            ground_truth_name=gt.get('name'),
            ground_truth_number=gt.get('card_number'),
            tags=gt.get('tags', [])
        )

        test_cases.append(test_case)

    return test_cases


if __name__ == "__main__":
    # Example usage
    print("Benchmark Framework Module")
    print("Import this module to use in optimization experiments")
