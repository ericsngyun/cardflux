# CardFlux Production Validation Plan

> **Status**: Ready to Execute | **Updated**: 2025-11-04 | **Phase**: Pre-Deployment

## Executive Summary

This document outlines the production validation strategy for CardFlux identification system before multi-game expansion. Based on the "Production First" approach, we will ensure 95%+ accuracy on HIGH confidence identifications before expanding to Pokémon and Magic TCG.

---

## Validation Goals

### Primary Objectives

1. **Accuracy Validation**: Achieve 95%+ accuracy on HIGH confidence identifications
2. **Speed Validation**: Maintain <500ms average identification time (Fast v2)
3. **Reliability Validation**: Zero crashes or memory leaks over 1000+ identifications
4. **Real-World Validation**: Test with actual shop inventory (50-100 cards)

### Success Criteria

| Metric | Target | Critical? |
|--------|--------|-----------|
| HIGH Confidence Accuracy | ≥95% | ✅ Critical |
| Overall Accuracy | ≥90% | ✅ Critical |
| Average Speed (Fast v2) | <500ms | 🟡 Important |
| P95 Speed | <1000ms | 🟡 Important |
| Memory Stability | No leaks | ✅ Critical |
| Edge Case Coverage | 100% | ✅ Critical |
| Crash Rate | 0% | ✅ Critical |

---

## Phase 1: Ground Truth Dataset Collection

**Duration**: 2-3 days
**Owner**: Development Team

### 1.1 Dataset Requirements

**Target Size**: 50-100 cards minimum
**Composition**:
- 30% common cards (C)
- 30% uncommon cards (UC)
- 20% rare cards (R)
- 10% super rare cards (SR)
- 10% leader/promo cards

**Diversity**:
- Mix of sets (ST01-ST10, OP01-OP11)
- Various card types (character, event, stage)
- Different art styles
- Multiple rarities and foil types

### 1.2 Data Collection Process

1. **Photograph Cards**
   - Use consistent lighting (natural or LED)
   - Distance: 12-18 inches from camera
   - Angle: Straight-on (0° tilt)
   - Resolution: 1920x1080 or higher
   - Format: PNG or JPG

2. **Label Each Card**
   Create `ground_truth.json`:
   ```json
   [
     {
       "image_path": "ground_truth/card_001.jpg",
       "card_id": 288227,
       "product_id": 288227,
       "name": "Monkey.D.Luffy",
       "number": "ST01-001",
       "set": "Starter Deck 1",
       "rarity": "L",
       "foil": false,
       "notes": "Clean card, good lighting"
     }
   ]
   ```

3. **Verify Labels**
   - Cross-reference with TCGPlayer
   - Check card numbers match
   - Verify correct variant/edition

### 1.3 Additional Test Cases

**Edge Cases to Include**:
- [ ] 5 cards with watermarks/sample stamps
- [ ] 5 cards in sleeves (with glare)
- [ ] 5 cards at different rotations (0°, 90°, 180°, 270°)
- [ ] 5 cards with minor damage (scratches, bends)
- [ ] 5 cards at varying distances (6in, 12in, 24in)
- [ ] 5 alternate art variants
- [ ] 3 cards with similar artwork (test differentiation)

**Total Target**: 60-100 cards

---

## Phase 2: Accuracy Validation

**Duration**: 1 day
**Owner**: Development Team

### 2.1 Automated Accuracy Test

Create `test_production_accuracy.py`:

```python
def test_ground_truth_accuracy():
    """Test accuracy against ground truth dataset."""

    ground_truth = load_json('ground_truth.json')
    identifier = FastCardIdentifier(game='one-piece')

    results = {
        'total': 0,
        'correct': 0,
        'high_conf_correct': 0,
        'high_conf_wrong': 0,
        'moderate_conf_correct': 0,
        'low_conf_correct': 0,
    }

    for entry in ground_truth:
        result = identifier.identify(entry['image_path'])
        results['total'] += 1

        # Check correctness
        is_correct = result['best_match']['card_id'] == entry['card_id']

        if is_correct:
            results['correct'] += 1
            if result['confidence'] == 'HIGH':
                results['high_conf_correct'] += 1
            elif result['confidence'] == 'MODERATE':
                results['moderate_conf_correct'] += 1
            else:
                results['low_conf_correct'] += 1
        else:
            if result['confidence'] == 'HIGH':
                results['high_conf_wrong'] += 1

    # Calculate metrics
    overall_accuracy = results['correct'] / results['total']
    high_conf_accuracy = (
        results['high_conf_correct'] /
        (results['high_conf_correct'] + results['high_conf_wrong'])
    )

    # Assertions
    assert overall_accuracy >= 0.90, f"Overall accuracy {overall_accuracy:.2%} < 90%"
    assert high_conf_accuracy >= 0.95, f"HIGH confidence accuracy {high_conf_accuracy:.2%} < 95%"

    return results
```

### 2.2 Manual Verification

For any failures:
1. Review failed identifications
2. Check if ground truth labels are correct
3. Analyze why identification failed
4. Categorize failure types:
   - Watermark issues
   - Similar artwork confusion
   - Poor image quality
   - Rotation/angle issues
   - Legitimate system errors

### 2.3 Confidence Calibration

Analyze confidence distribution:
- What percentage of HIGH confidence are correct?
- What percentage of MODERATE confidence are correct?
- What percentage of LOW confidence are correct?

Adjust thresholds if needed based on actual accuracy.

---

## Phase 3: Performance Validation

**Duration**: 1 day
**Owner**: Development Team

### 3.1 Speed Benchmarks

```python
def test_sustained_performance():
    """Test performance over 1000 identifications."""

    identifier = FastCardIdentifier(game='one-piece')
    test_images = load_test_images(count=20)  # Rotate through 20 images

    times = []
    memory_usage = []

    for i in range(1000):
        img = test_images[i % len(test_images)]

        start = time.time()
        result = identifier.identify(img)
        elapsed = time.time() - start

        times.append(elapsed * 1000)  # Convert to ms

        if i % 100 == 0:
            memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_usage.append(memory)
            print(f"[{i:4d}] {elapsed*1000:.0f}ms, Memory: {memory:.0f} MB")

    # Analyze results
    avg_time = np.mean(times)
    p95_time = np.percentile(times, 95)
    memory_growth = memory_usage[-1] - memory_usage[0]

    print(f"\nPerformance Summary:")
    print(f"  Average: {avg_time:.0f}ms")
    print(f"  P50: {np.median(times):.0f}ms")
    print(f"  P95: {p95_time:.0f}ms")
    print(f"  P99: {np.percentile(times, 99):.0f}ms")
    print(f"  Memory growth: {memory_growth:.0f} MB")

    # Assertions
    assert avg_time < 500, f"Average time {avg_time:.0f}ms > 500ms target"
    assert p95_time < 1000, f"P95 time {p95_time:.0f}ms > 1000ms target"
    assert memory_growth < 100, f"Memory leak detected: {memory_growth:.0f} MB growth"
```

### 3.2 Resource Monitoring

Monitor over 1000 identifications:
- CPU usage (should stabilize, not constantly 100%)
- Memory usage (should be stable, no leaks)
- Disk I/O (minimal)
- GPU usage (if enabled)

---

## Phase 4: Edge Case Validation

**Duration**: 1 day
**Owner**: Development Team

### 4.1 Edge Case Tests

```python
@pytest.mark.parametrize("test_case", [
    {"name": "no_card", "image": "empty_table.jpg", "expected": "NO_CARD_DETECTED"},
    {"name": "multiple_cards", "image": "two_cards.jpg", "expected": "MULTIPLE_CARDS_WARNING"},
    {"name": "rotated_90", "image": "card_rotated_90.jpg", "expected": "CORRECT_IDENTIFICATION"},
    {"name": "in_sleeve", "image": "card_in_sleeve.jpg", "expected": "CORRECT_IDENTIFICATION"},
    {"name": "damaged", "image": "damaged_card.jpg", "expected": "CORRECT_OR_WARNING"},
])
def test_edge_case(test_case):
    """Test edge case handling."""
    identifier = FastCardIdentifier(game='one-piece')
    result = identifier.identify(test_case['image'])
    # Validate expected behavior
```

### 4.2 Edge Cases Checklist

- [ ] No card in image → Handled gracefully
- [ ] Multiple cards → Warning or error
- [ ] Card rotated 90° → Still identified correctly
- [ ] Card rotated 180° → Still identified correctly
- [ ] Card in sleeve with glare → Lower confidence but correct
- [ ] Heavily damaged card → Warning or LOW confidence
- [ ] Card too far away → LOW confidence or quality warning
- [ ] Card partially visible → Warning or error
- [ ] Invalid image format → Proper error message
- [ ] Corrupted image → Proper error message

---

## Phase 5: Real-World Shop Testing

**Duration**: 2-3 days
**Owner**: Development Team + Shop Partner (if available)

### 5.1 Shop Inventory Test

**Goal**: Test with 50-100 real shop cards

**Process**:
1. Select diverse inventory sample
2. Run through identification system
3. Manually verify ALL results
4. Track accuracy, speed, edge cases
5. Collect feedback on UX

### 5.2 Shop Testing Metrics

Track:
- Accuracy (% correct identifications)
- Speed (average time per card)
- User experience (easy to use? frustrations?)
- Edge cases encountered
- System failures or crashes

### 5.3 Feedback Collection

Questions for shop owners/users:
1. How accurate were the identifications?
2. Were there any wrong identifications?
3. How was the speed? Acceptable?
4. Any edge cases or problems encountered?
5. Would you use this in production?
6. What improvements would you suggest?

---

## Phase 6: Results Analysis & Iteration

**Duration**: 1-2 days
**Owner**: Development Team

### 6.1 Analyze Results

Compile all validation data:
- Accuracy metrics
- Performance metrics
- Edge case results
- Shop feedback
- Failure analysis

### 6.2 Identify Issues

Categorize all failures/issues:
1. **Critical** - Must fix before production
2. **High** - Should fix before production
3. **Medium** - Can fix in next release
4. **Low** - Nice to have

### 6.3 Iterate if Needed

If accuracy < 95% HIGH confidence:
1. Analyze failure patterns
2. Implement fixes
3. Re-test on ground truth dataset
4. Repeat until criteria met

---

## Phase 7: Production Readiness Sign-Off

**Duration**: 1 day
**Owner**: Senior Engineer

### 7.1 Final Checklist

- [ ] ✅ Ground truth dataset collected (50-100 cards)
- [ ] ✅ Accuracy validation passed (≥95% HIGH confidence)
- [ ] ✅ Performance validation passed (<500ms avg, no leaks)
- [ ] ✅ Edge case validation passed (all cases handled)
- [ ] ✅ Real-world shop testing complete (50-100 cards)
- [ ] ✅ Automated tests added to test suite
- [ ] ✅ Documentation updated
- [ ] ✅ Known issues documented
- [ ] ✅ Failure recovery procedures documented

### 7.2 Production Readiness Report

Create final report:
```markdown
# Production Readiness Report - CardFlux One Piece TCG

**Date**: 2025-11-XX
**Status**: READY / NOT READY

## Validation Results

- Overall Accuracy: XX.X%
- HIGH Confidence Accuracy: XX.X%
- Average Speed: XXXms
- Memory Stable: YES/NO
- Edge Cases: XX/XX passed
- Shop Testing: XX/XX cards correct

## Critical Issues

[None / List issues]

## Recommendation

[READY FOR MULTI-GAME EXPANSION / NEEDS FIXES]
```

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. Ground Truth Collection | 2-3 days | Camera, cards |
| 2. Accuracy Validation | 1 day | Phase 1 |
| 3. Performance Validation | 1 day | Phase 1 |
| 4. Edge Case Validation | 1 day | Phase 1 |
| 5. Shop Testing | 2-3 days | Phase 2-4, shop partner |
| 6. Analysis & Iteration | 1-2 days | Phase 5 |
| 7. Sign-Off | 1 day | Phase 6 |

**Total**: 9-12 days (2-2.5 weeks)

---

## Next Steps After Validation

Once production validation is complete and system achieves ≥95% HIGH confidence accuracy:

1. **Multi-Game Expansion**
   - Add Pokémon TCG support
   - Add Magic: The Gathering support
   - Repeat validation for each game

2. **Production Deployment**
   - Package desktop app installers
   - Create deployment guide
   - Beta release to select shops

3. **Continuous Improvement**
   - Monitor production accuracy
   - Collect failure cases
   - Iterate and improve

---

**Maintained by**: CardFlux Team | **Last Updated**: 2025-11-04 | **Status**: Ready to Execute
