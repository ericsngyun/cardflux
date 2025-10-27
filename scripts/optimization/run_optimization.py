#!/usr/bin/env python3
"""
Main Optimization Orchestrator
Coordinates the entire optimization workflow
"""
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "identification" / "core"))
sys.path.insert(0, str(Path(__file__).parent))

from benchmark.framework import BenchmarkFramework, load_test_cases_from_directory
from config.system import ConfigurationManager
from experiments.tracker import ExperimentTracker, ExperimentRun, get_git_commit, get_hardware_info
from analysis.reporter import AnalysisReporter
from config.configurable_identifier import ConfigurableIdentifier


class OptimizationOrchestrator:
    """
    Main orchestrator for the optimization process
    """

    def __init__(self, test_dir: str, ground_truth_file: str,
                verbose: bool = True):
        """
        Args:
            test_dir: Directory with test images
            ground_truth_file: Path to ground truth JSON
            verbose: Print progress
        """
        self.test_dir = test_dir
        self.ground_truth_file = ground_truth_file
        self.verbose = verbose

        # Initialize components
        self.config_manager = ConfigurationManager()
        self.tracker = ExperimentTracker()
        self.reporter = AnalysisReporter()

        # Load test cases
        self.test_cases = load_test_cases_from_directory(
            test_dir, ground_truth_file
        )

        if self.verbose:
            print("="*80)
            print("OPTIMIZATION ORCHESTRATOR INITIALIZED")
            print("="*80)
            print(f"Test directory: {test_dir}")
            print(f"Ground truth file: {ground_truth_file}")
            print(f"Number of test cases: {len(self.test_cases)}")
            print(f"Test cases with ground truth: {sum(1 for tc in self.test_cases if tc.ground_truth_number)}")
            print("="*80)
            print()

    def establish_baseline(self) -> str:
        """
        Establish baseline performance with current configuration

        Returns:
            baseline_run_id
        """
        if self.verbose:
            print("="*80)
            print("ESTABLISHING BASELINE")
            print("="*80)

        # Create baseline config
        baseline_config = self.config_manager.create_baseline_config()

        if self.verbose:
            print(f"\nBaseline config created: {baseline_config.config_id}")
            print("\nRunning baseline benchmark...")

        # Run benchmark
        run_id = self.run_single_experiment(
            config=baseline_config,
            notes="Baseline configuration - current production system",
            tags=["baseline"]
        )

        if self.verbose:
            print(f"\n[SUCCESS] Baseline established: {run_id}")
            print("="*80)

        return run_id

    def run_single_experiment(self, config, notes: str = "",
                             tags: List[str] = None) -> str:
        """
        Run a single experiment with given configuration

        Args:
            config: Configuration object
            notes: Notes about this experiment
            tags: Tags for categorization

        Returns:
            run_id
        """
        if tags is None:
            tags = []

        if self.verbose:
            print(f"\n{'='*80}")
            print(f"RUNNING EXPERIMENT: {config.name}")
            print(f"{'='*80}")
            print(f"Config ID: {config.config_id}")
            if notes:
                print(f"Notes: {notes}")
            print()

        # Initialize identifier with configuration
        identifier = ConfigurableIdentifier(
            config=config.to_dict(),
            game="one-piece",
            verbose=False
        )

        # Run benchmark
        benchmark = BenchmarkFramework(
            identifier=identifier,
            test_cases=self.test_cases,
            verbose=self.verbose
        )

        start_time = time.time()
        results, metrics = benchmark.run_benchmark(
            top_k=config.get_param_value('faiss_top_k'),
            use_geometric=config.get_param_value('orb_enabled')
        )
        total_time = time.time() - start_time

        # Create experiment run
        run_id = f"run_{int(time.time())}_{config.config_id}"

        experiment_run = ExperimentRun(
            run_id=run_id,
            config_id=config.config_id,
            config_name=config.name,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            git_commit=get_git_commit(),
            hardware_info=get_hardware_info(),
            top_1_accuracy=metrics.top_1_accuracy,
            top_3_accuracy=metrics.top_3_accuracy,
            top_5_accuracy=metrics.top_5_accuracy,
            mean_reciprocal_rank=metrics.mean_reciprocal_rank,
            avg_time_ms=metrics.avg_time_ms,
            high_confidence_rate=metrics.high_confidence_rate,
            avg_final_score=metrics.avg_final_score,
            num_test_cases=len(self.test_cases),
            test_dataset=self.test_dir,
            notes=notes,
            tags=tags
        )

        # Prepare result details for provenance
        result_details = []
        for result in results:
            result_details.append({
                'image_name': Path(result.test_case.image_path).name,
                'ground_truth': result.test_case.ground_truth_number,
                'predicted': result.predicted_number,
                'correct': result.correct,
                'confidence': result.confidence,
                'final_score': result.final_score,
                'time_ms': result.time_ms
            })

        # Log to tracker
        self.tracker.log_experiment(
            run=experiment_run,
            config_data=config.to_dict(),
            result_details=result_details
        )

        if self.verbose:
            print(f"\n[SUCCESS] Experiment completed: {run_id}")
            print(f"   Top-1 Accuracy: {metrics.top_1_accuracy*100:.2f}%")
            print(f"   Avg Time: {metrics.avg_time_ms:.0f}ms")
            print(f"   HIGH Confidence: {metrics.high_confidence_rate*100:.1f}%")
            print(f"{'='*80}\n")

        return run_id

    def run_parameter_sweep(self, base_config_id: str,
                          param_ranges: Dict[str, List],
                          max_configs: int = 20) -> List[str]:
        """
        Run parameter sweep experiments

        Args:
            base_config_id: Base configuration to start from
            param_ranges: Dict of {param_name: [value1, value2, ...]}
            max_configs: Maximum number of configs to test

        Returns:
            List of run_ids
        """
        if self.verbose:
            print("="*80)
            print("PARAMETER SWEEP")
            print("="*80)
            print(f"Base config: {base_config_id}")
            print(f"Parameters: {list(param_ranges.keys())}")
            print(f"Max configs: {max_configs}")
            print()

        # Load base config
        base_config = self.config_manager.load_config(base_config_id)

        # Generate sweep configs
        configs = self.config_manager.generate_parameter_sweep(
            base_config=base_config,
            param_ranges=param_ranges,
            max_configs=max_configs
        )

        # Run each config
        run_ids = []
        for i, config in enumerate(configs, 1):
            if self.verbose:
                print(f"\n[{i}/{len(configs)}] Testing configuration...")

            run_id = self.run_single_experiment(
                config=config,
                notes=f"Parameter sweep {i}/{len(configs)}",
                tags=["sweep"]
            )
            run_ids.append(run_id)

        if self.verbose:
            print("\n" + "="*80)
            print(f"PARAMETER SWEEP COMPLETE: {len(run_ids)} experiments")
            print("="*80)

        return run_ids

    def find_best_configuration(self, metric: str = "top_1_accuracy",
                               tags: Optional[List[str]] = None) -> Dict:
        """
        Find best configuration by metric

        Args:
            metric: Metric to optimize for
            tags: Optional tag filter

        Returns:
            Best experiment data
        """
        leaderboard = self.tracker.get_leaderboard(
            metric=metric,
            tags=tags,
            limit=1
        )

        if not leaderboard:
            raise ValueError("No experiments found")

        best = leaderboard[0]
        best_experiment = self.tracker.get_experiment(best['run_id'])

        return best_experiment

    def generate_final_report(self, baseline_run_id: str,
                            best_run_id: Optional[str] = None):
        """
        Generate comprehensive final report

        Args:
            baseline_run_id: Baseline run ID
            best_run_id: Best run ID (if None, will find best automatically)
        """
        if best_run_id is None:
            # Find best
            best_exp = self.find_best_configuration()
            best_run_id = best_exp['run_id']

        # Get all experiments
        leaderboard = self.tracker.get_leaderboard(limit=1000)
        all_experiments = [self.tracker.get_experiment(e['run_id']) for e in leaderboard]

        # Generate report
        report_path = self.reporter.generate_optimization_summary(
            tracker=self.tracker,
            baseline_run_id=baseline_run_id,
            best_run_id=best_run_id,
            all_experiments=all_experiments
        )

        if self.verbose:
            print(f"\n[REPORT] Final report generated: {report_path}")

        return report_path

    def close(self):
        """Clean up resources"""
        self.tracker.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="TCG Card Identification System Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "command",
        choices=["baseline", "sweep", "report", "leaderboard"],
        help="Command to run"
    )

    parser.add_argument(
        "--test-dir",
        default="test-images/one-piece",
        help="Test images directory"
    )

    parser.add_argument(
        "--ground-truth",
        default="test-images/one-piece/ground_truth.json",
        help="Ground truth JSON file"
    )

    parser.add_argument(
        "--baseline-run",
        help="Baseline run ID (for comparison)"
    )

    parser.add_argument(
        "--config",
        help="Config ID to use"
    )

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = OptimizationOrchestrator(
        test_dir=args.test_dir,
        ground_truth_file=args.ground_truth,
        verbose=True
    )

    try:
        if args.command == "baseline":
            # Establish baseline
            baseline_run_id = orchestrator.establish_baseline()
            print(f"\n[SUCCESS] Baseline run ID: {baseline_run_id}")
            print(f"   SAVE THIS ID for future comparisons!")

        elif args.command == "sweep":
            if not args.baseline_run:
                print("ERROR: --baseline-run required for sweep")
                sys.exit(1)

            # Example parameter sweep
            param_ranges = {
                "orb_nfeatures": [500, 1000, 2000],
                "orb_verify_top_n": [5, 10, 20],
                "threshold_high": [0.60, 0.65, 0.70]
            }

            run_ids = orchestrator.run_parameter_sweep(
                base_config_id=args.baseline_run,
                param_ranges=param_ranges,
                max_configs=20
            )

            print(f"\n[SUCCESS] Completed {len(run_ids)} experiments")

        elif args.command == "leaderboard":
            orchestrator.tracker.print_leaderboard(limit=20)

        elif args.command == "report":
            if not args.baseline_run:
                print("ERROR: --baseline-run required for report")
                sys.exit(1)

            report_path = orchestrator.generate_final_report(
                baseline_run_id=args.baseline_run
            )
            print(f"\n[SUCCESS] Report generated: {report_path}")

    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
