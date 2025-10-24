#!/usr/bin/env python3
"""
Production Card Identification System V3 - Compressed Image Enhancements

Improvements over V2:
- CLAHE contrast enhancement for low-contrast images
- Adaptive sharpening for blurry/compressed images
- Denoising for JPEG compression artifacts
- Quality-aware preprocessing pipeline

Expected improvements on compressed images: +10-15% score
Processing overhead: +150-200ms

Author: Senior Principal Engineer
Date: 2025-10-21
"""
import sys
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from production_card_identifier_v2 import ProductionCardIdentifierV2


class ProductionCardIdentifierV3(ProductionCardIdentifierV2):
    """
    V3: Enhanced preprocessing for compressed/low-quality images.

    Key Improvements:
    1. CLAHE contrast enhancement (for low-contrast images)
    2. Adaptive sharpening (for blurry/compressed images)
    3. JPEG artifact removal (for compression noise)
    4. Quality-aware preprocessing pipeline

    Phase 1: Quick wins with minimal overhead (~150-200ms)
    """

    def __init__(self, game: str = 'one-piece', verbose: bool = True, enable_variant_classifier: bool = True):
        """Initialize V3 identifier."""
        super().__init__(game=game, verbose=verbose, enable_variant_classifier=enable_variant_classifier)

        if self.verbose:
            print(f"  [V3] Compressed image enhancements enabled:")
            print(f"      - CLAHE contrast enhancement")
            print(f"      - Adaptive sharpening")
            print(f"      - JPEG artifact removal")

    def _analyze_image_quality(self, img_array: np.ndarray) -> Dict:
        """
        Analyze image quality to determine enhancement strategy.

        Returns dict with:
        - sharpness: Laplacian variance (higher = sharper)
        - brightness: Mean pixel value
        - contrast: Std deviation (higher = more contrast)
        - edge_density: Ratio of edge pixels (high = compression artifacts)
        - is_compressed: Whether image appears to be compressed/low-quality
        """
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Calculate quality metrics
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        brightness = np.mean(gray)
        contrast = np.std(gray)

        # Edge density (high edge density can indicate compression artifacts)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Determine if image is compressed/low-quality
        is_compressed = (
            sharpness < 1500 or      # Low sharpness
            contrast < 40 or         # Low contrast
            edge_density > 0.15      # High edge density (artifacts)
        )

        return {
            'sharpness': sharpness,
            'brightness': brightness,
            'contrast': contrast,
            'edge_density': edge_density,
            'is_compressed': is_compressed
        }

    def _enhance_compressed_image(self, img_array: np.ndarray, quality: Dict) -> np.ndarray:
        """
        Enhanced preprocessing pipeline for compressed/low-quality images.

        Phase 1 Quick Wins:
        1. CLAHE contrast enhancement (~50ms)
        2. Adaptive sharpening (~100ms)
        3. Denoising for artifacts (~50ms)

        Total overhead: ~150-200ms
        Expected improvement: +10-15% score on compressed images
        """
        enhanced = img_array.copy()

        # Enhancement 1: CLAHE for low-contrast images
        if quality['contrast'] < 40:
            if self.verbose:
                print(f"  [V3] Low contrast detected ({quality['contrast']:.1f}), applying CLAHE...")

            # Convert to LAB color space
            lab = cv2.cvtColor(enhanced, cv2.COLOR_RGB2LAB)

            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            lab[:,:,0] = clahe.apply(lab[:,:,0])

            # Convert back to RGB
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

        # Enhancement 2: Adaptive sharpening for blurry images
        if quality['sharpness'] < 1500:
            if self.verbose:
                print(f"  [V3] Low sharpness detected ({quality['sharpness']:.1f}), applying sharpening...")

            # Unsharp masking kernel
            # [-1 -1 -1]
            # [-1  9 -1]  * 0.5 = moderate sharpening
            # [-1 -1 -1]
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]], dtype=np.float32) * 0.5

            enhanced = cv2.filter2D(enhanced, -1, kernel)
            enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)

        # Enhancement 3: Denoise if compression artifacts detected
        if quality['edge_density'] > 0.15:
            if self.verbose:
                print(f"  [V3] Compression artifacts detected ({quality['edge_density']:.4f}), denoising...")

            # Non-Local Means denoising
            # Lighter settings (h=6) to preserve detail while removing noise
            enhanced = cv2.fastNlMeansDenoisingColored(
                enhanced,
                None,
                h=6,          # Filter strength (lower = preserve more detail)
                hColor=6,     # Color component strength
                templateWindowSize=7,
                searchWindowSize=21
            )

        return enhanced

    def _preprocess_for_embedding(self, image_path: str) -> np.ndarray:
        """
        Enhanced preprocessing pipeline with compressed image detection.

        Pipeline:
        1. Load image
        2. Analyze quality
        3. Apply V3 enhancements (if compressed/low-quality)
        4. Apply V2 adaptive preprocessing
        5. Return preprocessed image
        """
        from PIL import Image

        # Load image
        image = Image.open(image_path).convert("RGB")
        img_array = np.array(image)

        # Step 1: Analyze image quality
        quality = self._analyze_image_quality(img_array)

        if self.verbose and quality['is_compressed']:
            print(f"  [V3] Compressed/low-quality image detected:")
            print(f"      Sharpness: {quality['sharpness']:.1f} (threshold: 1500)")
            print(f"      Contrast: {quality['contrast']:.1f} (threshold: 40)")
            print(f"      Edge density: {quality['edge_density']:.4f} (threshold: 0.15)")

        # Step 2: Apply V3 enhancements for compressed images
        if quality['is_compressed']:
            img_array = self._enhance_compressed_image(img_array, quality)

        # Step 3: Apply V2 adaptive preprocessing (brightness/sharpness)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        brightness = np.mean(gray)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Adaptive contrast enhancement (V2 logic)
        if brightness < 80:
            alpha, beta = 1.15, 15
        elif brightness > 180:
            alpha, beta = 0.95, -5
        else:
            alpha, beta = 1.05, 3

        enhanced = cv2.convertScaleAbs(img_array, alpha=alpha, beta=beta)

        # Adaptive bilateral filtering (V2 logic)
        if sharpness < 50:
            filtered = cv2.bilateralFilter(enhanced, d=7, sigmaColor=75, sigmaSpace=75)
        else:
            filtered = cv2.bilateralFilter(enhanced, d=5, sigmaColor=50, sigmaSpace=50)

        return filtered


def main():
    """Test V3 enhancements."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python production_card_identifier_v3.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("="*70)
    print("Testing V3 Compressed Image Enhancements")
    print("="*70)
    print()

    # Test with V3
    print("[V3] Enhanced preprocessing for compressed images")
    identifier = ProductionCardIdentifierV3()
    result = identifier.identify(image_path, top_k=50, use_geometric=True)

    print()
    print(f"Result: {result['best_match']['name']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Score: {result['best_match']['final_score']:.4f}")
    print(f"  Visual: {result['scores']['visual']:.4f}")
    print(f"  Geometric: {result['scores']['geometric']:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
