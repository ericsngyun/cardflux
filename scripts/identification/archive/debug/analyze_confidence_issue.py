#!/usr/bin/env python3
"""
Deep analysis of confidence scoring issues.
Analyzes why certain cards get LOW confidence despite correct identification.
"""
import sys
import json
import numpy as np
from pathlib import Path
from production_card_identifier import ProductionCardIdentifier

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

def analyze_image(image_path, identifier, expected_name=None):
    """Perform detailed analysis of identification result."""
    print(f"\n{'='*80}")
    print(f"DETAILED ANALYSIS: {Path(image_path).name}")
    print(f"{'='*80}")

    # Run identification with verbose output
    result = identifier.identify(image_path, top_k=50, tcg_hint="one-piece")

    best = result['best_match']
    scores = result['scores']
    confidence = result['confidence']

    print(f"\n[RESULT]")
    print(f"  Identified: {best['name']}")
    print(f"  Card Number: {best.get('number', 'N/A')}")
    print(f"  Confidence: {confidence} (score: {scores['final']:.4f})")

    if expected_name:
        is_correct = expected_name.lower() in best['name'].lower()
        print(f"  Expected: {expected_name}")
        print(f"  Match: {'[CORRECT]' if is_correct else '[WRONG]'}")

    print(f"\n[SCORE BREAKDOWN]")
    print(f"  Visual Score:    {scores['visual']:.4f} (weight: 0.75)")
    print(f"  Geometric Score: {scores['geometric']:.4f} (weight: 0.25)")
    print(f"  Final Score:     {scores['final']:.4f}")
    print(f"  2nd Place Score: {scores.get('second_place', 0):.4f}")
    print(f"  Margin:          {scores['final'] - scores.get('second_place', 0):.4f}")

    print(f"\n[THRESHOLDS]")
    print(f"  AUTO_ACCEPT:     0.60 {'[PASS]' if scores['final'] >= 0.60 else '[FAIL]'}")
    print(f"  MARGIN:          0.12 {'[PASS]' if (scores['final'] - scores.get('second_place', 0)) >= 0.12 else '[FAIL]'}")

    print(f"\n[CONFIDENCE LOGIC]")
    if scores['final'] >= 0.60 and (scores['final'] - scores.get('second_place', 0)) >= 0.12:
        print(f"  -> HIGH: Score >= 0.60 AND margin >= 0.12")
    elif scores['final'] >= 0.45 and scores['geometric'] > 0.0:
        print(f"  -> MODERATE: Score >= 0.45 AND has geometric match")
    else:
        print(f"  -> LOW: Does not meet HIGH or MODERATE criteria")
        print(f"      - Final score: {scores['final']:.4f} (need >= 0.60)")
        print(f"      - Margin: {scores['final'] - scores.get('second_place', 0):.4f} (need >= 0.12)")
        print(f"      - Geometric: {scores['geometric']:.4f}")

    print(f"\n[TOP 10 CANDIDATES]")
    top_candidates = result.get('top_candidates', [])[:10]
    for i, cand in enumerate(top_candidates, 1):
        visual = cand.get('score_visual', 0)
        geom = cand.get('score_geometric', 0)
        final = cand.get('score_final', 0)
        name = cand['name']

        # Truncate long names
        if len(name) > 50:
            name = name[:47] + "..."

        marker = "*" if i == 1 else " "
        print(f"  {marker} {i:2d}. {name:50s} | V:{visual:.3f} G:{geom:.3f} F:{final:.4f}")

    print(f"\n[FEATURE ANALYSIS]")
    if result.get('foil_detected'):
        print(f"  Foil: YES ({result['foil_type']}, conf: {result['foil_confidence']:.3f})")
    else:
        print(f"  Foil: NO")

    if result.get('card_number_extracted'):
        print(f"  Card Number: {result['card_number_extracted']}")
    else:
        print(f"  Card Number: Not detected")

    print(f"\n[TIMING]")
    print(f"  Total: {result['time_ms']}ms")

    print(f"\n[DIAGNOSIS]")

    # Analyze visual score
    if scores['visual'] < 0.70:
        print(f"  [!] Low visual similarity ({scores['visual']:.3f})")
        print(f"     -> Image quality issue (glare, shadows, angle)?")
        print(f"     -> Check if reference image exists in database")

    # Analyze geometric score
    if scores['geometric'] < 0.20:
        print(f"  [!] Low geometric match ({scores['geometric']:.3f})")
        print(f"     -> ORB features not matching well")
        print(f"     -> Could indicate variant (different artwork)")
        print(f"     -> Or poor feature extraction from query image")

    # Analyze margin
    margin = scores['final'] - scores.get('second_place', 0)
    if margin < 0.12:
        print(f"  [!] Low margin ({margin:.3f})")
        print(f"     -> Multiple similar candidates")
        print(f"     -> Card may have many variants in database")
        print(f"     -> Need better variant discrimination")

    # Check if correct but low confidence
    if expected_name and is_correct and confidence == "LOW":
        print(f"\n  [!] ALERT: Correct card but LOW confidence!")
        print(f"     This is a FALSE NEGATIVE - we need to adjust thresholds")
        print(f"     or improve scoring algorithm.")

    print(f"\n{'='*80}\n")

    return result


def main():
    print("\n" + "="*80)
    print("CONFIDENCE ISSUE ANALYSIS")
    print("="*80)

    # Test cases with expected results
    test_cases = [
        {
            "image": "../../test-images/one-piece/bege.png",
            "expected": "Capone\"Gang\"Bege",
            "description": "Clean scan, should be HIGH"
        },
        {
            "image": "../../test-images/one-piece/blackbeard.png",
            "expected": "Marshall.D.Teach",
            "description": "Clean scan, should be HIGH"
        },
        {
            "image": "../../test-images/one-piece/blackbeard-db.jpg",
            "expected": "Marshall.D.Teach",
            "description": "Database image, should be PERFECT"
        },
        {
            "image": "../../test-images/one-piece/yellow_event.png",
            "expected": "You're the One Who Should Disappear",
            "description": "Real-world photo with glare/shadows - PROBLEM CASE"
        }
    ]

    # Initialize system once
    print("\nInitializing production system...")
    identifier = ProductionCardIdentifier(game="one-piece", verbose=False)
    print("[OK] System ready\n")

    results = []

    for test in test_cases:
        image_path = test['image']

        if not Path(image_path).exists():
            print(f"[SKIP] {image_path} not found")
            continue

        print(f"\n{'='*80}")
        print(f"TEST: {test['description']}")
        print(f"{'='*80}")

        result = analyze_image(image_path, identifier, test['expected'])
        results.append({
            'image': Path(image_path).name,
            'expected': test['expected'],
            'got': result['best_match']['name'],
            'confidence': result['confidence'],
            'score': result['scores']['final'],
            'visual': result['scores']['visual'],
            'geometric': result['scores']['geometric'],
            'margin': result['scores']['final'] - result['scores'].get('second_place', 0)
        })

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    print(f"\n{'Image':<25} {'Confidence':<12} {'Score':<8} {'Visual':<8} {'Geom':<8} {'Margin':<8}")
    print("-" * 80)

    for r in results:
        print(f"{r['image']:<25} {r['confidence']:<12} {r['score']:<8.4f} {r['visual']:<8.4f} {r['geometric']:<8.4f} {r['margin']:<8.4f}")

    # Analysis
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    low_conf_correct = [r for r in results if r['confidence'] == 'LOW' and
                        r['expected'].lower() in r['got'].lower()]

    if low_conf_correct:
        print("\n[!] ISSUE DETECTED: Correct identifications with LOW confidence")
        print(f"   Affected: {len(low_conf_correct)} / {len(results)} test cases")

        for r in low_conf_correct:
            print(f"\n   Case: {r['image']}")
            print(f"   - Score: {r['score']:.4f} (need >= 0.60 for HIGH)")
            print(f"   - Margin: {r['margin']:.4f} (need >= 0.12 for HIGH)")

            if r['score'] < 0.60:
                shortfall = 0.60 - r['score']
                print(f"   - Shortfall: {shortfall:.4f} below threshold")

                if r['visual'] < 0.70:
                    print(f"   -> Root cause: Low visual similarity ({r['visual']:.3f})")
                    print(f"      Solution: Improve image preprocessing or use better reference images")

                if r['geometric'] < 0.20:
                    print(f"   -> Root cause: Poor geometric match ({r['geometric']:.3f})")
                    print(f"      Solution: Tune ORB parameters or expand geometric verification")

        print(f"\n   Potential Solutions:")
        print(f"   1. Lower AUTO_ACCEPT threshold: 0.60 -> 0.50")
        print(f"   2. Lower MARGIN threshold: 0.12 -> 0.08")
        print(f"   3. Improve preprocessing (denoise, deskew, crop)")
        print(f"   4. Adjust scoring weights (increase geometric weight?)")
        print(f"   5. Add card number matching boost")
    else:
        print("\n[OK] All correct identifications have appropriate confidence levels")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
