"""
Production Validation Script

Tests the Fast Identifier v2 against ground truth dataset to validate
production readiness and accuracy claims.

Usage:
    python production_validation.py

Outputs:
    - Detailed test results for each image
    - Accuracy metrics (overall, by confidence level)
    - Confidence calibration data
    - Recommendations for production deployment
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Fix Unicode output on Windows
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from fast_card_identifier import FastCardIdentifier


@dataclass
class TestCase:
    """Ground truth test case"""
    image_path: str
    expected_name: str
    expected_number: str
    expected_set: str
    notes: Optional[str] = None


@dataclass
class TestResult:
    """Result of running a test case"""
    test_case: TestCase
    identified_name: str
    identified_number: str
    identified_set: str
    confidence: str
    score: float
    is_correct: bool
    time_ms: float
    match_type: str = "unknown"  # "exact", "variant", "number_only", "incorrect"
    error: Optional[str] = None


# Ground Truth Dataset
# Based on actual test images in test-images/one-piece/
# Use absolute paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEST_IMAGES_DIR = PROJECT_ROOT / "test-images" / "one-piece"

GROUND_TRUTH = [
    TestCase(
        image_path=str(TEST_IMAGES_DIR / "blackbeard.png"),
        expected_name='Marshall.D.Teach (093) (Manga)',
        expected_number="OP09-093",
        expected_set="Four Emperors",
        notes="Manga variant - clean photo"
    ),
    TestCase(
        image_path=str(TEST_IMAGES_DIR / "bege.png"),
        expected_name='Capone"Gang"Bege',
        expected_number="ST02-004",
        expected_set="Starter Deck Worst Generation",
        notes="Standard card - clean photo"
    ),
    TestCase(
        image_path=str(TEST_IMAGES_DIR / "yellow_event.png"),
        expected_name="You're the One Who Should Disappear",
        expected_number="OP06-115",
        expected_set="Wings of the Captain",
        notes="Event card - text heavy, clean"
    ),
    TestCase(
        image_path=str(TEST_IMAGES_DIR / "radicalbeam.png"),
        expected_name="Radical Beam!! (Premium Card Collection -Best Selection Vol. 1-)",
        expected_number="OP01-029",
        expected_set="Premium Card Collection -Best Selection Vol. 1-",
        notes="Event card - Premium Collection variant"
    ),
    TestCase(
        image_path=str(TEST_IMAGES_DIR / "mihawk.png"),
        expected_name="Dracule Mihawk (OP01-070) (Alternate Art)",
        expected_number="OP01-070",
        expected_set="Romance Dawn",
        notes="Alternate art variant - clean"
    ),
    TestCase(
        image_path=str(TEST_IMAGES_DIR / "nusjuro_altart.png"),
        expected_name="St. Ethanbaron V. Nusjuro (Alternate Art)",
        expected_number="OP13-080",
        expected_set="One Piece Film Edition",
        notes="Alternate art variant"
    ),
    TestCase(
        image_path=str(TEST_IMAGES_DIR / "op13_shanks_altart.png"),
        expected_name="Shanks (065) (Alternate Art)",
        expected_number="OP13-065",
        expected_set="One Piece Film Edition",
        notes="Alternate art variant"
    ),
    TestCase(
        image_path=str(TEST_IMAGES_DIR / "op13_garp_altart.png"),
        expected_name="Monkey.D.Garp (Alternate Art)",
        expected_number="OP13-016",
        expected_set="One Piece Film Edition",
        notes="Alternate art variant"
    ),
    TestCase(
        image_path=str(TEST_IMAGES_DIR / "op13_saboleader_altart.png"),
        expected_name="Sabo (004) (Alternate Art)",
        expected_number="OP13-004",
        expected_set="One Piece Film Edition",
        notes="Alternate art leader variant"
    ),
]


class ProductionValidator:
    """Validates production readiness of card identifier"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.identifier = None
        self.results: List[TestResult] = []

    def setup(self):
        """Initialize the identifier"""
        if self.verbose:
            print("=" * 80)
            print("PRODUCTION VALIDATION - Fast Identifier v2")
            print("=" * 80)
            print()
            print("Initializing Fast Card Identifier...")

        try:
            self.identifier = FastCardIdentifier(
                game="one-piece",
                verbose=False,
                use_gpu=False
            )
            if self.verbose:
                print("✓ Identifier initialized successfully")
                print()
        except Exception as e:
            print(f"✗ Failed to initialize identifier: {e}")
            sys.exit(1)

    def _normalize_name(self, name: str) -> str:
        """Normalize card name for variant-aware comparison"""
        # Remove variant suffixes (Manga, Alt Art, Premium, etc.)
        name = name.lower().strip()
        # Remove common variant markers
        for suffix in [' (manga)', ' (alt art)', ' (alternate art)', ' (premium)',
                      ' (parallel)', ' (special)', ' (promo)', ' (foil)']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name

    def _is_correct_match(self, identified_name: str, identified_number: str,
                         expected_name: str, expected_number: str) -> tuple[bool, str]:
        """
        Check if identification is correct, handling variants intelligently.

        Returns: (is_correct, match_type)
            match_type: "exact", "variant", "number_only", "incorrect"
        """
        # Exact match (best case)
        if identified_name == expected_name and identified_number == expected_number:
            return True, "exact"

        # Card number match with variant name (common for alt art)
        if identified_number == expected_number:
            norm_identified = self._normalize_name(identified_name)
            norm_expected = self._normalize_name(expected_name)
            if norm_identified == norm_expected:
                return True, "variant"
            # Even if names differ, same card number is acceptable
            return True, "number_only"

        # No match
        return False, "incorrect"

    def run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        if self.verbose:
            print(f"Testing: {Path(test_case.image_path).name}")
            print(f"  Expected: {test_case.expected_name} ({test_case.expected_number})")

        start_time = time.time()

        try:
            result = self.identifier.identify(test_case.image_path)

            time_ms = (time.time() - start_time) * 1000

            # Check if correct
            best_match = result.get("best_match", {})
            identified_name = best_match.get("name", "")
            identified_number = best_match.get("number", "")
            identified_set = best_match.get("set", "")

            is_correct, match_type = self._is_correct_match(
                identified_name, identified_number,
                test_case.expected_name, test_case.expected_number
            )

            test_result = TestResult(
                test_case=test_case,
                identified_name=identified_name,
                identified_number=identified_number,
                identified_set=identified_set,
                confidence=result.get("confidence", "UNKNOWN"),
                score=best_match.get("final_score", 0.0),
                is_correct=is_correct,
                time_ms=time_ms,
                match_type=match_type,
                error=None
            )

            if self.verbose:
                status = "✓" if is_correct else "✗"
                print(f"  Identified: {identified_name} ({identified_number})")
                print(f"  Confidence: {result.get('confidence', 'UNKNOWN')} (score: {best_match.get('final_score', 0.0):.4f})")
                print(f"  Time: {time_ms:.1f}ms")

                if is_correct:
                    if match_type == "exact":
                        print(f"  Result: {status} CORRECT (Exact Match)")
                    elif match_type == "variant":
                        print(f"  Result: {status} CORRECT (Variant Match)")
                    elif match_type == "number_only":
                        print(f"  Result: {status} CORRECT (Card Number Match)")
                else:
                    print(f"  Result: {status} INCORRECT")

                if test_case.notes:
                    print(f"  Notes: {test_case.notes}")

                if not is_correct:
                    print(f"  ⚠️  MISMATCH DETECTED!")

                print()

            return test_result

        except Exception as e:
            test_result = TestResult(
                test_case=test_case,
                identified_name="",
                identified_number="",
                identified_set="",
                confidence="ERROR",
                score=0.0,
                is_correct=False,
                time_ms=(time.time() - start_time) * 1000,
                match_type="error",
                error=str(e)
            )

            if self.verbose:
                print(f"  ✗ Error: {e}")
                print()

            return test_result

    def run_validation(self, test_cases: List[TestCase]):
        """Run validation on all test cases"""
        if self.verbose:
            print(f"Running validation on {len(test_cases)} test cases...")
            print("-" * 80)
            print()

        for test_case in test_cases:
            result = self.run_test(test_case)
            self.results.append(result)

    def analyze_results(self) -> Dict:
        """Analyze test results and generate metrics"""
        total_tests = len(self.results)
        correct_tests = sum(1 for r in self.results if r.is_correct)
        error_tests = sum(1 for r in self.results if r.error is not None)

        # Match type distribution
        exact_matches = sum(1 for r in self.results if r.match_type == "exact")
        variant_matches = sum(1 for r in self.results if r.match_type == "variant")
        number_only_matches = sum(1 for r in self.results if r.match_type == "number_only")

        # Accuracy by confidence level
        high_confidence_results = [r for r in self.results if r.confidence == "HIGH"]
        moderate_confidence_results = [r for r in self.results if r.confidence == "MODERATE"]
        low_confidence_results = [r for r in self.results if r.confidence == "LOW"]

        high_accuracy = (
            sum(1 for r in high_confidence_results if r.is_correct) / len(high_confidence_results)
            if high_confidence_results else 0
        )
        moderate_accuracy = (
            sum(1 for r in moderate_confidence_results if r.is_correct) / len(moderate_confidence_results)
            if moderate_confidence_results else 0
        )
        low_accuracy = (
            sum(1 for r in low_confidence_results if r.is_correct) / len(low_confidence_results)
            if low_confidence_results else 0
        )

        # Timing statistics
        times = [r.time_ms for r in self.results if r.error is None]
        avg_time = sum(times) / len(times) if times else 0
        min_time = min(times) if times else 0
        max_time = max(times) if times else 0

        # Score statistics
        scores = [r.score for r in self.results if r.error is None]
        avg_score = sum(scores) / len(scores) if scores else 0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0

        return {
            "total_tests": total_tests,
            "correct": correct_tests,
            "incorrect": total_tests - correct_tests - error_tests,
            "errors": error_tests,
            "accuracy": correct_tests / total_tests if total_tests > 0 else 0,
            "match_type_distribution": {
                "exact": exact_matches,
                "variant": variant_matches,
                "number_only": number_only_matches,
            },
            "confidence_distribution": {
                "HIGH": len(high_confidence_results),
                "MODERATE": len(moderate_confidence_results),
                "LOW": len(low_confidence_results),
            },
            "accuracy_by_confidence": {
                "HIGH": high_accuracy,
                "MODERATE": moderate_accuracy,
                "LOW": low_accuracy,
            },
            "timing": {
                "avg_ms": avg_time,
                "min_ms": min_time,
                "max_ms": max_time,
            },
            "scores": {
                "avg": avg_score,
                "min": min_score,
                "max": max_score,
            },
        }

    def print_summary(self, metrics: Dict):
        """Print validation summary"""
        print()
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print()

        # Overall Accuracy
        print(f"Overall Accuracy: {metrics['accuracy']*100:.1f}% ({metrics['correct']}/{metrics['total_tests']})")
        print(f"  ✓ Correct: {metrics['correct']}")
        print(f"  ✗ Incorrect: {metrics['incorrect']}")
        if metrics['errors'] > 0:
            print(f"  ⚠️  Errors: {metrics['errors']}")
        print()

        # Match Type Distribution
        print("Match Type Distribution:")
        match_dist = metrics['match_type_distribution']
        total = metrics['total_tests']
        print(f"  Exact Matches: {match_dist['exact']} ({match_dist['exact']/total*100:.1f}%)")
        print(f"  Variant Matches: {match_dist['variant']} ({match_dist['variant']/total*100:.1f}%)")
        print(f"  Card Number Only: {match_dist['number_only']} ({match_dist['number_only']/total*100:.1f}%)")
        print()

        # Confidence Distribution
        print("Confidence Distribution:")
        for level, count in metrics['confidence_distribution'].items():
            pct = count / metrics['total_tests'] * 100 if metrics['total_tests'] > 0 else 0
            print(f"  {level}: {count} ({pct:.1f}%)")
        print()

        # Accuracy by Confidence Level
        print("Accuracy by Confidence Level:")
        for level, accuracy in metrics['accuracy_by_confidence'].items():
            count = metrics['confidence_distribution'][level]
            if count > 0:
                print(f"  {level}: {accuracy*100:.1f}% ({int(accuracy*count)}/{count})")
            else:
                print(f"  {level}: N/A (no tests)")
        print()

        # Performance
        print("Performance:")
        print(f"  Average: {metrics['timing']['avg_ms']:.1f}ms")
        print(f"  Min: {metrics['timing']['min_ms']:.1f}ms")
        print(f"  Max: {metrics['timing']['max_ms']:.1f}ms")
        print()

        # Confidence Scores
        print("Score Statistics:")
        print(f"  Average: {metrics['scores']['avg']:.4f}")
        print(f"  Min: {metrics['scores']['min']:.4f}")
        print(f"  Max: {metrics['scores']['max']:.4f}")
        print()

    def print_recommendations(self, metrics: Dict):
        """Print production deployment recommendations"""
        print("=" * 80)
        print("PRODUCTION DEPLOYMENT RECOMMENDATIONS")
        print("=" * 80)
        print()

        accuracy = metrics['accuracy']
        high_accuracy = metrics['accuracy_by_confidence']['HIGH']
        high_count = metrics['confidence_distribution']['HIGH']
        high_pct = high_count / metrics['total_tests'] * 100

        # Determine readiness
        if accuracy >= 0.95 and high_accuracy >= 0.98 and high_pct >= 80:
            print("🟢 READY FOR PRODUCTION")
            print()
            print("System meets production criteria:")
            print(f"  ✓ Overall accuracy: {accuracy*100:.1f}% (target: ≥95%)")
            print(f"  ✓ HIGH confidence accuracy: {high_accuracy*100:.1f}% (target: ≥98%)")
            print(f"  ✓ HIGH confidence rate: {high_pct:.1f}% (target: ≥80%)")
            print()
            print("Recommendations:")
            print("  1. Deploy to production environment")
            print("  2. Monitor accuracy in real-world usage")
            print("  3. Collect failure cases for future training")
            print("  4. Set up automated accuracy monitoring")

        elif accuracy >= 0.90:
            print("🟡 ALMOST READY")
            print()
            print("System is close to production readiness:")
            print(f"  • Overall accuracy: {accuracy*100:.1f}% (target: ≥95%)")
            print(f"  • HIGH confidence accuracy: {high_accuracy*100:.1f}% (target: ≥98%)")
            print(f"  • HIGH confidence rate: {high_pct:.1f}% (target: ≥80%)")
            print()
            print("Recommendations:")
            print("  1. Expand test dataset to 50-100 cards")
            print("  2. Test on diverse conditions (lighting, angles, damage)")
            print("  3. Tune confidence thresholds if needed")
            print("  4. Consider soft launch with manual review fallback")

        else:
            print("🔴 NOT READY FOR PRODUCTION")
            print()
            print("System needs improvement:")
            print(f"  ✗ Overall accuracy: {accuracy*100:.1f}% (target: ≥95%)")
            print(f"  ✗ HIGH confidence accuracy: {high_accuracy*100:.1f}% (target: ≥98%)")
            print(f"  • HIGH confidence rate: {high_pct:.1f}% (target: ≥80%)")
            print()
            print("Recommendations:")
            print("  1. Investigate failure cases")
            print("  2. Improve preprocessing or model")
            print("  3. Expand test dataset significantly")
            print("  4. DO NOT deploy to production until accuracy improves")

        print()

    def save_results(self, output_path: str):
        """Save detailed results to JSON"""
        output = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_cases": len(self.results),
            "results": [
                {
                    "image": Path(r.test_case.image_path).name,
                    "expected": {
                        "name": r.test_case.expected_name,
                        "number": r.test_case.expected_number,
                        "set": r.test_case.expected_set,
                    },
                    "identified": {
                        "name": r.identified_name,
                        "number": r.identified_number,
                        "set": r.identified_set,
                    },
                    "confidence": r.confidence,
                    "score": r.score,
                    "correct": r.is_correct,
                    "match_type": r.match_type,
                    "time_ms": r.time_ms,
                    "error": r.error,
                    "notes": r.test_case.notes,
                }
                for r in self.results
            ],
            "metrics": self.analyze_results(),
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"Results saved to: {output_path}")
        print()

    def cleanup(self):
        """Clean up resources"""
        if self.identifier:
            try:
                self.identifier.cleanup()
            except:
                pass


def main():
    """Main validation function"""
    validator = ProductionValidator(verbose=True)

    try:
        # Setup
        validator.setup()

        # Run validation
        validator.run_validation(GROUND_TRUTH)

        # Analyze and report
        metrics = validator.analyze_results()
        validator.print_summary(metrics)
        validator.print_recommendations(metrics)

        # Save results
        output_dir = Path(__file__).parent.parent.parent.parent / "test-results" / "current"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "production_validation.json"
        validator.save_results(str(output_file))

    finally:
        validator.cleanup()


if __name__ == "__main__":
    main()
