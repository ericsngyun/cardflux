#!/usr/bin/env python3
"""
Deep architectural analysis of the hybrid card identification system.
Identifies faults, bottlenecks, and improvement opportunities.
"""
import json
from pathlib import Path
from typing import Dict, List

# Test results
TEST_RESULTS = {
    "bege.png": {
        "correct_card": "Capone\"Gang\"Bege",
        "correct_id": "ST02-004",
        "actual": "Capone\"Gang\"Bege",
        "confidence": "LOW",
        "visual_score": 0.8936,
        "geometric_score": 0.3978,
        "final_score": 0.7250,
        "time_ms": 1918,
        "issues": [
            "LOW confidence despite correct match",
            "OCR extracted '1000' instead of card name",
            "Geometric score only 0.39 (weak match)",
            "Below AUTO_ACCEPT threshold (0.75)"
        ]
    },
    "blackbeard.png": {
        "correct_card": "Marshall.D.Teach",
        "correct_id": "OP09-093",
        "actual": "Marshall.D.Teach (093) (Manga)",
        "confidence": "LOW",
        "visual_score": 0.7696,
        "geometric_score": 0.1607,
        "final_score": 0.5789,
        "time_ms": 676,
        "issues": [
            "LOW confidence despite correct match",
            "OCR completely failed (extracted nothing)",
            "Very weak geometric score (0.16)",
            "Low visual score (0.77) - watermark interference",
            "Final score far below threshold"
        ]
    },
    "blackbeard-db.jpg": {
        "correct_card": "Marshall.D.Teach (093) (Manga)",
        "correct_id": "OP09-093",
        "actual": "Marshall.D.Teach (093) (Manga)",
        "confidence": "HIGH",
        "visual_score": 1.0,
        "geometric_score": 1.0,
        "final_score": 0.9517,
        "time_ms": 1868,
        "issues": [
            "Perfect match but slow (1.8s)",
            "OCR extracted '12000' (ATK value, not name)"
        ]
    },
    "yellow_event.png": {
        "correct_card": "You're the One Who Should Disappear",
        "correct_id": "OP06-115",
        "actual": "You're the One Who Should Disappear",
        "confidence": "LOW",
        "visual_score": 0.7260,
        "geometric_score": 0.1376,
        "final_score": 0.5426,
        "time_ms": 1548,
        "issues": [
            "LOW confidence despite correct match",
            "OCR extracted 'DSAPPEAR' (partial/corrupted)",
            "Weak geometric match (0.14)",
            "Visual score marginal (0.73)",
            "Final score well below threshold"
        ]
    }
}


class SystemAnalyzer:
    """Analyzes the hybrid identification system for faults and improvements."""

    def __init__(self):
        self.faults = []
        self.bottlenecks = []
        self.improvements = []

    def analyze(self) -> Dict:
        """Perform comprehensive system analysis."""
        print("=" * 80)
        print("HYBRID IDENTIFICATION SYSTEM - DEEP ARCHITECTURAL ANALYSIS")
        print("=" * 80)

        self._analyze_accuracy()
        self._analyze_confidence_calibration()
        self._analyze_component_effectiveness()
        self._analyze_thresholds()
        self._analyze_preprocessing()
        self._analyze_performance()
        self._analyze_architecture()

        return {
            "faults": self.faults,
            "bottlenecks": self.bottlenecks,
            "improvements": self.improvements
        }

    def _analyze_accuracy(self):
        """Analyze prediction accuracy."""
        print("\n[1] ACCURACY ANALYSIS")
        print("-" * 80)

        correct = sum(1 for r in TEST_RESULTS.values() if r['correct_card'] in r['actual'])
        total = len(TEST_RESULTS)
        accuracy = correct / total * 100

        print(f"  Accuracy: {correct}/{total} ({accuracy:.1f}%)")

        if accuracy < 100:
            self.faults.append({
                "severity": "HIGH",
                "category": "Accuracy",
                "issue": f"System only achieving {accuracy:.1f}% accuracy",
                "impact": "Production system needs 99%+ accuracy"
            })

        # Analyze confidence distribution
        high_conf = sum(1 for r in TEST_RESULTS.values() if r['confidence'] == 'HIGH')
        low_conf = sum(1 for r in TEST_RESULTS.values() if r['confidence'] == 'LOW')

        print(f"  Confidence: {high_conf} HIGH, {low_conf} LOW")
        print(f"  Problem: {low_conf}/{total} correct matches have LOW confidence")

        self.faults.append({
            "severity": "CRITICAL",
            "category": "Confidence Calibration",
            "issue": "75% of correct matches flagged as LOW confidence",
            "root_cause": "Thresholds too aggressive for real-world images",
            "impact": "Users won't trust system, manual verification needed"
        })

    def _analyze_confidence_calibration(self):
        """Analyze confidence threshold calibration."""
        print("\n[2] CONFIDENCE CALIBRATION ANALYSIS")
        print("-" * 80)

        # Current thresholds
        THRESHOLD_AUTO_ACCEPT = 0.75
        THRESHOLD_MARGIN = 0.15

        print(f"  Current AUTO_ACCEPT threshold: {THRESHOLD_AUTO_ACCEPT}")
        print(f"  Current MARGIN threshold: {THRESHOLD_MARGIN}")
        print()

        # Analyze how many correct matches would pass at different thresholds
        scores = [r['final_score'] for r in TEST_RESULTS.values()]

        print("  Score distribution (all correct matches):")
        for name, result in TEST_RESULTS.items():
            status = "[PASS]" if result['final_score'] >= THRESHOLD_AUTO_ACCEPT else "[FAIL]"
            print(f"    {name:20s} {result['final_score']:.4f} {status}")

        print()
        print("  FAULT: Threshold set too high for real-world conditions!")
        print(f"    - Only {sum(1 for s in scores if s >= THRESHOLD_AUTO_ACCEPT)}/4 correct matches pass")
        print(f"    - Median score: {sorted(scores)[len(scores)//2]:.4f}")
        print(f"    - Min correct score: {min(scores):.4f}")

        self.faults.append({
            "severity": "CRITICAL",
            "category": "Threshold Calibration",
            "issue": "AUTO_ACCEPT threshold (0.75) too high for real-world images",
            "evidence": "3/4 correct matches score below threshold",
            "root_cause": "Thresholds tuned for perfect DB images, not user photos",
            "fix": "Lower to 0.55-0.60 based on empirical data"
        })

    def _analyze_component_effectiveness(self):
        """Analyze effectiveness of each component."""
        print("\n[3] COMPONENT EFFECTIVENESS ANALYSIS")
        print("-" * 80)

        # Visual component
        print("  [Visual - DINOv2] Weight: 0.70")
        visual_scores = [r['visual_score'] for r in TEST_RESULTS.values()]
        avg_visual = sum(visual_scores) / len(visual_scores)
        print(f"    Average score: {avg_visual:.4f}")
        print(f"    Range: {min(visual_scores):.4f} - {max(visual_scores):.4f}")

        if max(visual_scores) == 1.0 and min(visual_scores) < 0.8:
            print("    [!] High variance detected!")
            print("    Issue: Watermarks and photo quality heavily impact scores")
            self.faults.append({
                "severity": "HIGH",
                "category": "Visual Component",
                "issue": "DINOv2 embeddings inconsistent for watermarked/photographed cards",
                "evidence": f"Score range: {min(visual_scores):.2f} - {max(visual_scores):.2f}",
                "impact": "Same card gets different scores based on photo quality"
            })

        # OCR component
        print("\n  [OCR - EasyOCR] Weight: 0.05")
        ocr_scores = [r.get('ocr_score', 0.0) for r in TEST_RESULTS.values()]
        avg_ocr = sum(ocr_scores) / len(ocr_scores)
        print(f"    Average score: {avg_ocr:.4f}")
        print(f"    Contribution: {avg_ocr * 0.05:.4f} to final score")

        if avg_ocr < 0.1:
            print("    [!] OCR completely ineffective!")
            print("    Issues:")
            print("      - Extracts ATK values instead of card names")
            print("      - Fails on stylized event card text")
            print("      - No region-specific logic for card zones")

            self.faults.append({
                "severity": "MEDIUM",
                "category": "OCR Component",
                "issue": "OCR provides near-zero contribution to identification",
                "root_cause": "No spatial awareness - extracts wrong text regions",
                "impact": "Wasted computation with 5% weight doing nothing",
                "fix": "Either fix region extraction or reduce weight to 0%"
            })

        # Geometric component
        print("\n  [Geometric - ORB] Weight: 0.25")
        geom_scores = [r['geometric_score'] for r in TEST_RESULTS.values()]
        avg_geom = sum(geom_scores) / len(geom_scores)
        print(f"    Average score: {avg_geom:.4f}")
        print(f"    Range: {min(geom_scores):.4f} - {max(geom_scores):.4f}")

        if max(geom_scores) == 1.0 and avg_geom < 0.5:
            print("    [!] Inconsistent performance!")
            print("    Issues:")
            print("      - Works great for clean images (1.0)")
            print("      - Fails for angled/watermarked photos (0.16-0.40)")
            print("      - Only checking top 5 candidates")

            self.faults.append({
                "severity": "HIGH",
                "category": "Geometric Component",
                "issue": "ORB matching fails on real-world photo conditions",
                "root_cause": "Sensitive to rotation, watermarks, lighting changes",
                "impact": "25% weight component contributes little for user photos",
                "fix": "Use more robust features or expand candidate set"
            })

    def _analyze_thresholds(self):
        """Analyze threshold values."""
        print("\n[4] THRESHOLD ANALYSIS")
        print("-" * 80)

        # Weight analysis
        print("  Current weights:")
        print("    Visual:    0.70 (70%)")
        print("    OCR:       0.05 (5%)")
        print("    Geometric: 0.25 (25%)")
        print()

        # Calculate effective contribution
        print("  Effective contribution (avg across test set):")
        avg_contributions = {
            "visual": 0.70 * sum(r['visual_score'] for r in TEST_RESULTS.values()) / len(TEST_RESULTS),
            "ocr": 0.05 * sum(r.get('ocr_score', 0) for r in TEST_RESULTS.values()) / len(TEST_RESULTS),
            "geometric": 0.25 * sum(r['geometric_score'] for r in TEST_RESULTS.values()) / len(TEST_RESULTS)
        }

        for component, contribution in avg_contributions.items():
            print(f"    {component:10s} {contribution:.4f}")

        print()
        if avg_contributions['ocr'] < 0.01:
            print("  [!] OCR weight (5%) far exceeds actual contribution (0.1%)")
            self.improvements.append({
                "category": "Weight Optimization",
                "current": "Visual: 0.70, OCR: 0.05, Geometric: 0.25",
                "proposed": "Visual: 0.75, OCR: 0.00, Geometric: 0.25",
                "rationale": "OCR contributes nothing, redistribute to visual",
                "expected_impact": "Slight accuracy improvement, 10% faster"
            })

    def _analyze_preprocessing(self):
        """Analyze preprocessing pipeline."""
        print("\n[5] PREPROCESSING ANALYSIS")
        print("-" * 80)

        print("  Current preprocessing:")
        print("    1. Bilateral filter (d=5, sigma=50)")
        print("    2. Contrast enhancement (alpha=1.05, beta=3)")
        print("    3. Upscaling for images <400px")
        print()

        print("  Issues identified:")
        print("    [!] Preprocessing applied at query time ONLY")
        print("      - Database embeddings: Raw 600x600 images")
        print("      - Query embeddings: Filtered + enhanced")
        print("      - Result: EMBEDDING MISMATCH!")

        self.faults.append({
            "severity": "CRITICAL",
            "category": "Preprocessing Mismatch",
            "issue": "Query preprocessing != Database preprocessing",
            "root_cause": "preprocess_image() only called in get_image_embedding()",
            "impact": "Embeddings computed in different spaces, reduces accuracy",
            "fix": "Either preprocess ALL images or disable query preprocessing",
            "evidence": "Visual scores show high variance (0.77-1.0) for same card type"
        })

        print()
        print("    [!] Upscaling small images may introduce artifacts")
        print("      - Scale factor can be 2x+ for very small images")
        print("      - LANCZOS resampling can create edge artifacts")

        self.improvements.append({
            "category": "Preprocessing",
            "issue": "Aggressive upscaling may hurt accuracy",
            "fix": "Use DINOv2's native rescaling instead of manual upscale",
            "expected_impact": "More consistent embeddings"
        })

    def _analyze_performance(self):
        """Analyze performance bottlenecks."""
        print("\n[6] PERFORMANCE ANALYSIS")
        print("-" * 80)

        times = [r['time_ms'] for r in TEST_RESULTS.values()]
        avg_time = sum(times) / len(times)

        print(f"  Average identification time: {avg_time:.0f}ms")
        print(f"  Range: {min(times)}ms - {max(times)}ms")
        print()

        # Breakdown
        print("  Time breakdown (estimated):")
        print("    Model load:      ~2500ms (one-time)")
        print("    Embedding:       ~300ms (DINOv2 + preprocessing)")
        print("    FAISS search:    ~10ms (very fast)")
        print("    OCR:             ~800ms (EasyOCR is slow)")
        print("    ORB (top 5):     ~400ms (5 comparisons)")
        print("    Score fusion:    ~5ms (trivial)")
        print()

        if avg_time > 1000:
            print("  [!] Average time >1 second is too slow for real-time UX")
            self.bottlenecks.append({
                "severity": "HIGH",
                "component": "OCR Processing",
                "time": "~800ms",
                "impact": "50% of identification time",
                "fix": "Disable OCR (contributes 0%) or optimize regions"
            })

        self.bottlenecks.append({
            "severity": "MEDIUM",
            "component": "Geometric Verification",
            "time": "~400ms for 5 candidates",
            "impact": "25% of identification time",
            "optimization": "Parallelize ORB matching or reduce candidate count"
        })

        self.improvements.append({
            "category": "Performance",
            "optimization": "Skip OCR entirely",
            "expected_speedup": "~800ms (53% faster)",
            "tradeoff": "None - OCR contributes nothing currently"
        })

    def _analyze_architecture(self):
        """Analyze architectural decisions."""
        print("\n[7] ARCHITECTURAL ANALYSIS")
        print("-" * 80)

        print("  Current architecture:")
        print("    Stage 1: Visual retrieval (top 20)")
        print("    Stage 2: OCR extraction (all candidates)")
        print("    Stage 3: Geometric verification (top 5 only)")
        print("    Stage 4: Score fusion")
        print()

        print("  Issues:")
        print("    [!] Limited geometric verification")
        print("      - Only checks top 5 visual candidates")
        print("      - If correct card ranks #6-20 visually, never verified")
        print("      - Watermarks can push correct card down visual ranking")

        self.faults.append({
            "severity": "HIGH",
            "category": "Architecture",
            "issue": "Geometric verification limited to top 5 visual candidates",
            "scenario": "Watermarked cards rank low visually, never get geometric check",
            "fix": "Expand geometric verification to top 10-15 candidates",
            "tradeoff": "~2x slower geometric stage, but more robust"
        })

        print()
        print("    [!] No watermark detection/removal")
        print("      - Watermarks drastically reduce visual similarity")
        print("      - No preprocessing to detect or mask watermark regions")

        self.improvements.append({
            "category": "Preprocessing",
            "feature": "Watermark detection and masking",
            "approach": "Detect text overlay regions, mask before embedding",
            "expected_impact": "10-15% improvement in visual scores"
        })

        print()
        print("    [!] Single embedding model")
        print("      - Only using DINOv2-small")
        print("      - Could ensemble with CLIP or other models")

        self.improvements.append({
            "category": "Architecture",
            "feature": "Model ensemble",
            "approach": "Combine DINOv2 + CLIP embeddings",
            "expected_impact": "5-10% accuracy improvement",
            "tradeoff": "2x embedding time"
        })

    def print_summary(self):
        """Print executive summary."""
        print("\n" + "=" * 80)
        print("EXECUTIVE SUMMARY")
        print("=" * 80)

        print(f"\n  Total Faults Found: {len(self.faults)}")
        critical = sum(1 for f in self.faults if f['severity'] == 'CRITICAL')
        high = sum(1 for f in self.faults if f['severity'] == 'HIGH')
        medium = sum(1 for f in self.faults if f['severity'] == 'MEDIUM')

        print(f"    CRITICAL: {critical}")
        print(f"    HIGH:     {high}")
        print(f"    MEDIUM:   {medium}")

        print(f"\n  Performance Bottlenecks: {len(self.bottlenecks)}")
        print(f"  Improvement Opportunities: {len(self.improvements)}")

        print("\n  TOP PRIORITY FIXES:")
        print("    1. Lower AUTO_ACCEPT threshold from 0.75 -> 0.60")
        print("    2. Fix preprocessing mismatch (apply to DB or remove from query)")
        print("    3. Disable or fix OCR (currently useless, wastes 800ms)")
        print("    4. Expand geometric verification from top 5 -> top 10")
        print("    5. Add watermark detection/masking")

        print("\n  Expected Impact:")
        print("    - Confidence: 75% LOW -> 90%+ HIGH/MODERATE")
        print("    - Speed: 1500ms -> 700ms (2x faster)")
        print("    - Accuracy: 100% (maintain while improving confidence)")


def main():
    analyzer = SystemAnalyzer()
    results = analyzer.analyze()
    analyzer.print_summary()

    # Save analysis
    output_file = Path(__file__).parent.parent.parent / "system_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n  Full analysis saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
