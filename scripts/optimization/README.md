# TCG Card Identification System - Optimization Framework

A systematic, production-grade optimization framework for finding the optimal configuration of the TCG card identification system.

## 🎯 Overview

This framework provides:
- **Benchmark Framework**: Comprehensive testing with accuracy, speed, and robustness metrics
- **Configuration Management**: Versioned configs with inheritance and parameter sweeps
- **Experiment Tracking**: SQLite database tracking all experiments with full provenance
- **Analysis & Reporting**: Automated reports with statistical comparisons
- **Optimization Orchestrator**: Coordinates the entire optimization workflow

## 📁 Structure

```
scripts/optimization/
├── benchmark/
│   └── framework.py          # Test harness, metrics calculator, comparison engine
├── config/
│   ├── system.py              # Config management, versioning, parameter sweeps
│   └── configs/               # Stored configurations (auto-created)
├── experiments/
│   ├── tracker.py             # Experiment tracking, leaderboard, provenance
│   └── experiments.db         # SQLite database (auto-created)
├── analysis/
│   ├── reporter.py            # Report generation, visualization
│   └── reports/               # Generated reports (auto-created)
├── run_optimization.py        # Main orchestrator
└── README.md                  # This file
```

## 🚀 Quick Start

### Step 1: Establish Baseline

```bash
cd scripts/optimization
python run_optimization.py baseline \
  --test-dir ../../test-images/one-piece \
  --ground-truth ../../test-images/one-piece/ground_truth.json
```

This will:
- Create baseline configuration from current system
- Run comprehensive benchmark
- Save results to database
- Output baseline run ID (SAVE THIS!)

**Example output:**
```
✅ Baseline run ID: run_1730000000_baseline_1730000000
   Save this ID for future comparisons!
```

### Step 2: Run Parameter Sweep

```bash
python run_optimization.py sweep \
  --baseline-run run_1730000000_baseline_1730000000 \
  --test-dir ../../test-images/one-piece \
  --ground-truth ../../test-images/one-piece/ground_truth.json
```

This will:
- Generate configurations with different parameter values
- Run experiments for each configuration
- Track all results in database

### Step 3: View Leaderboard

```bash
python run_optimization.py leaderboard
```

Shows top configurations ranked by accuracy.

### Step 4: Generate Report

```bash
python run_optimization.py report \
  --baseline-run run_1730000000_baseline_1730000000
```

Generates comprehensive markdown report with:
- Executive summary
- Best configuration details
- Optimization progress
- Key findings and recommendations

## 🔧 Advanced Usage

### Custom Parameter Sweep

Edit `run_optimization.py` line 309 to customize parameters:

```python
param_ranges = {
    "dinov2_model": ["facebook/dinov2-small", "facebook/dinov2-base"],
    "orb_nfeatures": [500, 1000, 2000],
    "orb_verify_top_n": [5, 10, 20],
    "threshold_high": [0.60, 0.65, 0.70],
    "fusion_visual_weight_high_geom": [0.60, 0.70, 0.80]
}
```

### Using as Library

```python
from optimization.run_optimization import OptimizationOrchestrator

# Initialize
orchestrator = OptimizationOrchestrator(
    test_dir="test-images/one-piece",
    ground_truth_file="test-images/one-piece/ground_truth.json"
)

# Establish baseline
baseline_run_id = orchestrator.establish_baseline()

# Run custom experiments
from optimization.config.system import ConfigurationManager

config_manager = ConfigurationManager()
baseline_config = config_manager.load_config(baseline_run_id)

# Create variant
faster_config = config_manager.create_variant(
    parent_config=baseline_config,
    name="Faster ORB",
    description="Reduce ORB features for speed",
    param_changes={
        "orb_nfeatures": 500,
        "orb_verify_top_n": 5
    },
    tags=["speed-optimization"]
)

# Test it
run_id = orchestrator.run_single_experiment(
    config=faster_config,
    notes="Testing speed optimization"
)

# Generate report
orchestrator.generate_final_report(baseline_run_id)
orchestrator.close()
```

### Accessing Results Database

```python
from optimization.experiments.tracker import ExperimentTracker

tracker = ExperimentTracker()

# Get leaderboard
leaderboard = tracker.get_leaderboard(metric="top_1_accuracy", limit=10)

# Get experiment details
experiment = tracker.get_experiment("run_1730000000_...")

# Compare two experiments
comparison = tracker.compare_experiments(run_id_a, run_id_b)

# Find problematic images
problematic = tracker.get_problematic_images(min_experiments=3, max_accuracy=0.5)

tracker.close()
```

## 📊 Metrics Tracked

### Accuracy Metrics
- **Top-1 Accuracy**: % of images correctly identified (rank 1)
- **Top-3 Accuracy**: % correct in top 3 candidates
- **Top-5 Accuracy**: % correct in top 5 candidates
- **Mean Reciprocal Rank**: Average of 1/rank for all correct identifications

### Performance Metrics
- **Average Time**: Mean identification time per image
- **Min/Max/Median Time**: Time distribution
- **Throughput**: Images processed per second

### Confidence Metrics
- **HIGH Confidence Rate**: % of images with HIGH confidence
- **MODERATE Confidence Rate**: % with MODERATE confidence
- **LOW Confidence Rate**: % with LOW confidence

### Score Metrics
- **Average Final Score**: Mean final confidence score
- **Average Visual Score**: Mean DINOv2 similarity
- **Average Geometric Score**: Mean ORB matching score

### Robustness Metrics
- **Accuracy by Tag**: Performance on specific image types
  - `watermarked`: Images with watermarks
  - `angled`: Off-axis captures
  - `poor_lighting`: Low light conditions
  - `phone_photo`: Phone camera captures
  - `foil`: Foil/parallel cards

### Error Analysis
- **False Positives**: HIGH confidence but wrong
- **False Negatives**: Correct card not in top-5
- **Confusion Pairs**: Most common misidentifications
- **Problematic Cards**: Cards with <80% accuracy

## 🎯 Configuration Parameters

The system tracks 40+ parameters across categories:

### DINOv2 (Visual Embeddings)
- `dinov2_model`: Model size (small/base/large)
- `dinov2_preprocessing_bilateral`: Enable bilateral filter
- `dinov2_preprocessing_contrast`: Enable contrast enhancement
- `dinov2_bilateral_d`: Filter diameter
- `dinov2_bilateral_sigma_color`: Color sigma
- `dinov2_bilateral_sigma_space`: Space sigma
- `dinov2_contrast_alpha`: Contrast multiplier
- `dinov2_contrast_beta`: Brightness offset

### FAISS (Vector Search)
- `faiss_index_type`: Index type (Flat/IVFFlat/HNSW)
- `faiss_top_k`: Number of candidates to retrieve

### ORB (Geometric Verification)
- `orb_enabled`: Enable ORB matching
- `orb_nfeatures`: Number of features to detect
- `orb_scaleFactor`: Pyramid scale factor
- `orb_nlevels`: Pyramid levels
- `orb_edgeThreshold`: Edge detection threshold
- `orb_lowe_ratio`: Lowe's ratio test threshold
- `orb_verify_top_n`: How many candidates to verify
- `orb_early_stop_visual`: Visual threshold for early stop
- `orb_early_stop_geometric`: Geometric threshold for early stop

### SIFT/AKAZE (Cascade Matching)
- `sift_enabled`: Enable SIFT in cascade
- `sift_nfeatures`: Number of SIFT features
- `sift_cascade_threshold`: Threshold to skip ORB
- `akaze_enabled`: Enable AKAZE fallback
- `akaze_cascade_threshold`: Threshold to try AKAZE

### Score Fusion
- `fusion_strategy`: fixed/dynamic/learned
- `fusion_visual_weight_high_geom`: Visual weight when geom > 0.15
- `fusion_geometric_weight_high_geom`: Geometric weight when geom > 0.15
- `fusion_visual_weight_mid_geom`: Visual weight when geom 0.05-0.15
- `fusion_geometric_weight_mid_geom`: Geometric weight when geom 0.05-0.15
- `fusion_visual_weight_low_geom`: Visual weight when geom < 0.05
- `fusion_geometric_weight_low_geom`: Geometric weight when geom < 0.05

### Confidence Thresholds
- `threshold_high`: High confidence threshold
- `threshold_moderate`: Moderate confidence threshold
- `threshold_margin`: Margin for confidence boost

### OCR
- `ocr_enabled`: Enable card number extraction
- `ocr_hard_filter_enabled`: Filter to matching cards only
- `ocr_hard_filter_confidence`: Confidence threshold for filter
- `ocr_hard_filter_min_matches`: Minimum matches for filter
- `ocr_card_number_boost`: Score boost for number match

## 📈 Optimization Strategies

### 1. Grid Search
Test all combinations of parameter values:
```python
param_ranges = {
    "orb_nfeatures": [500, 1000, 2000],
    "threshold_high": [0.60, 0.65, 0.70]
}
# Creates 3 × 3 = 9 configurations
```

### 2. Sequential Optimization
Optimize one component at a time:
1. Optimize DINOv2 preprocessing
2. Optimize FAISS retrieval
3. Optimize ORB verification
4. Optimize score fusion
5. Optimize confidence thresholds

### 3. Ablation Studies
Test impact of individual components:
```python
# Test without ORB
config_no_orb = create_variant(baseline, {"orb_enabled": False})

# Test without OCR
config_no_ocr = create_variant(baseline, {"ocr_enabled": False})

# Compare to see which contributes more
```

### 4. A/B Testing
Compare specific hypotheses:
```python
# Hypothesis: More ORB features improves accuracy
config_a = create_variant(baseline, {"orb_nfeatures": 500})
config_b = create_variant(baseline, {"orb_nfeatures": 2000})

# Run both and compare
```

## 🔍 Interpreting Results

### Good Results
- Top-1 accuracy > 90%
- HIGH confidence rate > 60%
- Average time < 500ms
- False positive rate < 5%

### Red Flags
- Top-1 accuracy dropping
- HIGH confidence rate dropping
- Speed increasing significantly
- Many false positives

### Common Patterns
- **More ORB features**: ↑ accuracy, ↑ time
- **Higher thresholds**: ↓ HIGH conf rate, ↑ precision
- **More candidates (top_k)**: ↑ accuracy (small), ↑ time
- **Geometric verification**: ↑ accuracy on watermarked, ↑ time

## 🚨 Troubleshooting

### "No test cases with ground truth found"
- Check ground_truth.json file exists
- Verify JSON format matches schema
- Ensure image names match exactly

### "Configuration not found"
- Use correct run_id from baseline step
- Check config was saved (look in config/configs/)

### "Module not found" errors
- Ensure you're in the right directory
- Check Python path includes parent directories
- Verify all dependencies installed

### Slow experiments
- Reduce number of test images
- Decrease max_configs parameter
- Use faster parameter ranges

## 📝 Best Practices

1. **Always establish baseline first**
   - Provides reference point
   - Validates test setup

2. **Start with small sweeps**
   - Test 2-3 values per parameter
   - Expand based on results

3. **Track everything**
   - Add descriptive notes to experiments
   - Use tags for organization
   - Document hypotheses

4. **Version control configs**
   - Configs auto-saved to git
   - Commit after major findings

5. **Generate reports regularly**
   - After each sweep
   - Before changing strategy

6. **Monitor problematic images**
   - Identify consistent failures
   - May need better ground truth
   - Could indicate edge cases

## 🎓 Example Workflow

```bash
# 1. Establish baseline
python run_optimization.py baseline \
  --test-dir ../../test-images/one-piece \
  --ground-truth ../../test-images/one-piece/ground_truth.json

# Save the baseline_run_id from output
BASELINE_RUN="run_1730000000_baseline_1730000000"

# 2. Quick sweep to find promising directions
# Edit run_optimization.py to test 2-3 values per param
python run_optimization.py sweep --baseline-run $BASELINE_RUN

# 3. Check leaderboard
python run_optimization.py leaderboard

# 4. Refine based on results
# Edit param_ranges to explore promising regions
python run_optimization.py sweep --baseline-run $BASELINE_RUN

# 5. Generate final report
python run_optimization.py report --baseline-run $BASELINE_RUN

# 6. Deploy best configuration
# Extract best config from database
# Apply to production system
```

## 🤝 Contributing

To add new parameters:
1. Add to `ConfigParameter` definitions in `config/system.py`
2. Update `create_baseline_config()` with current value
3. Document in this README

To add new metrics:
1. Add to `BenchmarkMetrics` in `benchmark/framework.py`
2. Update `_calculate_metrics()` to compute it
3. Add to database schema in `experiments/tracker.py`

## 📚 References

- **Benchmark Framework**: `benchmark/framework.py`
- **Config Management**: `config/system.py`
- **Experiment Tracking**: `experiments/tracker.py`
- **Analysis & Reporting**: `analysis/reporter.py`
- **Main Orchestrator**: `run_optimization.py`

## 🐛 Known Issues

1. **Config application not fully implemented**: Current system runs with production defaults. Need to implement config → identifier parameter mapping.

2. **Visualization uses ASCII**: For production, integrate matplotlib/plotly for proper charts.

3. **No parallel execution**: Experiments run sequentially. Could parallelize for speed.

4. **Limited statistical tests**: Only basic t-tests. Could add more rigorous analysis.

## 🔮 Future Enhancements

- [ ] Implement config → identifier parameter mapping
- [ ] Add Bayesian optimization for smart parameter search
- [ ] Parallel experiment execution
- [ ] Real-time progress visualization (web dashboard)
- [ ] Export to W&B / MLflow for tracking
- [ ] Automated A/B testing in production
- [ ] Cross-validation support
- [ ] Multi-TCG optimization

---

Built with ❤️ for production ML systems
