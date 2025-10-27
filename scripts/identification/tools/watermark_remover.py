#!/usr/bin/env python3
"""
Watermark Removal Utility for TCGPlayer SAMPLE Watermarks

Removes semi-transparent "SAMPLE" watermarks from card images to improve
visual similarity matching in DINOv2 embeddings.
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import warnings

warnings.filterwarnings('ignore')


class WatermarkRemover:
    """
    Removes TCGPlayer SAMPLE watermarks from card images.

    The watermark is a semi-transparent white text in the center of the image.
    We use inpainting to fill the watermark region based on surrounding pixels.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def detect_watermark_mask(self, image: np.ndarray, threshold: int = 200) -> np.ndarray:
        """
        Detect watermark region by finding very bright pixels in center area.

        Args:
            image: Input image (BGR or RGB)
            threshold: Brightness threshold for watermark detection (0-255)

        Returns:
            Binary mask where 255 = watermark pixel, 0 = clean pixel
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Create mask for very bright pixels (watermark is semi-transparent white)
        watermark_mask = np.zeros_like(gray, dtype=np.uint8)
        watermark_mask[gray > threshold] = 255

        # Focus on center region where watermark appears
        h, w = gray.shape
        center_mask = np.zeros_like(gray, dtype=np.uint8)
        center_mask[h//4:3*h//4, w//6:5*w//6] = 255

        # Combine: only bright pixels in center region
        watermark_mask = cv2.bitwise_and(watermark_mask, center_mask)

        # Morphological operations to clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        watermark_mask = cv2.morphologyEx(watermark_mask, cv2.MORPH_CLOSE, kernel)
        watermark_mask = cv2.morphologyEx(watermark_mask, cv2.MORPH_OPEN, kernel)

        # Dilate slightly to ensure we cover entire watermark
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        watermark_mask = cv2.dilate(watermark_mask, kernel_dilate, iterations=2)

        return watermark_mask

    def remove_watermark(self, image: np.ndarray, method: str = 'inpaint') -> Tuple[np.ndarray, bool]:
        """
        Remove watermark from image.

        Args:
            image: Input image (BGR or RGB)
            method: Removal method ('inpaint', 'blur', 'none')

        Returns:
            Tuple of (cleaned_image, watermark_detected)
        """
        # Detect watermark
        watermark_mask = self.detect_watermark_mask(image)

        # Check if watermark exists (>1% of image is watermarked)
        watermark_ratio = np.sum(watermark_mask > 0) / watermark_mask.size
        watermark_detected = watermark_ratio > 0.01

        if not watermark_detected:
            if self.verbose:
                print(f"  [INFO] No watermark detected (ratio: {watermark_ratio:.4f})")
            return image.copy(), False

        if self.verbose:
            print(f"  [INFO] Watermark detected (ratio: {watermark_ratio:.4f}), removing...")

        if method == 'none':
            return image.copy(), True

        # Remove watermark
        if method == 'inpaint':
            # Use Telea inpainting algorithm
            cleaned = cv2.inpaint(image, watermark_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        elif method == 'blur':
            # Alternative: blur the watermark region
            blurred = cv2.GaussianBlur(image, (21, 21), 0)
            cleaned = image.copy()
            cleaned[watermark_mask > 0] = blurred[watermark_mask > 0]
        else:
            raise ValueError(f"Unknown method: {method}")

        return cleaned, True

    def process_file(self, input_path: str, output_path: Optional[str] = None, method: str = 'inpaint') -> bool:
        """
        Process a single image file.

        Args:
            input_path: Path to input image
            output_path: Path to save cleaned image (optional)
            method: Removal method

        Returns:
            True if watermark was detected and removed
        """
        # Read image
        image = cv2.imread(input_path)
        if image is None:
            if self.verbose:
                print(f"  [ERROR] Failed to read: {input_path}")
            return False

        # Remove watermark
        cleaned, watermark_detected = self.remove_watermark(image, method=method)

        # Save if output path provided
        if output_path and watermark_detected:
            cv2.imwrite(output_path, cleaned)
            if self.verbose:
                print(f"  [OK] Saved cleaned image to: {output_path}")

        return watermark_detected

    def process_directory(self, input_dir: str, output_dir: Optional[str] = None, method: str = 'inpaint') -> dict:
        """
        Process all images in a directory.

        Args:
            input_dir: Directory containing images
            output_dir: Directory to save cleaned images (optional)
            method: Removal method

        Returns:
            Statistics dictionary
        """
        input_path = Path(input_dir)

        if not input_path.exists():
            raise ValueError(f"Input directory not found: {input_dir}")

        # Find all images
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        images = []
        for ext in image_extensions:
            images.extend(input_path.glob(f"*{ext}"))

        if self.verbose:
            print(f"\nProcessing {len(images)} images from {input_dir}...\n")

        # Process each image
        total = len(images)
        watermarked = 0
        clean = 0
        failed = 0

        for i, img_path in enumerate(images, 1):
            if self.verbose and i % 100 == 0:
                print(f"  Progress: {i}/{total} ({i/total*100:.1f}%)")

            try:
                # Determine output path
                out_path = None
                if output_dir:
                    out_dir = Path(output_dir)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path = str(out_dir / img_path.name)

                # Process
                detected = self.process_file(str(img_path), out_path, method=method)

                if detected:
                    watermarked += 1
                else:
                    clean += 1

            except Exception as e:
                if self.verbose:
                    print(f"  [ERROR] Failed to process {img_path.name}: {e}")
                failed += 1

        stats = {
            'total': total,
            'watermarked': watermarked,
            'clean': clean,
            'failed': failed,
            'watermark_rate': watermarked / total * 100 if total > 0 else 0
        }

        if self.verbose:
            print(f"\n{'='*60}")
            print("WATERMARK REMOVAL RESULTS")
            print(f"{'='*60}")
            print(f"Total images:      {stats['total']}")
            print(f"Watermarked:       {stats['watermarked']} ({stats['watermark_rate']:.1f}%)")
            print(f"Clean:             {stats['clean']} ({stats['clean']/total*100:.1f}%)")
            print(f"Failed:            {stats['failed']}")
            print(f"{'='*60}\n")

        return stats


def test_watermark_removal():
    """Test watermark removal on sample images."""
    remover = WatermarkRemover(verbose=True)

    # Test on known watermarked image
    test_image = "data/images/one-piece/593883.jpg"  # Radical Beam (Textured Foil)

    print(f"Testing watermark removal on: {test_image}")
    print("="*60)

    # Read image
    image = cv2.imread(test_image)
    if image is None:
        print(f"ERROR: Could not read {test_image}")
        return

    # Remove watermark
    cleaned, detected = remover.remove_watermark(image, method='inpaint')

    # Save result
    output_path = "test-results/watermark_removal_test.jpg"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, cleaned)

    print(f"\n[OK] Test complete!")
    print(f"  Watermark detected: {detected}")
    print(f"  Cleaned image saved to: {output_path}")

    # Show comparison
    mask = remover.detect_watermark_mask(image)
    mask_path = "test-results/watermark_mask.jpg"
    cv2.imwrite(mask_path, mask)
    print(f"  Watermark mask saved to: {mask_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_watermark_removal()
    else:
        print(__doc__)
        print("\nUsage:")
        print("  python watermark_remover.py test                    # Run test")
        print("  python -c 'from watermark_remover import ...'       # Use in script")
