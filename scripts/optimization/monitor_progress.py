#!/usr/bin/env python3
"""
Monitor optimization progress
"""
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from experiments.tracker import ExperimentTracker


def monitor():
    """Monitor optimization progress"""
    tracker = ExperimentTracker()

    try:
        # Get all experiments
        leaderboard = tracker.get_leaderboard(limit=100)

        # Count by tags
        baseline_count = len([e for e in leaderboard if 'baseline' in e.get('tags', [])])
        sweep_001_count = len([e for e in leaderboard if 'sweep_001' in e.get('tags', [])])

        print("="*80)
        print("OPTIMIZATION PROGRESS MONITOR")
        print("="*80)
        print(f"\nTotal Experiments: {len(leaderboard)}")
        print(f"  Baseline:   {baseline_count}")
        print(f"  Sweep #001: {sweep_001_count}/27 (expected)")
        print()

        # Show top 5
        print("Current Top 5:")
        print("-"*80)
        for i, entry in enumerate(leaderboard[:5], 1):
            tags_str = ', '.join(entry.get('tags', []))
            print(f"{i}. {entry['config_name'][:40]:40s} "
                  f"Acc: {entry['top_1_accuracy']*100:5.1f}% "
                  f"Time: {entry['avg_time_ms']:4.0f}ms "
                  f"[{tags_str}]")

        print()

        # Best vs baseline
        best = leaderboard[0]
        baseline = [e for e in leaderboard if 'baseline' in e.get('tags', [])]

        if baseline:
            baseline = baseline[0]
            acc_improvement = (best['top_1_accuracy'] - baseline['top_1_accuracy']) / baseline['top_1_accuracy'] * 100
            time_change = (best['avg_time_ms'] - baseline['avg_time_ms']) / baseline['avg_time_ms'] * 100

            print("Best vs Baseline:")
            print(f"  Accuracy: {baseline['top_1_accuracy']*100:.1f}% -> {best['top_1_accuracy']*100:.1f}% ({acc_improvement:+.1f}%)")
            print(f"  Time:     {baseline['avg_time_ms']:.0f}ms -> {best['avg_time_ms']:.0f}ms ({time_change:+.1f}%)")

        print()
        print("="*80)

    finally:
        tracker.close()


if __name__ == "__main__":
    monitor()
