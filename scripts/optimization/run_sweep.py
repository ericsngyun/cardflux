#!/usr/bin/env python3
"""
Run a specific optimization sweep
"""
import sys
import importlib.util
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_optimization import OptimizationOrchestrator
from config.system import ConfigurationManager


def run_sweep(sweep_file: str):
    """
    Run a sweep defined in a sweep config file

    Args:
        sweep_file: Path to sweep config Python file
    """
    # Load sweep configuration
    spec = importlib.util.spec_from_file_location("sweep_config", sweep_file)
    sweep_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sweep_config)

    print("="*80)
    print("OPTIMIZATION SWEEP")
    print("="*80)
    print(f"Sweep file: {Path(sweep_file).name}")
    print(f"Baseline: {sweep_config.BASELINE_RUN_ID}")
    print(f"Parameters: {list(sweep_config.PARAM_RANGES.keys())}")
    print(f"Max configs: {sweep_config.MAX_CONFIGS}")
    print(f"Notes: {sweep_config.NOTES}")
    print(f"Tags: {sweep_config.TAGS}")
    print("="*80)
    print()

    # Initialize orchestrator
    orchestrator = OptimizationOrchestrator(
        test_dir="../../test-images/one-piece",
        ground_truth_file="../../test-images/one-piece/ground_truth.json",
        verbose=True
    )

    try:
        # Load baseline config
        config_manager = ConfigurationManager()

        # Extract config ID from run ID
        # Run ID format: run_<timestamp>_<config_id>
        baseline_config_id = sweep_config.BASELINE_RUN_ID.split('_', 2)[2]
        baseline_config = config_manager.load_config(baseline_config_id)

        print(f"Loaded baseline config: {baseline_config.name}")
        print()

        # Run parameter sweep
        run_ids = orchestrator.run_parameter_sweep(
            base_config_id=baseline_config_id,
            param_ranges=sweep_config.PARAM_RANGES,
            max_configs=sweep_config.MAX_CONFIGS
        )

        print("\n" + "="*80)
        print("SWEEP COMPLETE")
        print("="*80)
        print(f"Total experiments: {len(run_ids)}")
        print(f"Baseline run: {sweep_config.BASELINE_RUN_ID}")
        print()

        # Show leaderboard
        print("Top 5 Configurations:")
        orchestrator.tracker.print_leaderboard(limit=5)

        # Find best
        best = orchestrator.find_best_configuration()
        baseline = orchestrator.tracker.get_experiment(sweep_config.BASELINE_RUN_ID)

        print("\n" + "="*80)
        print("BEST vs BASELINE")
        print("="*80)

        baseline_acc = baseline['metrics']['top_1_accuracy']
        best_acc = best['metrics']['top_1_accuracy']
        acc_improvement = (best_acc - baseline_acc) / baseline_acc * 100

        baseline_time = baseline['metrics']['avg_time_ms']
        best_time = best['metrics']['avg_time_ms']
        time_change = (best_time - baseline_time) / baseline_time * 100

        print(f"\nAccuracy:")
        print(f"  Baseline: {baseline_acc*100:.2f}%")
        print(f"  Best:     {best_acc*100:.2f}%")
        print(f"  Change:   {acc_improvement:+.2f}%")

        print(f"\nSpeed:")
        print(f"  Baseline: {baseline_time:.0f}ms")
        print(f"  Best:     {best_time:.0f}ms")
        print(f"  Change:   {time_change:+.2f}%")

        print(f"\nBest Config: {best['config_name']}")
        print(f"Best Run ID: {best['run_id']}")

        # Recommendation
        print("\n" + "="*80)
        print("RECOMMENDATION")
        print("="*80)

        if best_acc > baseline_acc and (best_acc - baseline_acc) >= 0.05:  # 5% improvement
            print("✓ DEPLOY: Significant accuracy improvement")
            print(f"  Deploy config: {best['config_id']}")
        elif best_acc > baseline_acc and (best_acc - baseline_acc) >= 0.02:  # 2% improvement
            print("~ CONSIDER: Moderate improvement, validate on larger test set")
        else:
            print("✗ REVERT: No significant improvement found")
            print("  Keep baseline configuration")
            print("  Try different optimization strategy")

        print("\n" + "="*80)

    finally:
        orchestrator.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run optimization sweep")
    parser.add_argument("sweep_file", help="Path to sweep configuration file")

    args = parser.parse_args()

    run_sweep(args.sweep_file)
