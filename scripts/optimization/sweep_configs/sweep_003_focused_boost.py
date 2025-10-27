#!/usr/bin/env python3
"""
Sweep #003: Focused High-Impact Optimization
Target: Fix the 3 failures (bonney, radicalbeam, sanji)

Strategy: Multi-pronged approach based on root cause analysis
- Increase top-K to ensure correct card is in candidates
- Boost contrast for dark/angled images
- Lower HIGH threshold to boost confidence rate

Expected Impact: +10-30% accuracy (7→8 or 9 correct out of 10)
"""

# Baseline run ID
BASELINE_RUN_ID = "run_1761580678_baseline_1761580664"

# Highly focused parameter ranges
PARAM_RANGES = {
    # CRITICAL: Retrieve more candidates (correct card may be ranked 50-100)
    "faiss_top_k": [75, 100, 150],  # Baseline: 50

    # IMPORTANT: Boost contrast for dark/angled images
    "dinov2_contrast_alpha": [1.10, 1.15, 1.20],  # Baseline: 1.05

    # MODERATE: Lower threshold to boost HIGH conf rate (currently 60%→80%+)
    "threshold_high": [0.60, 0.62, 0.65],  # Baseline: 0.65
}

# 3 × 3 × 3 = 27 configs (manageable, focused)
MAX_CONFIGS = 27

NOTES = "Sweep #003: Focused optimization - top-K + contrast + thresholds"
TAGS = ["sweep_003", "focused", "high_impact"]

if __name__ == "__main__":
    print("Sweep #003: Focused High-Impact Optimization")
    print(f"Baseline: {BASELINE_RUN_ID}")
    print(f"Parameters: {list(PARAM_RANGES.keys())}")
    print(f"Expected configs: {MAX_CONFIGS}")
    print(f"\nTarget: Fix 3 failures (bonney, radicalbeam, sanji)")
    print(f"Strategy: More candidates + better contrast + lower threshold")
    print(f"Expected impact: 70% → 80-90% accuracy")
