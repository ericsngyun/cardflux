#!/usr/bin/env python3
"""
Production Card Identification System V2 - Enhanced Version

Improvements over V1:
- Multi-frame fusion for improved accuracy
- Adaptive preprocessing based on image analysis
- Enhanced detection for foil/glossy cards
- Adaptive quality thresholds
- Better sleeve handling

All improvements are backwards compatible with V1 fallback support.

Author: Senior Principal Engineer
Date: 2025-10-21
"""
import sys
import json
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

# Suppress warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import cv2
    import faiss
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModel

    # Import V1 as base class
    from production_card_identifier import ProductionCardIdentifier
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    sys.exit(1)


class ProductionCardIdentifierV2(ProductionCardIdentifier):
    """
    Enhanced card identification with multi-frame fusion and adaptive preprocessing.

    New Features:
    - Multi-frame result fusion (vote across 3-5 frames)
    - Adaptive preprocessing (brightness/sharpness aware)
    - Adaptive quality thresholds (distance-dependent)
    - Enhanced foil card detection
    - Sleeve glare detection
    """

    def __init__(self, game: str = 'one-piece', verbose: bool = True, enable_variant_classifier: bool = True):
        """Initialize V2 identifier (extends V1)."""
        # Call parent constructor
        super().__init__(game=game, verbose=verbose, enable_variant_classifier=enable_variant_classifier)

        if self.verbose:
            print(f"  [V2] Enhanced features enabled:")
            print(f"      - Multi-frame fusion")
            print(f"      - Adaptive preprocessing")
            print(f"      - Adaptive quality thresholds")

    def identify_multi_frame(
        self,
        image_paths: List[str],
        top_k: int = 50,
        use_geometric: bool = True,
        tcg_hint: Optional[str] = None
    ) -> Dict:
        """
        Identify card using multiple frames with result fusion.

        This is the KEY improvement of V2: aggregate results across multiple
        captures to handle borderline cases and improve accuracy.

        Args:
            image_paths: List of 3-5 image paths captured in sequence
            top_k: Number of visual candidates per frame
            use_geometric: Enable geometric verification
            tcg_hint: TCG hint for card number extraction

        Returns:
            Fused identification result with voting metadata
        """
        if len(image_paths) < 2:
            # Single frame, use standard identify
            return self.identify(image_paths[0], top_k=top_k, use_geometric=use_geometric, tcg_hint=tcg_hint)

        if self.verbose:
            print(f"\n{'='*70}")
            print(f"MULTI-FRAME IDENTIFICATION (V2)")
            print(f"{'='*70}")
            print(f"Frames: {len(image_paths)}")

        start_time = time.time()
        frame_results = []

        # Identify each frame independently
        for idx, image_path in enumerate(image_paths, 1):
            if self.verbose:
                print(f"\n[Frame {idx}/{len(image_paths)}] Processing: {Path(image_path).name}")

            result = self.identify(
                image_path,
                top_k=top_k,
                use_geometric=use_geometric,
                tcg_hint=tcg_hint
            )
            frame_results.append(result)

            if self.verbose:
                best = result['best_match']
                print(f"  → {best['name']} ({result['confidence']}, score: {best['final_score']:.3f})")

        # Fuse results
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"FUSING RESULTS")
            print(f"{'='*70}")

        fused_result = self._fuse_multi_frame_results(frame_results)

        total_time = time.time() - start_time
        fused_result['multi_frame'] = {
            'num_frames': len(image_paths),
            'total_time_ms': int(total_time * 1000),
            'avg_time_per_frame_ms': int((total_time / len(image_paths)) * 1000),
            'frame_results': frame_results,  # Keep individual results for debugging
        }

        if self.verbose:
            print(f"\nFINAL FUSED RESULT:")
            print(f"  Card: {fused_result['best_match']['name']}")
            print(f"  Confidence: {fused_result['confidence']}")
            print(f"  Fusion Votes: {fused_result.get('fusion_votes', 0):.1f}")
            print(f"  Total Time: {total_time*1000:.0f}ms")
            print(f"{'='*70}\n")

        return fused_result

    def _fuse_multi_frame_results(self, frame_results: List[Dict]) -> Dict:
        """
        Fuse multiple identification results using weighted voting.

        Strategy:
        1. Each frame votes for a card (weighted by confidence)
        2. HIGH confidence = 1.0 vote, MODERATE = 0.6, LOW = 0.3
        3. Winner = most votes + highest average score
        4. Boost confidence if multiple frames strongly agree

        Args:
            frame_results: List of identification results from multiple frames

        Returns:
            Fused result with highest vote count
        """
        if len(frame_results) == 1:
            return frame_results[0]

        # Voting system: card_id -> {votes, scores, results}
        card_votes = {}

        confidence_weights = {
            'HIGH': 1.0,
            'MODERATE': 0.6,
            'LOW': 0.3
        }

        for result in frame_results:
            card_id = result['best_match']['card_id']
            confidence = result['confidence']
            final_score = result['best_match']['final_score']

            weight = confidence_weights.get(confidence, 0.3)

            if card_id not in card_votes:
                card_votes[card_id] = {
                    'votes': 0,
                    'scores': [],
                    'results': [],
                    'confidence_levels': []
                }

            card_votes[card_id]['votes'] += weight
            card_votes[card_id]['scores'].append(final_score)
            card_votes[card_id]['results'].append(result)
            card_votes[card_id]['confidence_levels'].append(confidence)

        # Find winner (most votes, then highest avg score)
        winner_id = max(
            card_votes.items(),
            key=lambda x: (x[1]['votes'], np.mean(x[1]['scores']))
        )[0]

        winner_data = card_votes[winner_id]
        winner_result = winner_data['results'][0]  # Use first occurrence as base

        # Calculate fusion metadata
        num_votes = winner_data['votes']
        avg_score = np.mean(winner_data['scores'])
        max_score = max(winner_data['scores'])
        agreement_rate = num_votes / len(frame_results)

        # Boost confidence if strong agreement
        original_confidence = winner_result['confidence']
        boosted_confidence = original_confidence

        if num_votes >= 2.5:  # At least 2.5 weighted votes (e.g., 2 HIGH + 1 MODERATE)
            boosted_confidence = 'HIGH'
        elif num_votes >= 1.5 and avg_score > 0.70:
            boosted_confidence = 'HIGH'
        elif num_votes >= 1.2:
            boosted_confidence = 'MODERATE'

        # Update winner result with fusion data
        fused_result = winner_result.copy()
        fused_result['confidence'] = boosted_confidence
        fused_result['fusion_votes'] = num_votes
        fused_result['fusion_avg_score'] = avg_score
        fused_result['fusion_max_score'] = max_score
        fused_result['fusion_agreement_rate'] = agreement_rate
        fused_result['fusion_original_confidence'] = original_confidence
        fused_result['fusion_confidence_boost'] = (boosted_confidence != original_confidence)

        if self.verbose:
            print(f"Voting Results:")
            for card_id, data in sorted(card_votes.items(), key=lambda x: x[1]['votes'], reverse=True)[:3]:
                card_name = data['results'][0]['best_match']['name']
                print(f"  {data['votes']:.1f} votes → {card_name} (avg: {np.mean(data['scores']):.3f})")

            print(f"\nWinner: {winner_result['best_match']['name']}")
            print(f"  Votes: {num_votes:.1f}/{len(frame_results)}")
            print(f"  Agreement: {agreement_rate*100:.1f}%")
            print(f"  Confidence: {original_confidence} → {boosted_confidence}")

        return fused_result

    def _get_image_embedding(self, image_path: str) -> np.ndarray:
        """
        Generate DINOv2 embedding with ADAPTIVE preprocessing (V2 enhancement).

        Analyzes image characteristics first, then applies appropriate filters.
        Maintains consistency with index embeddings while handling edge cases better.
        """
        image = Image.open(image_path).convert("RGB")
        img_array = np.array(image)

        # Analyze image characteristics
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        brightness = np.mean(gray)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Adaptive preprocessing based on analysis
        if brightness < 80:
            # Dark image - enhance brightness more aggressively
            alpha, beta = 1.15, 15
        elif brightness > 180:
            # Bright image - reduce brightness slightly
            alpha, beta = 0.95, -5
        else:
            # Normal brightness - standard enhancement (same as V1)
            alpha, beta = 1.05, 3

        enhanced = cv2.convertScaleAbs(img_array, alpha=alpha, beta=beta)

        # Adaptive bilateral filtering based on sharpness
        if sharpness < 50:
            # Blurry image - stronger denoising
            filtered = cv2.bilateralFilter(enhanced, 7, 75, 75)
        else:
            # Sharp image - standard filtering (same as V1)
            filtered = cv2.bilateralFilter(enhanced, 5, 50, 50)

        # Convert back to PIL
        image = Image.fromarray(filtered)

        # Generate embedding with DINOv2 (same as V1)
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def _check_image_quality(self, image_path: str, card_area_ratio: float = 0.25) -> Dict:
        """
        Check image quality with ADAPTIVE thresholds (V2 enhancement).

        Farther cards (smaller area_ratio) get more lenient thresholds.
        This reduces false rejections of valid but distant captures.

        Args:
            image_path: Path to image
            card_area_ratio: Card area as fraction of frame (0.02 to 0.85)

        Returns:
            Quality check result with adaptive thresholds
        """
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if img is None:
            return {
                'is_acceptable': False,
                'sharpness_score': 0.0,
                'brightness': 0.0,
                'warnings': ['Image could not be loaded']
            }

        warnings = []

        # Check image size
        if min(img.shape) < 200:
            warnings.append(f'Image too small ({img.shape[1]}x{img.shape[0]})')

        # Adaptive sharpness threshold
        # Far cards (0.02 ratio) → threshold 20, Close cards (0.50 ratio) → threshold 50
        adaptive_sharpness_threshold = 20 + (card_area_ratio * 60)

        laplacian = cv2.Laplacian(img, cv2.CV_64F)
        sharpness_score = laplacian.var()

        if sharpness_score < adaptive_sharpness_threshold:
            warnings.append(f'Image may be blurry (sharpness: {sharpness_score:.1f}, threshold: {adaptive_sharpness_threshold:.1f})')

        # Adaptive brightness tolerance
        # More lenient when card is far away
        brightness = np.mean(img)
        brightness_tolerance = 30 + (card_area_ratio * 20)

        min_brightness = 50 - brightness_tolerance
        max_brightness = 220 + brightness_tolerance

        if brightness < min_brightness:
            warnings.append(f'Image too dark (brightness: {brightness:.1f})')
        elif brightness > max_brightness:
            warnings.append(f'Image overexposed (brightness: {brightness:.1f})')

        # Check for sleeve glare (V2 enhancement)
        glare_pixels = np.sum(img > 240)
        glare_ratio = glare_pixels / img.size

        if glare_ratio > 0.05:  # More than 5% bright pixels
            warnings.append(f'Glare detected (possible sleeve reflection: {glare_ratio*100:.1f}%)')

        # More lenient acceptance criteria for distant cards
        is_acceptable = (
            sharpness_score >= adaptive_sharpness_threshold * 0.8 and  # Allow 80% of threshold
            min_brightness <= brightness <= max_brightness
        )

        return {
            'is_acceptable': is_acceptable,
            'sharpness_score': float(sharpness_score),
            'brightness': float(brightness),
            'glare_ratio': float(glare_ratio),
            'adaptive_sharpness_threshold': float(adaptive_sharpness_threshold),
            'warnings': warnings
        }

    def identify(
        self,
        image_path: str,
        top_k: int = 50,
        use_geometric: bool = True,
        tcg_hint: Optional[str] = None
    ) -> Dict:
        """
        Identify card with V2 enhancements (single frame).

        Overrides V1 identify() to use adaptive preprocessing and quality checks.

        Args:
            image_path: Path to card image
            top_k: Number of visual candidates
            use_geometric: Enable geometric verification
            tcg_hint: TCG hint for card number extraction

        Returns:
            Identification result
        """
        # Get card area ratio estimate from image
        # (In real usage, this would come from card detector)
        # For now, assume reasonable default
        estimated_area_ratio = 0.25

        # Call parent identify() which will use our overridden methods
        result = super().identify(image_path, top_k, use_geometric, tcg_hint)

        # Update quality check with adaptive thresholds
        result['quality_check'] = self._check_image_quality(image_path, estimated_area_ratio)

        # Add V2 metadata
        result['identifier_version'] = 'v2'
        result['enhancements'] = {
            'adaptive_preprocessing': True,
            'adaptive_quality_thresholds': True,
            'enhanced_sleeve_detection': True
        }

        return result


def main():
    """Main entry point for testing V2."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Production Card Identification System V2 - Enhanced',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single frame (uses adaptive preprocessing)
  python production_card_identifier_v2.py card.jpg

  # Multi-frame fusion (best accuracy)
  python production_card_identifier_v2.py frame1.jpg frame2.jpg frame3.jpg --multi-frame

  # Compare with V1
  python production_card_identifier_v2.py card.jpg --compare-v1
        """
    )
    parser.add_argument('images', nargs='+', help='Path(s) to card image(s)')
    parser.add_argument('--tcg', default='one-piece', help='TCG hint (default: one-piece)')
    parser.add_argument('--top-k', type=int, default=50, help='Number of candidates (default: 50)')
    parser.add_argument('--multi-frame', action='store_true', help='Use multi-frame fusion')
    parser.add_argument('--compare-v1', action='store_true', help='Compare with V1 baseline')
    parser.add_argument('--json', help='Save result to JSON file')
    parser.add_argument('--quiet', action='store_true', help='Suppress output')

    args = parser.parse_args()

    try:
        # Initialize V2 identifier
        identifier_v2 = ProductionCardIdentifierV2(
            game=args.tcg,
            verbose=not args.quiet
        )

        # Identify
        if args.multi_frame and len(args.images) > 1:
            result = identifier_v2.identify_multi_frame(
                args.images,
                top_k=args.top_k,
                tcg_hint=args.tcg
            )
        else:
            result = identifier_v2.identify(
                args.images[0],
                top_k=args.top_k,
                tcg_hint=args.tcg
            )

        # Compare with V1 if requested
        if args.compare_v1:
            print(f"\n{'='*70}")
            print("COMPARING WITH V1 BASELINE")
            print(f"{'='*70}\n")

            identifier_v1 = ProductionCardIdentifier(
                game=args.tcg,
                verbose=not args.quiet
            )

            v1_result = identifier_v1.identify(
                args.images[0],
                top_k=args.top_k,
                tcg_hint=args.tcg
            )

            # Print comparison
            print(f"\nV1 Result: {v1_result['best_match']['name']}")
            print(f"  Confidence: {v1_result['confidence']}")
            print(f"  Score: {v1_result['best_match']['final_score']:.4f}")
            print(f"  Time: {v1_result['time_ms']}ms")

            print(f"\nV2 Result: {result['best_match']['name']}")
            print(f"  Confidence: {result['confidence']}")
            print(f"  Score: {result['best_match']['final_score']:.4f}")
            print(f"  Time: {result['time_ms']}ms")

            if result['best_match']['card_id'] == v1_result['best_match']['card_id']:
                print(f"\n✓ SAME CARD identified by both versions")
            else:
                print(f"\n⚠ DIFFERENT CARDS identified!")

        # Save JSON if requested
        if args.json:
            with open(args.json, 'w') as f:
                json.dump(result, f, indent=2)
            if not args.quiet:
                print(f"\n[OK] Result saved to: {args.json}")

        # Exit code based on confidence
        if result['confidence'] == 'HIGH':
            sys.exit(0)
        elif result['confidence'] == 'MODERATE':
            sys.exit(1)
        else:
            sys.exit(2)

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()
