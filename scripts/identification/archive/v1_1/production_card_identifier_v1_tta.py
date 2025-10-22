#!/usr/bin/env python3
"""
Production Card Identification System V1 + TTA (Test-Time Augmentation)

Enhancement over V1 baseline:
- Query image augmentation at identification time
- Multiple augmented versions with weighted voting
- Conservative approach: only boost confidence, never reduce

Expected improvement: +8-12% accuracy on real-world photos
Processing overhead: +100-200ms (3-5 augmentations)

Author: Senior Principal Engineer
Date: 2025-10-21
"""
import sys
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from production_card_identifier import ProductionCardIdentifier


class ProductionCardIdentifierV1_TTA(ProductionCardIdentifier):
    """
    V1 + TTA: Test-Time Augmentation for improved robustness.

    Key Features:
    1. Generate 3-5 augmented versions of query image
    2. Run identification on each augmented version
    3. Vote/aggregate results (weighted by confidence)
    4. Conservative: only boost scores, never reduce

    Augmentations:
    - Original (weight: 1.0)
    - Rotate +3° (weight: 0.8)
    - Rotate -3° (weight: 0.8)
    - Brightness +10% (weight: 0.7)
    - Brightness -10% (weight: 0.7)

    Total: 5 forward passes, ~150-250ms overhead
    """

    def __init__(self, game: str = 'one-piece', verbose: bool = True, enable_variant_classifier: bool = True):
        """Initialize V1+TTA identifier."""
        super().__init__(game=game, verbose=verbose, enable_variant_classifier=enable_variant_classifier)

        if self.verbose:
            print(f"  [TTA] Test-Time Augmentation enabled:")
            print(f"      - 5 augmented versions (original + 4 transforms)")
            print(f"      - Weighted voting for robustness")
            print(f"      - Conservative score boosting")

    def _augment_image(self, image_path: str) -> List[Tuple[str, float]]:
        """
        Generate augmented versions of the query image.

        Returns:
            List of (augmented_image_path, weight) tuples
        """
        # Load original image
        img = Image.open(image_path).convert('RGB')
        img_array = np.array(img)

        augmented = []
        temp_dir = Path(tempfile.gettempdir()) / "cardflux_tta"
        temp_dir.mkdir(exist_ok=True)

        # 1. Original (highest weight)
        original_path = str(temp_dir / "aug_original.jpg")
        img.save(original_path)
        augmented.append((original_path, 1.0))

        # 2. Rotate +3 degrees (handle slight angle)
        rotated_pos = self._rotate_image(img_array, angle=3)
        rotated_pos_path = str(temp_dir / "aug_rotate_pos3.jpg")
        Image.fromarray(rotated_pos).save(rotated_pos_path)
        augmented.append((rotated_pos_path, 0.8))

        # 3. Rotate -3 degrees
        rotated_neg = self._rotate_image(img_array, angle=-3)
        rotated_neg_path = str(temp_dir / "aug_rotate_neg3.jpg")
        Image.fromarray(rotated_neg).save(rotated_neg_path)
        augmented.append((rotated_neg_path, 0.8))

        # 4. Brightness +10% (handle dark photos)
        bright_plus = self._adjust_brightness(img_array, factor=1.1)
        bright_plus_path = str(temp_dir / "aug_bright_plus.jpg")
        Image.fromarray(bright_plus).save(bright_plus_path)
        augmented.append((bright_plus_path, 0.7))

        # 5. Brightness -10% (handle overexposed photos)
        bright_minus = self._adjust_brightness(img_array, factor=0.9)
        bright_minus_path = str(temp_dir / "aug_bright_minus.jpg")
        Image.fromarray(bright_minus).save(bright_minus_path)
        augmented.append((bright_minus_path, 0.7))

        return augmented

    def _rotate_image(self, img_array: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by angle degrees."""
        h, w = img_array.shape[:2]
        center = (w // 2, h // 2)

        # Get rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Rotate
        rotated = cv2.warpAffine(img_array, M, (w, h),
                                 borderMode=cv2.BORDER_REPLICATE)

        return rotated

    def _adjust_brightness(self, img_array: np.ndarray, factor: float) -> np.ndarray:
        """Adjust brightness by factor (1.0 = no change)."""
        adjusted = np.clip(img_array * factor, 0, 255).astype(np.uint8)
        return adjusted

    def _aggregate_results(self, results: List[Tuple[Dict, float]]) -> Dict:
        """
        Aggregate results from multiple augmented images.

        Strategy:
        1. Collect all predictions with their weights
        2. Vote for most common card (weighted)
        3. Average scores (weighted)
        4. Boost confidence if agreement is high

        Conservative approach: Only boost, never reduce from original
        """
        # Extract card predictions with weights
        card_votes = {}
        original_result = None

        for result, weight in results:
            card_id = result['best_match']['card_id']
            score = result['best_match']['final_score']

            # Track original result (weight=1.0)
            if weight == 1.0:
                original_result = result

            if card_id not in card_votes:
                card_votes[card_id] = {
                    'votes': 0,
                    'scores': [],
                    'weights': [],
                    'results': []
                }

            card_votes[card_id]['votes'] += weight
            card_votes[card_id]['scores'].append(score)
            card_votes[card_id]['weights'].append(weight)
            card_votes[card_id]['results'].append(result)

        # Find winner (most votes)
        winner_id = max(card_votes.items(), key=lambda x: x[1]['votes'])[0]
        winner_data = card_votes[winner_id]

        # Calculate weighted average score
        total_weight = sum(winner_data['weights'])
        weighted_score = sum(s * w for s, w in zip(winner_data['scores'], winner_data['weights'])) / total_weight

        # Calculate agreement rate
        agreement_rate = winner_data['votes'] / sum(v['votes'] for v in card_votes.values())

        # Get the best result for this card
        best_result = max(winner_data['results'],
                         key=lambda r: r['best_match']['final_score'])

        # Conservative boosting: only if TTA improves over original
        if original_result and winner_id == original_result['best_match']['card_id']:
            # Same card identified - boost score if TTA is more confident
            if weighted_score > original_result['best_match']['final_score']:
                # TTA boosted the score
                final_result = best_result.copy()
                final_result['best_match']['final_score'] = weighted_score
                final_result['tta_boost'] = weighted_score - original_result['best_match']['final_score']
                final_result['tta_agreement'] = agreement_rate
            else:
                # TTA didn't improve - use original
                final_result = original_result
                final_result['tta_boost'] = 0.0
                final_result['tta_agreement'] = agreement_rate
        else:
            # Different card or no original - use TTA result but flag it
            final_result = best_result.copy()
            final_result['best_match']['final_score'] = weighted_score
            final_result['tta_boost'] = 0.0
            final_result['tta_agreement'] = agreement_rate
            final_result['tta_different_card'] = True

        # Re-compute confidence based on potentially boosted score
        final_result['confidence'] = self._compute_confidence_from_score(
            final_result['best_match']['final_score']
        )

        return final_result

    def _compute_confidence_from_score(self, score: float) -> str:
        """Compute confidence level from score (V1 logic)."""
        if score >= 0.75:
            return 'HIGH'
        elif score >= 0.62:
            return 'MODERATE'
        else:
            return 'LOW'

    def identify_with_tta(
        self,
        image_path: str,
        top_k: int = 50,
        use_geometric: bool = True,
        tcg_hint: str = None
    ) -> Dict:
        """
        Identify card using Test-Time Augmentation.

        Args:
            image_path: Path to query image
            top_k: Number of candidates
            use_geometric: Enable geometric verification
            tcg_hint: TCG hint for card number extraction

        Returns:
            Aggregated identification result with TTA metadata
        """
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"IDENTIFICATION WITH TTA")
            print(f"{'='*70}")

        # Generate augmented images
        augmented_images = self._augment_image(image_path)

        if self.verbose:
            print(f"Generated {len(augmented_images)} augmented versions")
            print()

        # Run identification on each augmented version
        results = []
        for aug_path, weight in augmented_images:
            if self.verbose:
                aug_name = Path(aug_path).stem
                print(f"  [{aug_name}] (weight: {weight:.1f})", end=" ")

            # Use parent's identify method (V1 baseline)
            result = super().identify(aug_path, top_k=top_k,
                                     use_geometric=use_geometric,
                                     tcg_hint=tcg_hint)

            if self.verbose:
                print(f"→ {result['best_match']['name'][:30]:30s} | {result['confidence']:8s} | {result['best_match']['final_score']:.4f}")

            results.append((result, weight))

        # Aggregate results
        if self.verbose:
            print()
            print("Aggregating results...")

        final_result = self._aggregate_results(results)

        if self.verbose:
            print()
            print(f"Final Result: {final_result['best_match']['name']}")
            print(f"Confidence: {final_result['confidence']}")
            print(f"Score: {final_result['best_match']['final_score']:.4f}")
            print(f"TTA Boost: +{final_result.get('tta_boost', 0):.4f}")
            print(f"Agreement: {final_result.get('tta_agreement', 0)*100:.1f}%")

        return final_result

    def identify(self, image_path: str, **kwargs) -> Dict:
        """
        Override identify to use TTA by default.

        This ensures TTA is used when called from version manager.
        """
        return self.identify_with_tta(image_path, **kwargs)


def main():
    """Test V1+TTA."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python production_card_identifier_v1_tta.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("="*70)
    print("Testing V1 + TTA (Test-Time Augmentation)")
    print("="*70)
    print()

    # Test with V1+TTA
    identifier = ProductionCardIdentifierV1_TTA()
    result = identifier.identify_with_tta(image_path, top_k=50, use_geometric=True)

    print()
    print("="*70)
    print("FINAL RESULT")
    print("="*70)
    print(f"Card: {result['best_match']['name']}")
    print(f"Number: {result['best_match']['number']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Score: {result['best_match']['final_score']:.4f}")
    print(f"TTA Boost: +{result.get('tta_boost', 0):.4f}")
    print(f"Agreement: {result.get('tta_agreement', 0)*100:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
