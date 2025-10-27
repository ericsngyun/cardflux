#!/usr/bin/env python3
"""
Sweep #002: Preprocessing Enhancement
Target: Fix angled/poor lighting images (currently 0% accuracy)

Strategy: Optimize DINOv2 preprocessing for challenging images
Expected Impact: +20-30% on challenging images through better visual embeddings
"""

# Baseline run ID to compare against
BASELINE_RUN_ID = "run_1761580678_baseline_1761580664"

# Parameter ranges to test
PARAM_RANGES = {
    # Increase bilateral filter strength for noise reduction
    "dinov2_bilateral_sigma_color": [30, 50, 70, 90],  # Baseline: 50

    # Increase contrast enhancement for dark images
    "dinov2_contrast_alpha": [1.00, 1.05, 1.10, 1.15, 1.20],  # Baseline: 1.05
}

# Expected configurations: 4 × 5 = 20 experiments
MAX_CONFIGS = 20

NOTES = "Sweep #002: Optimize preprocessing for angled/poor lighting images"
TAGS = ["sweep_002", "preprocessing_boost", "challenging_images"]

if __name__ == "__main__":
    print("Sweep #002: Preprocessing Enhancement")
    print(f"Baseline: {BASELINE_RUN_ID}")
    print(f"Parameters: {list(PARAM_RANGES.keys())}")
    print(f"Expected configs: {MAX_CONFIGS}")
    print(f"\nTarget: Fix angled/poor lighting (0% → 70%+)")
    print(f"Strategy: Stronger noise reduction + contrast boost")
    print(f"Expected impact: +10-20% overall accuracy")
