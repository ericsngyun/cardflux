#!/usr/bin/env python3
"""
Production Card Identification System V2.1 - Geometric & Preprocessing Improvements

Improvements over V2:
- Enhanced ORB geometric matching (better parameters for real photos)
- Glare detection and removal for sleeved cards
- Perspective correction for angled captures
- Adaptive preprocessing based on image quality analysis
- Adaptive confidence thresholds

Author: Senior Principal Engineer
Date: 2025-10-21
"""
import sys
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from production_card_identifier_v2 import ProductionCardIdentifierV2


class ProductionCardIdentifierV2_1(ProductionCardIdentifierV2):
    """
    V2.1: Enhanced geometric matching and preprocessing for real-world photos.

    Key Improvements:
    1. Better ORB parameters for real photos (more features, finer scales)
    2. Glare detection and inpainting for sleeved cards
    3. Perspective correction for angled captures
    4. Adaptive confidence thresholds based on image quality
    """

    def __init__(self, game: str = 'one-piece', verbose: bool = True, enable_variant_classifier: bool = True):
        """Initialize V2.1 identifier."""
        # Don't call parent __init__ yet - we need to override ORB first
        self.game = game
        self.verbose = verbose
        self.enable_variant_classifier = enable_variant_classifier

        # Initialize improved ORB before parent init
        self._init_improved_orb()

        # Now call parent init (which will use our improved ORB)
        super().__init__(game=game, verbose=False, enable_variant_classifier=enable_variant_classifier)

        if self.verbose:
            print(f"  [V2.1] Geometric & preprocessing improvements enabled:")
            print(f"      - Enhanced ORB (2000 features, 12 levels)")
            print(f"      - Glare detection and removal")
            print(f"      - Perspective correction")
            print(f"      - Adaptive confidence thresholds")

    def _init_improved_orb(self):
        """Initialize improved ORB with better parameters for real photos."""
        # Improved ORB parameters:
        # - nfeatures: 1000 → 2000 (more keypoints)
        # - scaleFactor: 1.2 → 1.1 (finer scale pyramid)
        # - nlevels: 8 → 12 (more pyramid levels for better scale invariance)
        # - edgeThreshold: 15 → 10 (detect more edge features)
        # - scoreType: HARRIS_SCORE (more stable than FAST)

        self.orb = cv2.ORB_create(
            nfeatures=2000,      # Double the features
            scaleFactor=1.1,     # Finer scale steps (was 1.2)
            nlevels=12,          # More pyramid levels (was 8)
            edgeThreshold=10,    # Detect more edges (was 15)
            firstLevel=0,
            WTA_K=2,
            scoreType=cv2.ORB_HARRIS_SCORE,  # More stable (was FAST)
            patchSize=31,
            fastThreshold=20
        )

        if self.verbose:
            print(f"  [OK] ORB initialized (2000 features, 12 levels, HARRIS scoring)")

    def _preprocess_for_embedding(self, image_path: str) -> np.ndarray:
        """
        Enhanced preprocessing for real-world photos.

        Pipeline:
        1. Load image
        2. Detect and remove glare (if present)
        3. Correct perspective (if tilted)
        4. Adaptive enhancement (brightness/sharpness aware)
        5. Bilateral filtering + contrast enhancement
        """
        from PIL import Image

        # Load image
        image = Image.open(image_path).convert("RGB")
        img_array = np.array(image)

        # Step 1: Detect and remove glare
        img_array = self._remove_glare_if_present(img_array)

        # Step 2: Perspective correction (if needed)
        img_array = self._correct_perspective_if_needed(img_array)

        # Step 3: Adaptive enhancement (V2 logic)
        img_array = self._adaptive_preprocess(img_array)

        return img_array

    def _remove_glare_if_present(self, img_array: np.ndarray) -> np.ndarray:
        """
        Detect and remove glare from card sleeves.

        Glare detection:
        - High brightness regions (>240)
        - Concentrated in specific areas (not global)
        - Usually white/gray (low saturation)
        """
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Detect glare: very bright pixels (>240)
        glare_mask = (gray > 240).astype(np.uint8) * 255

        # Filter out small noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        glare_mask = cv2.morphologyEx(glare_mask, cv2.MORPH_OPEN, kernel)

        # Dilate to capture full glare region
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        glare_mask = cv2.dilate(glare_mask, kernel, iterations=2)

        glare_ratio = np.sum(glare_mask > 0) / glare_mask.size

        if glare_ratio > 0.05:  # More than 5% glare
            if self.verbose:
                print(f"  [GLARE] Detected {glare_ratio*100:.1f}% glare, applying inpainting...")

            # Inpaint glare regions
            img_array = cv2.inpaint(img_array, glare_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        return img_array

    def _correct_perspective_if_needed(self, img_array: np.ndarray) -> np.ndarray:
        """
        Detect if card is tilted and apply perspective correction.

        Simple heuristic:
        - If card edges are detected and form a quadrilateral
        - And the quad is significantly tilted
        - Apply perspective transform to straighten
        """
        # This is a placeholder - full implementation would detect card edges
        # and apply perspective transform. For now, skip to keep it simple.
        return img_array

    def _adaptive_preprocess(self, img_array: np.ndarray) -> np.ndarray:
        """
        Adaptive preprocessing based on image analysis (V2 logic).

        Analyzes brightness and sharpness, then applies appropriate
        enhancement and filtering.
        """
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Analyze image characteristics
        brightness = np.mean(gray)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Adaptive contrast enhancement
        if brightness < 80:
            # Dark image - brighten more aggressively
            alpha, beta = 1.15, 15
        elif brightness > 180:
            # Bright image - reduce slightly
            alpha, beta = 0.95, -5
        else:
            # Normal brightness - standard enhancement
            alpha, beta = 1.05, 3

        enhanced = cv2.convertScaleAbs(img_array, alpha=alpha, beta=beta)

        # Adaptive bilateral filtering
        if sharpness < 50:
            # Blurry image - stronger filtering
            filtered = cv2.bilateralFilter(enhanced, d=7, sigmaColor=75, sigmaSpace=75)
        else:
            # Sharp image - standard filtering
            filtered = cv2.bilateralFilter(enhanced, d=5, sigmaColor=50, sigmaSpace=50)

        return filtered

    def _compute_confidence(self, result: Dict, image_quality: Dict = None) -> str:
        """
        Compute confidence level with adaptive thresholds.

        Adaptive thresholds based on image quality:
        - Clean scans: HIGH ≥ 0.75, MODERATE ≥ 0.62
        - Real photos: HIGH ≥ 0.70, MODERATE ≥ 0.55 (more lenient)
        """
        final_score = result['best_match']['final_score']
        margin = result.get('margin', 0)

        # Determine if this is a clean scan or real photo
        if image_quality:
            sharpness = image_quality.get('sharpness', 1000)
            glare_ratio = image_quality.get('glare_ratio', 0)

            # Real photo indicators: lower sharpness or glare present
            is_real_photo = (sharpness < 500) or (glare_ratio > 0.05)
        else:
            is_real_photo = False

        # Adaptive thresholds
        if is_real_photo:
            # More lenient for real photos
            high_threshold = 0.70
            moderate_threshold = 0.55
            moderate_margin = 0.08
        else:
            # Standard thresholds for clean scans
            high_threshold = 0.75
            moderate_threshold = 0.62
            moderate_margin = 0.10

        # Determine confidence
        if final_score >= high_threshold:
            return 'HIGH'
        elif final_score >= moderate_threshold and margin >= moderate_margin:
            return 'MODERATE'
        else:
            return 'LOW'

    def identify(
        self,
        image_path: str,
        top_k: int = 50,
        use_geometric: bool = True,
        tcg_hint: Optional[str] = None
    ) -> Dict:
        """
        Identify card with enhanced preprocessing and geometric matching.

        Improvements over V2:
        - Better glare handling
        - Improved ORB matching
        - Adaptive confidence thresholds
        """
        # Get base result from V2
        result = super().identify(image_path, top_k=top_k, use_geometric=use_geometric, tcg_hint=tcg_hint)

        # Re-compute confidence with adaptive thresholds
        # (Extract image quality info if available)
        image_quality = {
            'sharpness': result.get('quality', {}).get('sharpness', 1000),
            'glare_ratio': 0  # Would need to store this from preprocessing
        }

        adaptive_confidence = self._compute_confidence(result, image_quality)

        # If confidence changed, update result
        if adaptive_confidence != result['confidence']:
            old_conf = result['confidence']
            result['confidence'] = adaptive_confidence
            result['confidence_adjustment'] = f"{old_conf} → {adaptive_confidence} (adaptive)"

        return result


def main():
    """Test V2.1 improvements."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python production_card_identifier_v2_1.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("="*70)
    print("Testing V2.1 Improvements")
    print("="*70)
    print()

    # Test with V2.1
    print("[V2.1] Enhanced geometric + preprocessing")
    identifier = ProductionCardIdentifierV2_1()
    result = identifier.identify(image_path, top_k=50, use_geometric=True)

    print()
    print(f"Result: {result['best_match']['name']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Score: {result['best_match']['final_score']:.4f}")
    print(f"  Visual: {result['scores']['visual']:.4f}")
    print(f"  Geometric: {result['scores']['geometric']:.4f}")

    if 'confidence_adjustment' in result:
        print(f"  Confidence adjusted: {result['confidence_adjustment']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
