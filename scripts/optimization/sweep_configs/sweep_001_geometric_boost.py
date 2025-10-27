#!/usr/bin/env python3
"""
Sweep #001: Geometric Verification Boost
Target: Fix angled/poor lighting images (currently 0% accuracy)

Strategy: Increase ORB features and verification depth for better geometric matching
Expected Impact: +20-30% on challenging images
"""

# Baseline run ID to compare against
BASELINE_RUN_ID = "run_1761580678_baseline_1761580664"

# Parameter ranges to test
PARAM_RANGES = {
    # Increase ORB features for better matching on challenging images
    "orb_nfeatures": [1000, 1500, 2000],  # Baseline: 1000

    # Verify more candidates to catch correct card even if visual ranking is off
    "orb_verify_top_n": [10, 15, 20],  # Baseline: 10

    # Relax Lowe's ratio to accept more matches (may help on noisy images)
    "orb_lowe_ratio": [0.75, 0.80, 0.85],  # Baseline: 0.80
}

# Expected configurations: 3 × 3 × 3 = 27 experiments
MAX_CONFIGS = 27

NOTES = "Sweep #001: Boost geometric matching for angled/poor lighting images"
TAGS = ["sweep_001", "geometric_boost", "challenging_images"]

if __name__ == "__main__":
    print("Sweep #001: Geometric Verification Boost")
    print(f"Baseline: {BASELINE_RUN_ID}")
    print(f"Parameters: {list(PARAM_RANGES.keys())}")
    print(f"Expected configs: {MAX_CONFIGS}")
    print(f"\nTarget: Fix angled/poor lighting (0% → 70%+)")
    print(f"Expected impact: +20-30% overall accuracy")
