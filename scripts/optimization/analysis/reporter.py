#!/usr/bin/env python3
"""
Analysis and Reporting Tools
Generates comprehensive reports with visualizations
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class OptimizationReport:
    """Comprehensive optimization report"""
    title: str
    summary: Dict
    baseline_metrics: Dict
    best_metrics: Dict
    improvement: Dict
    experiments_run: int
    total_time_hours: float
    key_findings: List[str]
    recommendations: List[str]
    visualizations: List[str]  # Paths to generated charts


class AnalysisReporter:
    """
    Generates analysis reports and visualizations
    """

    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: Directory for reports and visualizations
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "reports"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_experiment_report(self, experiment_data: Dict,
                                  comparison_baseline: Optional[Dict] = None) -> str:
        """
        Generate comprehensive report for an experiment

        Args:
            experiment_data: Experiment results
            comparison_baseline: Optional baseline for comparison

        Returns:
            Path to generated markdown report
        """
        report_lines = []

        # Header
        report_lines.append(f"# Experiment Report: {experiment_data['config_name']}")
        report_lines.append(f"\n**Run ID:** {experiment_data['run_id']}")
        report_lines.append(f"**Timestamp:** {experiment_data['timestamp']}")
        if experiment_data.get('git_commit'):
            report_lines.append(f"**Git Commit:** {experiment_data['git_commit']}")
        report_lines.append("\n---\n")

        # Metrics Summary
        metrics = experiment_data['metrics']
        report_lines.append("## 📊 Performance Metrics\n")
        report_lines.append(f"| Metric | Value |")
        report_lines.append(f"|--------|-------|")
        report_lines.append(f"| Top-1 Accuracy | **{metrics['top_1_accuracy']*100:.2f}%** |")
        report_lines.append(f"| Top-3 Accuracy | {metrics['top_3_accuracy']*100:.2f}% |")
        report_lines.append(f"| Top-5 Accuracy | {metrics['top_5_accuracy']*100:.2f}% |")
        report_lines.append(f"| Mean Reciprocal Rank | {metrics['mean_reciprocal_rank']:.4f} |")
        report_lines.append(f"| Average Time | {metrics['avg_time_ms']:.0f}ms |")
        report_lines.append(f"| HIGH Confidence Rate | {metrics['high_confidence_rate']*100:.1f}% |")
        report_lines.append(f"| Average Score | {metrics['avg_final_score']:.4f} |")
        report_lines.append("\n")

        # Comparison with baseline
        if comparison_baseline:
            report_lines.append("## 📈 Comparison with Baseline\n")
            baseline_metrics = comparison_baseline['metrics']

            improvements = []
            for metric_name, metric_val in metrics.items():
                baseline_val = baseline_metrics.get(metric_name, 0)
                if baseline_val > 0 and metric_name != 'avg_time_ms':
                    improvement = ((metric_val - baseline_val) / baseline_val) * 100
                    improvements.append((metric_name, improvement, metric_val, baseline_val))
                elif metric_name == 'avg_time_ms' and baseline_val > 0:
                    improvement = ((baseline_val - metric_val) / baseline_val) * 100
                    improvements.append((metric_name, improvement, metric_val, baseline_val))

            report_lines.append("| Metric | Baseline | Current | Improvement |")
            report_lines.append("|--------|----------|---------|-------------|")
            for metric_name, improvement, current, baseline in improvements:
                sign = "+" if improvement > 0 else ""
                report_lines.append(
                    f"| {metric_name} | {baseline:.4f} | {current:.4f} | "
                    f"**{sign}{improvement:.2f}%** |"
                )
            report_lines.append("\n")

        # Configuration
        if 'config' in experiment_data and experiment_data['config']:
            report_lines.append("## ⚙️ Configuration\n")
            config = experiment_data['config']
            params = config.get('parameters', {})

            # Group by category
            categories = {}
            for param_name, param_data in params.items():
                category = param_data.get('category', 'general')
                if category not in categories:
                    categories[category] = []
                categories[category].append((param_name, param_data['value']))

            for category, param_list in sorted(categories.items()):
                report_lines.append(f"\n### {category.title()}\n")
                report_lines.append("| Parameter | Value |")
                report_lines.append("|-----------|-------|")
                for param_name, value in param_list:
                    report_lines.append(f"| {param_name} | `{value}` |")
            report_lines.append("\n")

        # Provenance (per-image results)
        if 'provenance' in experiment_data:
            provenance = experiment_data['provenance']
            correct_count = sum(1 for p in provenance if p['correct'])
            total_count = len(provenance)

            report_lines.append(f"## 🎯 Per-Image Results ({correct_count}/{total_count} correct)\n")

            # Failed images
            failed = [p for p in provenance if not p['correct']]
            if failed:
                report_lines.append(f"\n### Failed Images ({len(failed)})\n")
                report_lines.append("| Image | Ground Truth | Predicted | Confidence | Score |")
                report_lines.append("|-------|--------------|-----------|------------|-------|")
                for f in failed[:10]:  # Limit to first 10
                    report_lines.append(
                        f"| {f['image_name']} | {f['ground_truth']} | "
                        f"{f['predicted']} | {f['confidence']} | {f['final_score']:.4f} |"
                    )
                if len(failed) > 10:
                    report_lines.append(f"\n*... and {len(failed) - 10} more*\n")
            report_lines.append("\n")

        # Save report
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        report_file = self.output_dir / f"report_{experiment_data['run_id']}_{timestamp}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        return str(report_file)

    def generate_optimization_summary(self, tracker, baseline_run_id: str,
                                     best_run_id: str,
                                     all_experiments: List[Dict]) -> str:
        """
        Generate summary of entire optimization process

        Args:
            tracker: ExperimentTracker instance
            baseline_run_id: Run ID of baseline
            best_run_id: Run ID of best configuration
            all_experiments: List of all experiment data

        Returns:
            Path to generated report
        """
        baseline = tracker.get_experiment(baseline_run_id)
        best = tracker.get_experiment(best_run_id)

        if not baseline or not best:
            raise ValueError("Baseline or best experiment not found")

        report_lines = []

        # Header
        report_lines.append("# Optimization Summary Report\n")
        report_lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_lines.append(f"**Total Experiments:** {len(all_experiments)}\n")
        report_lines.append("---\n")

        # Executive Summary
        baseline_acc = baseline['metrics']['top_1_accuracy']
        best_acc = best['metrics']['top_1_accuracy']
        acc_improvement = ((best_acc - baseline_acc) / baseline_acc) * 100

        baseline_time = baseline['metrics']['avg_time_ms']
        best_time = best['metrics']['avg_time_ms']
        time_change = ((best_time - baseline_time) / baseline_time) * 100

        report_lines.append("## 🎯 Executive Summary\n")
        report_lines.append(f"- **Baseline Accuracy:** {baseline_acc*100:.2f}%")
        report_lines.append(f"- **Best Accuracy:** {best_acc*100:.2f}%")
        report_lines.append(f"- **Improvement:** {acc_improvement:+.2f}%\n")
        report_lines.append(f"- **Baseline Speed:** {baseline_time:.0f}ms")
        report_lines.append(f"- **Best Speed:** {best_time:.0f}ms")
        report_lines.append(f"- **Speed Change:** {time_change:+.2f}%\n")

        # Best Configuration
        report_lines.append("## 🏆 Best Configuration\n")
        report_lines.append(f"**Name:** {best['config_name']}\n")
        report_lines.append(f"**Run ID:** {best['run_id']}\n")
        report_lines.append("### Key Changes from Baseline\n")

        config_changes = tracker._diff_configs(baseline['config'], best['config'])
        if config_changes:
            report_lines.append("| Parameter | Baseline | Best | Change |")
            report_lines.append("|-----------|----------|------|--------|")
            for param, values in sorted(config_changes.items()):
                baseline_val = values['config_a']
                best_val = values['config_b']
                report_lines.append(f"| {param} | `{baseline_val}` | `{best_val}` | ➔ |")
        else:
            report_lines.append("*No configuration changes detected*\n")

        report_lines.append("\n")

        # Optimization Progress
        report_lines.append("## 📈 Optimization Progress\n")

        # Sort experiments by timestamp
        sorted_experiments = sorted(all_experiments, key=lambda x: x['timestamp'])

        report_lines.append("| # | Config Name | Top-1 Acc | Time (ms) | Notes |")
        report_lines.append("|---|-------------|-----------|-----------|-------|")

        for idx, exp in enumerate(sorted_experiments[:20], 1):  # Limit to first 20
            acc = exp['metrics']['top_1_accuracy']
            time_ms = exp['metrics']['avg_time_ms']
            notes = exp.get('notes', '')[:30]  # Truncate notes
            report_lines.append(f"| {idx} | {exp['config_name'][:25]} | {acc*100:.2f}% | {time_ms:.0f}ms | {notes} |")

        if len(sorted_experiments) > 20:
            report_lines.append(f"\n*... and {len(sorted_experiments) - 20} more experiments*\n")

        report_lines.append("\n")

        # Key Findings
        report_lines.append("## 💡 Key Findings\n")

        # Analyze what worked
        findings = self._analyze_experiments(all_experiments)
        for finding in findings:
            report_lines.append(f"- {finding}")

        report_lines.append("\n")

        # Recommendations
        report_lines.append("## 🎯 Recommendations\n")
        recommendations = self._generate_recommendations(baseline, best, all_experiments)
        for rec in recommendations:
            report_lines.append(f"- {rec}")

        report_lines.append("\n")

        # Save report
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        report_file = self.output_dir / f"optimization_summary_{timestamp}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        print(f"\n📄 Optimization summary report generated: {report_file}")
        return str(report_file)

    def _analyze_experiments(self, experiments: List[Dict]) -> List[str]:
        """Analyze experiments to find patterns"""
        findings = []

        # Find accuracy trend
        accuracies = [e['metrics']['top_1_accuracy'] for e in experiments]
        if len(accuracies) > 1:
            trend = np.polyfit(range(len(accuracies)), accuracies, 1)[0]
            if trend > 0.001:
                findings.append(f"Accuracy improved over time (trend: +{trend*100:.3f}% per experiment)")
            elif trend < -0.001:
                findings.append(f"Accuracy declined over time (trend: {trend*100:.3f}% per experiment)")
            else:
                findings.append("Accuracy remained relatively stable")

        # Find speed trend
        times = [e['metrics']['avg_time_ms'] for e in experiments]
        if len(times) > 1:
            time_trend = np.polyfit(range(len(times)), times, 1)[0]
            if time_trend < -1:
                findings.append(f"Speed improved over time (trend: {time_trend:.1f}ms per experiment)")
            elif time_trend > 1:
                findings.append(f"Speed decreased over time (trend: +{time_trend:.1f}ms per experiment)")

        # Best performers
        best_acc = max(experiments, key=lambda x: x['metrics']['top_1_accuracy'])
        fastest = min(experiments, key=lambda x: x['metrics']['avg_time_ms'])

        findings.append(f"Best accuracy: {best_acc['config_name']} ({best_acc['metrics']['top_1_accuracy']*100:.2f}%)")
        findings.append(f"Fastest: {fastest['config_name']} ({fastest['metrics']['avg_time_ms']:.0f}ms)")

        return findings

    def _generate_recommendations(self, baseline: Dict, best: Dict,
                                 all_experiments: List[Dict]) -> List[str]:
        """Generate recommendations based on results"""
        recommendations = []

        # Check if best is significantly better
        acc_improvement = best['metrics']['top_1_accuracy'] - baseline['metrics']['top_1_accuracy']

        if acc_improvement > 0.05:
            recommendations.append(
                f"✅ Deploy best configuration - significant accuracy improvement ({acc_improvement*100:.2f}%)"
            )
        elif acc_improvement > 0.02:
            recommendations.append(
                f"Consider deploying best configuration - moderate improvement ({acc_improvement*100:.2f}%)"
            )
        else:
            recommendations.append(
                f"⚠️  Limited improvement found ({acc_improvement*100:.2f}%) - may need different optimization approach"
            )

        # Speed considerations
        time_change = best['metrics']['avg_time_ms'] - baseline['metrics']['avg_time_ms']
        if time_change > 100:
            recommendations.append(
                f"⚠️  Best config is slower (+{time_change:.0f}ms) - evaluate speed/accuracy tradeoff"
            )
        elif time_change < -100:
            recommendations.append(
                f"✅ Best config is also faster ({time_change:.0f}ms speedup)"
            )

        # Confidence rate
        best_conf = best['metrics']['high_confidence_rate']
        baseline_conf = baseline['metrics']['high_confidence_rate']
        if best_conf < baseline_conf - 0.1:
            recommendations.append(
                f"⚠️  HIGH confidence rate dropped ({baseline_conf*100:.1f}% → {best_conf*100:.1f}%) - review thresholds"
            )

        # Further optimization
        if acc_improvement < 0.10:
            recommendations.append(
                "Consider additional optimization strategies: fine-tuning models, ensemble methods, or augmentation"
            )

        return recommendations

    def create_comparison_chart(self, experiments: List[Dict],
                               metric: str = "top_1_accuracy",
                               title: str = "Optimization Progress") -> str:
        """
        Create comparison chart (returns ASCII art for simplicity)

        For production, use matplotlib/plotly
        """
        values = [e['metrics'][metric] for e in experiments]
        names = [e['config_name'][:20] for e in experiments]

        # Simple ASCII chart
        chart_lines = []
        chart_lines.append(f"\n{title}")
        chart_lines.append("=" * 60)

        max_val = max(values)
        min_val = min(values)
        range_val = max_val - min_val if max_val != min_val else 1

        for name, value in zip(names, values):
            normalized = (value - min_val) / range_val
            bar_length = int(normalized * 40)
            bar = "█" * bar_length
            chart_lines.append(f"{name:20s} | {bar} {value:.4f}")

        chart_lines.append("=" * 60)

        chart_str = '\n'.join(chart_lines)
        print(chart_str)

        return chart_str


if __name__ == "__main__":
    print("Analysis Reporter Module")
    print("Import this module to generate reports")
