#!/usr/bin/env python3
"""
Experiment Tracking System
Tracks all experiments, results, and provides leaderboard functionality
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import subprocess


@dataclass
class ExperimentRun:
    """Represents a single experiment run"""
    run_id: str
    config_id: str
    config_name: str
    timestamp: str
    git_commit: Optional[str]
    hardware_info: Dict[str, str]

    # Results
    top_1_accuracy: float
    top_3_accuracy: float
    top_5_accuracy: float
    mean_reciprocal_rank: float
    avg_time_ms: float
    high_confidence_rate: float
    avg_final_score: float

    # Metadata
    num_test_cases: int
    test_dataset: str
    notes: str = ""
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class ExperimentTracker:
    """
    Tracks experiments and maintains results database
    """

    def __init__(self, db_path: str = None):
        """
        Args:
            db_path: Path to SQLite database
        """
        if db_path is None:
            db_path = Path(__file__).parent / "experiments.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()

    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()

        # Experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                run_id TEXT PRIMARY KEY,
                config_id TEXT NOT NULL,
                config_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                git_commit TEXT,
                hardware_info TEXT,
                top_1_accuracy REAL,
                top_3_accuracy REAL,
                top_5_accuracy REAL,
                mean_reciprocal_rank REAL,
                avg_time_ms REAL,
                high_confidence_rate REAL,
                avg_final_score REAL,
                num_test_cases INTEGER,
                test_dataset TEXT,
                notes TEXT,
                tags TEXT
            )
        ''')

        # Results provenance table (which images passed/failed)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS result_provenance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                image_name TEXT NOT NULL,
                ground_truth TEXT,
                predicted TEXT,
                correct INTEGER,
                confidence TEXT,
                final_score REAL,
                time_ms INTEGER,
                FOREIGN KEY (run_id) REFERENCES experiments(run_id)
            )
        ''')

        # Config snapshots table (store full config with each experiment)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_snapshots (
                run_id TEXT PRIMARY KEY,
                config_json TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES experiments(run_id)
            )
        ''')

        self.conn.commit()

    def log_experiment(self, run: ExperimentRun, config_data: Dict,
                      result_details: List[Dict]) -> str:
        """
        Log an experiment run

        Args:
            run: ExperimentRun object
            config_data: Full configuration dict
            result_details: List of per-image results

        Returns:
            run_id
        """
        cursor = self.conn.cursor()

        # Insert experiment
        cursor.execute('''
            INSERT INTO experiments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            run.run_id,
            run.config_id,
            run.config_name,
            run.timestamp,
            run.git_commit,
            json.dumps(run.hardware_info),
            run.top_1_accuracy,
            run.top_3_accuracy,
            run.top_5_accuracy,
            run.mean_reciprocal_rank,
            run.avg_time_ms,
            run.high_confidence_rate,
            run.avg_final_score,
            run.num_test_cases,
            run.test_dataset,
            run.notes,
            json.dumps(run.tags)
        ))

        # Insert config snapshot
        cursor.execute('''
            INSERT INTO config_snapshots VALUES (?, ?)
        ''', (run.run_id, json.dumps(config_data)))

        # Insert result provenance
        for result in result_details:
            cursor.execute('''
                INSERT INTO result_provenance (run_id, image_name, ground_truth, predicted,
                                              correct, confidence, final_score, time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run.run_id,
                result['image_name'],
                result.get('ground_truth'),
                result['predicted'],
                1 if result['correct'] else 0,
                result['confidence'],
                result['final_score'],
                result['time_ms']
            ))

        self.conn.commit()
        return run.run_id

    def get_leaderboard(self, metric: str = "top_1_accuracy",
                       tags: Optional[List[str]] = None,
                       limit: int = 20) -> List[Dict]:
        """
        Get leaderboard sorted by metric

        Args:
            metric: Metric to sort by (top_1_accuracy, avg_time_ms, etc.)
            tags: Filter by tags
            limit: Number of results

        Returns:
            List of experiment summaries
        """
        cursor = self.conn.cursor()

        # Build query
        query = f'''
            SELECT run_id, config_id, config_name, timestamp,
                   top_1_accuracy, top_3_accuracy, avg_time_ms,
                   high_confidence_rate, avg_final_score, tags
            FROM experiments
        '''

        # Add tag filter
        where_clause = ""
        if tags:
            # SQLite JSON functions for filtering
            tag_conditions = " OR ".join([f"tags LIKE '%{tag}%'" for tag in tags])
            where_clause = f"WHERE {tag_conditions}"
            query += " " + where_clause

        # Sort
        reverse = metric not in ["avg_time_ms"]  # Lower is better for time
        order = "DESC" if reverse else "ASC"
        query += f" ORDER BY {metric} {order} LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()

        leaderboard = []
        for row in rows:
            leaderboard.append({
                'rank': len(leaderboard) + 1,
                'run_id': row[0],
                'config_id': row[1],
                'config_name': row[2],
                'timestamp': row[3],
                'top_1_accuracy': row[4],
                'top_3_accuracy': row[5],
                'avg_time_ms': row[6],
                'high_confidence_rate': row[7],
                'avg_final_score': row[8],
                'tags': json.loads(row[9]) if row[9] else []
            })

        return leaderboard

    def get_experiment(self, run_id: str) -> Optional[Dict]:
        """Get full experiment details"""
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT * FROM experiments WHERE run_id = ?
        ''', (run_id,))

        row = cursor.fetchone()
        if not row:
            return None

        # Get config snapshot
        cursor.execute('''
            SELECT config_json FROM config_snapshots WHERE run_id = ?
        ''', (run_id,))
        config_row = cursor.fetchone()

        # Get result provenance
        cursor.execute('''
            SELECT image_name, ground_truth, predicted, correct, confidence, final_score, time_ms
            FROM result_provenance WHERE run_id = ?
        ''', (run_id,))
        provenance_rows = cursor.fetchall()

        return {
            'run_id': row[0],
            'config_id': row[1],
            'config_name': row[2],
            'timestamp': row[3],
            'git_commit': row[4],
            'hardware_info': json.loads(row[5]) if row[5] else {},
            'metrics': {
                'top_1_accuracy': row[6],
                'top_3_accuracy': row[7],
                'top_5_accuracy': row[8],
                'mean_reciprocal_rank': row[9],
                'avg_time_ms': row[10],
                'high_confidence_rate': row[11],
                'avg_final_score': row[12]
            },
            'num_test_cases': row[13],
            'test_dataset': row[14],
            'notes': row[15],
            'tags': json.loads(row[16]) if row[16] else [],
            'config': json.loads(config_row[0]) if config_row else {},
            'provenance': [
                {
                    'image_name': p[0],
                    'ground_truth': p[1],
                    'predicted': p[2],
                    'correct': bool(p[3]),
                    'confidence': p[4],
                    'final_score': p[5],
                    'time_ms': p[6]
                }
                for p in provenance_rows
            ]
        }

    def compare_experiments(self, run_id_a: str, run_id_b: str) -> Dict:
        """
        Compare two experiments

        Returns:
            Comparison dict showing differences
        """
        exp_a = self.get_experiment(run_id_a)
        exp_b = self.get_experiment(run_id_b)

        if not exp_a or not exp_b:
            raise ValueError("One or both experiments not found")

        # Metric comparisons
        comparison = {
            'experiment_a': {
                'run_id': exp_a['run_id'],
                'config_name': exp_a['config_name'],
                'timestamp': exp_a['timestamp']
            },
            'experiment_b': {
                'run_id': exp_b['run_id'],
                'config_name': exp_b['config_name'],
                'timestamp': exp_b['timestamp']
            },
            'metrics': {}
        }

        for metric in ['top_1_accuracy', 'top_3_accuracy', 'avg_time_ms', 'avg_final_score', 'high_confidence_rate']:
            val_a = exp_a['metrics'][metric]
            val_b = exp_b['metrics'][metric]
            diff = val_b - val_a

            # For time, lower is better
            if metric == 'avg_time_ms':
                improvement = -diff / val_a if val_a > 0 else 0
            else:
                improvement = diff / val_a if val_a > 0 else 0

            comparison['metrics'][metric] = {
                'experiment_a': val_a,
                'experiment_b': val_b,
                'difference': diff,
                'improvement_pct': improvement * 100
            }

        # Image-level differences (which images changed)
        prov_a = {p['image_name']: p for p in exp_a['provenance']}
        prov_b = {p['image_name']: p for p in exp_b['provenance']}

        improved = []
        regressed = []

        for img_name in prov_a.keys():
            if img_name in prov_b:
                a_correct = prov_a[img_name]['correct']
                b_correct = prov_b[img_name]['correct']

                if not a_correct and b_correct:
                    improved.append(img_name)
                elif a_correct and not b_correct:
                    regressed.append(img_name)

        comparison['image_changes'] = {
            'improved': improved,
            'regressed': regressed,
            'net_change': len(improved) - len(regressed)
        }

        # Config differences
        config_diff = self._diff_configs(exp_a['config'], exp_b['config'])
        comparison['config_changes'] = config_diff

        return comparison

    def _diff_configs(self, config_a: Dict, config_b: Dict) -> Dict[str, Any]:
        """Find differences between two configs"""
        params_a = config_a.get('parameters', {})
        params_b = config_b.get('parameters', {})

        differences = {}

        all_params = set(params_a.keys()) | set(params_b.keys())

        for param in all_params:
            val_a = params_a.get(param, {}).get('value')
            val_b = params_b.get(param, {}).get('value')

            if val_a != val_b:
                differences[param] = {
                    'config_a': val_a,
                    'config_b': val_b
                }

        return differences

    def get_problematic_images(self, min_experiments: int = 3,
                              max_accuracy: float = 0.5) -> List[Dict]:
        """
        Find images that consistently fail across experiments

        Args:
            min_experiments: Minimum number of experiments image must appear in
            max_accuracy: Maximum accuracy to be considered problematic

        Returns:
            List of problematic images with statistics
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT image_name,
                   COUNT(*) as num_experiments,
                   SUM(correct) as num_correct,
                   AVG(final_score) as avg_score,
                   AVG(CAST(correct AS REAL)) as accuracy
            FROM result_provenance
            GROUP BY image_name
            HAVING num_experiments >= ? AND accuracy <= ?
            ORDER BY accuracy ASC, num_experiments DESC
        ''', (min_experiments, max_accuracy))

        rows = cursor.fetchall()

        problematic = []
        for row in rows:
            problematic.append({
                'image_name': row[0],
                'num_experiments': row[1],
                'num_correct': row[2],
                'avg_score': row[3],
                'accuracy': row[4]
            })

        return problematic

    def print_leaderboard(self, metric: str = "top_1_accuracy", limit: int = 10):
        """Print leaderboard to console"""
        leaderboard = self.get_leaderboard(metric=metric, limit=limit)

        print("="*100)
        print(f"LEADERBOARD - Sorted by {metric}")
        print("="*100)
        print(f"{'Rank':<6} {'Config Name':<30} {'Top-1':<10} {'Top-3':<10} {'Time(ms)':<12} {'HIGH%':<10} {'Timestamp':<20}")
        print("-"*100)

        for entry in leaderboard:
            print(f"{entry['rank']:<6} "
                  f"{entry['config_name'][:28]:<30} "
                  f"{entry['top_1_accuracy']*100:>6.2f}%   "
                  f"{entry['top_3_accuracy']*100:>6.2f}%   "
                  f"{entry['avg_time_ms']:>8.0f}ms   "
                  f"{entry['high_confidence_rate']*100:>6.1f}%   "
                  f"{entry['timestamp']:<20}")

        print("="*100)

    def export_to_csv(self, output_path: str, tags: Optional[List[str]] = None):
        """Export experiments to CSV for external analysis"""
        import csv

        cursor = self.conn.cursor()

        query = '''
            SELECT run_id, config_id, config_name, timestamp,
                   top_1_accuracy, top_3_accuracy, top_5_accuracy,
                   mean_reciprocal_rank, avg_time_ms, high_confidence_rate,
                   avg_final_score, num_test_cases, test_dataset, tags
            FROM experiments
        '''

        if tags:
            tag_conditions = " OR ".join([f"tags LIKE '%{tag}%'" for tag in tags])
            query += f" WHERE {tag_conditions}"

        query += " ORDER BY timestamp DESC"

        cursor.execute(query)
        rows = cursor.fetchall()

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'run_id', 'config_id', 'config_name', 'timestamp',
                'top_1_accuracy', 'top_3_accuracy', 'top_5_accuracy',
                'mean_reciprocal_rank', 'avg_time_ms', 'high_confidence_rate',
                'avg_final_score', 'num_test_cases', 'test_dataset', 'tags'
            ])
            writer.writerows(rows)

        print(f"Exported {len(rows)} experiments to {output_path}")

    def close(self):
        """Close database connection"""
        self.conn.close()


def get_git_commit() -> Optional[str]:
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except:
        return None


def get_hardware_info() -> Dict[str, str]:
    """Get basic hardware info"""
    import platform
    import psutil

    return {
        'platform': platform.system(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'cpu_count': str(psutil.cpu_count()),
        'memory_gb': f"{psutil.virtual_memory().total / (1024**3):.1f}"
    }


if __name__ == "__main__":
    # Example usage
    tracker = ExperimentTracker()

    # Print leaderboard
    tracker.print_leaderboard()

    # Get problematic images
    problematic = tracker.get_problematic_images()
    if problematic:
        print(f"\nProblematic Images ({len(problematic)}):")
        for img in problematic[:5]:
            print(f"  {img['image_name']}: {img['accuracy']*100:.1f}% accuracy "
                  f"({img['num_correct']}/{img['num_experiments']})")

    tracker.close()
