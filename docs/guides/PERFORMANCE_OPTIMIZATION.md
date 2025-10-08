# Performance Optimization Guide

> **Last Updated**: 2025-10-07
> **Status**: Optimization strategies for embedding generation

## Current Performance

### Embedding Generation (5,053 cards)

| Method | Time | Speed | Notes |
|--------|------|-------|-------|
| Sequential DINOv2 | ~380s | ~13 cards/sec | Original implementation |
| Batch DINOv2 (CPU) | 380s | 13.3 cards/sec | Batch size 32, 4 workers |
| **Target** | <120s | >42 cards/sec | 3x improvement needed |

### Identification Speed

| Stage | Current | Target | Status |
|-------|---------|--------|--------|
| DINOv2 embedding | 10-15ms | <20ms | ✅ Good |
| FAISS search | 2-8ms | <10ms | ✅ Good |
| ORB verification (×10) | 10-20ms | <50ms | ✅ Good |
| **Total (without OCR)** | 732ms | <200ms | ⚠️ Need optimization |

## Why Embedding is Slow on CPU

The main bottleneck is **CPU-bound inference** with DINOv2:

1. **Model size**: DINOv2-small has 22M parameters
2. **Forward pass**: Each image requires ~75ms on CPU
3. **Batch processing helps minimally on CPU** due to limited parallelism

## Optimization Strategies

### 1. Use GPU (Recommended - 10x speedup)

**Install CUDA-enabled PyTorch:**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**Expected improvement:**
- Sequential: 380s → **40s** (9.5x faster)
- Batch processing: 380s → **25s** (15x faster with batching)
- Speed: 13 cards/sec → **200+ cards/sec**

**GPU benefits:**
- FP16 (half precision) support for 2x additional speedup
- Efficient batch processing (32-64 images at once)
- Parallel matrix operations

### 2. Use Smaller Model (2x speedup, -10% accuracy)

**DINOv2-tiny instead of DINOv2-small:**
```python
MODEL_NAME = "facebook/dinov2-tiny"  # 5M params vs 22M
```

**Trade-offs:**
- Embedding dim: 192 instead of 384
- Speed: 2x faster
- Accuracy: ~90-95% of small model performance

### 3. ONNX Runtime (1.5-2x speedup on CPU)

Convert model to ONNX format for optimized CPU inference:

```python
import onnxruntime as ort

# Export to ONNX (one-time)
torch.onnx.export(model, dummy_input, "dinov2.onnx")

# Use ONNX Runtime
session = ort.InferenceSession("dinov2.onnx",
                                providers=['CPUExecutionProvider'])
```

**Benefits:**
- Graph optimizations
- Quantization support (INT8 for 4x speedup)
- Cross-platform compatibility

### 4. Quantization (4x speedup, -5% accuracy)

Use INT8 quantization for faster CPU inference:

```python
import torch.quantization

# Quantize model
model_int8 = torch.quantization.quantize_dynamic(
    model,
    {torch.nn.Linear},
    dtype=torch.qint8
)
```

**Trade-offs:**
- Speed: 4x faster on CPU
- Memory: 4x less RAM
- Accuracy: Minimal loss (<5%)

### 5. Pre-compute and Cache (Best for production)

For production environments where cards don't change often:

1. **Pre-compute all embeddings** once (can take hours, doesn't matter)
2. **Store in database** or files
3. **Only compute embeddings for new cards**
4. **Incremental updates** when new sets release

**Implementation:**
```python
# Check if embedding exists
if card_id in existing_embeddings:
    embedding = existing_embeddings[card_id]
else:
    embedding = compute_embedding(image)
    cache[card_id] = embedding
```

## Recommended Setup by Use Case

### For Development / Testing
```bash
# Use batch processing on CPU
python services/embedder/bin/embed_onepiece_dinov2_fast.py
```
- Time: 6-7 minutes for 5k cards
- Acceptable for testing

### For Production with GPU
```bash
# Install CUDA PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Use optimized embedder
python services/embedder/bin/embed_onepiece_dinov2_fast.py
```
- Time: 25-40 seconds for 5k cards
- Run once per new set release

### For Production without GPU
```bash
# Option 1: Pre-compute embeddings on GPU machine, transfer files
# Option 2: Use ONNX + quantization
pip install onnxruntime

# Convert and use ONNX model (requires setup)
```
- Time: 2-3 minutes for 5k cards
- Good for resource-constrained environments

## Comparison: CPU vs GPU

### CPU (Current Setup)
- **Hardware**: Standard laptop/desktop CPU
- **Time**: 380 seconds for 5k cards
- **Cost**: $0 additional hardware
- **When to use**: Testing, low-volume (<10k cards)

### GPU (Recommended for Production)
- **Hardware**: NVIDIA GPU (GTX 1060 or better)
- **Time**: 25-40 seconds for 5k cards
- **Cost**: $200-500 for entry GPU
- **When to use**: Production, frequent updates, large datasets

### Cloud GPU (Alternative)
- **Service**: Google Colab, AWS EC2 GPU, Lambda Labs
- **Time**: 25-40 seconds for 5k cards
- **Cost**: $0.30-1.00 per hour
- **When to use**: Occasional batch processing, no local GPU

## Optimization Roadmap

### Phase 1: Current (Done)
- ✅ Batch processing implemented
- ✅ Multi-threaded image loading
- ✅ Pre-allocated arrays

### Phase 2: Quick Wins (Optional)
- ⏳ ONNX conversion for CPU optimization
- ⏳ Model quantization (INT8)
- ⏳ Switch to DINOv2-tiny for faster processing

### Phase 3: Production (When Scaling)
- 🔲 GPU inference setup
- 🔲 Incremental embedding updates
- 🔲 Embedding caching system
- 🔲 Multi-GPU for very large datasets

## Identification Speed Optimization

The hybrid identifier currently takes **732ms** per card. To reach <200ms:

### Bottleneck Analysis
```
Model loading:      920ms  (one-time)
DINOv2 forward:     ~10ms  ✅ Good
FAISS search:       ~5ms   ✅ Good
ORB (×10 cards):    ~700ms ⚠️ Main bottleneck!
```

### Solution: Reduce ORB candidates
```python
# In identify_card_hybrid.py
# Current: Verify top 10 candidates
top_candidates = candidates[:10]

# Optimized: Only verify top 3-5
top_candidates = candidates[:3]
```

**Expected improvement:**
- 732ms → **150-200ms** (3-4x faster)
- Still maintains high accuracy

### Alternative: Skip ORB for high-confidence matches
```python
# Only use ORB if visual similarity < 0.90
if best_visual_score < 0.90:
    run_orb_verification()
```

**Expected improvement:**
- Most cards: 50-100ms (visual + OCR only)
- Ambiguous cards: 200-300ms (with ORB)
- Average: **100-150ms**

## Summary

**For immediate improvement without hardware changes:**
1. Use the optimized batch embedder (`embed_onepiece_dinov2_fast.py`)
2. Reduce ORB candidates from 10 → 3 in identifier
3. Consider DINOv2-tiny if accuracy loss acceptable

**For production deployment:**
1. Get a GPU (10-15x speedup for embeddings)
2. Pre-compute all embeddings
3. Only update incrementally for new cards

**Current bottlenecks:**
- ✅ DINOv2 forward pass: Acceptable on CPU
- ⚠️ ORB verification: Too many candidates (10 cards)
- ℹ️ OCR: Disabled due to Windows Long Path issue (optional feature)

---

**Questions?** See [HYBRID_IDENTIFICATION.md](HYBRID_IDENTIFICATION.md) for architecture details.
