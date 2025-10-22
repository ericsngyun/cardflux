#!/usr/bin/env python3
"""
Card Detection Module
Detects 0, 1, or multiple cards in an image using contour detection.

This is CRITICAL for production:
- Reject images with no cards
- Reject images with multiple cards
- Auto-crop to card bounding box
- Detect card rotation

Author: Senior Principal Engineer
Date: 2025-10-22
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path


class CardDetector:
    """
    Detects trading cards in images using contour detection.

    Features:
    - Detects rectangular card shapes
    - Filters by size (cards are ~63mm x 88mm, aspect ratio ~1.4)
    - Rejects images with 0 or 2+ cards
    - Returns cropped card image
    """

    def __init__(
        self,
        min_card_area_ratio: float = 0.1,  # Card must be at least 10% of image
        max_card_area_ratio: float = 0.9,  # Card must be at most 90% of image
        aspect_ratio_range: Tuple[float, float] = (1.2, 1.6),  # TCG cards ~1.4 ratio
        corner_detection: bool = True
    ):
        """
        Initialize card detector.

        Args:
            min_card_area_ratio: Minimum card area as fraction of image
            max_card_area_ratio: Maximum card area as fraction of image
            aspect_ratio_range: (min, max) aspect ratio for cards
            corner_detection: Use corner detection for better accuracy
        """
        self.min_card_area_ratio = min_card_area_ratio
        self.max_card_area_ratio = max_card_area_ratio
        self.aspect_ratio_min, self.aspect_ratio_max = aspect_ratio_range
        self.corner_detection = corner_detection

    def detect_cards(self, image_path: str) -> Dict:
        """
        Detect cards in image.

        Returns:
            {
                'num_cards': int,
                'status': 'NO_CARD' | 'SINGLE_CARD' | 'MULTIPLE_CARDS',
                'bounding_boxes': [{'x': int, 'y': int, 'w': int, 'h': int, 'confidence': float}],
                'primary_card': {'x': int, 'y': int, 'w': int, 'h': int} or None,
                'rotation_angle': float or None,
                'warnings': [str],
                'is_acceptable': bool
            }
        """
        image = cv2.imread(image_path)

        if image is None:
            return {
                'num_cards': 0,
                'status': 'ERROR',
                'bounding_boxes': [],
                'primary_card': None,
                'rotation_angle': None,
                'warnings': ['Could not load image'],
                'is_acceptable': False
            }

        # Find card contours
        cards = self._find_card_contours(image)

        # Determine status
        num_cards = len(cards)
        warnings = []

        if num_cards == 0:
            status = 'NO_CARD'
            is_acceptable = False
            warnings.append('No card detected in image')
            primary_card = None
            rotation_angle = None

        elif num_cards == 1:
            status = 'SINGLE_CARD'
            is_acceptable = True
            primary_card = cards[0]
            rotation_angle = self._estimate_rotation(image, primary_card)

            # Check if card is well-positioned
            if primary_card['confidence'] < 0.7:
                warnings.append('Card detection confidence low - card may be partially obscured')

        else:  # num_cards > 1
            status = 'MULTIPLE_CARDS'
            is_acceptable = False
            warnings.append(f'Multiple cards detected ({num_cards}) - please photograph one card at a time')

            # Pick largest card as primary (if user wants to proceed anyway)
            cards_sorted = sorted(cards, key=lambda c: c['w'] * c['h'], reverse=True)
            primary_card = cards_sorted[0]
            rotation_angle = self._estimate_rotation(image, primary_card)

        return {
            'num_cards': num_cards,
            'status': status,
            'bounding_boxes': cards,
            'primary_card': primary_card,
            'rotation_angle': rotation_angle,
            'warnings': warnings,
            'is_acceptable': is_acceptable
        }

    def _find_card_contours(self, image: np.ndarray) -> List[Dict]:
        """
        Find card-like rectangular contours in image.

        Returns:
            List of bounding boxes with confidence scores
        """
        h, w = image.shape[:2]
        image_area = h * w

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive threshold to handle varying lighting
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cards = []

        for contour in contours:
            # Get bounding rectangle
            x, y, w_box, h_box = cv2.boundingRect(contour)
            area = w_box * h_box

            # Check if size is appropriate for a card
            area_ratio = area / image_area

            if area_ratio < self.min_card_area_ratio or area_ratio > self.max_card_area_ratio:
                continue

            # Check aspect ratio (cards are ~1.4:1)
            aspect_ratio = max(w_box, h_box) / min(w_box, h_box)

            if aspect_ratio < self.aspect_ratio_min or aspect_ratio > self.aspect_ratio_max:
                continue

            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Cards should have 4 corners
            if self.corner_detection and len(approx) != 4:
                # Try to find 4 dominant corners
                corners = self._find_corners(contour)
                if len(corners) < 4:
                    continue

            # Calculate confidence based on how "rectangular" it is
            rect_area = w_box * h_box
            contour_area = cv2.contourArea(contour)
            rectangularity = contour_area / rect_area if rect_area > 0 else 0

            # Confidence: higher if more rectangular and good aspect ratio
            aspect_ratio_score = 1.0 - abs(aspect_ratio - 1.4) / 0.4  # Closer to 1.4 = better
            confidence = (rectangularity * 0.6 + aspect_ratio_score * 0.4)

            if confidence < 0.5:
                continue

            cards.append({
                'x': int(x),
                'y': int(y),
                'w': int(w_box),
                'h': int(h_box),
                'confidence': float(confidence),
                'area_ratio': float(area_ratio),
                'aspect_ratio': float(aspect_ratio)
            })

        # Sort by confidence
        cards.sort(key=lambda c: c['confidence'], reverse=True)

        return cards

    def _find_corners(self, contour: np.ndarray) -> List[Tuple[int, int]]:
        """Find 4 dominant corners in contour."""
        # Use Harris corner detection or similar
        # For now, use approxPolyDP with relaxed epsilon
        epsilon = 0.05 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        return [tuple(point[0]) for point in approx]

    def _estimate_rotation(self, image: np.ndarray, card_bbox: Dict) -> Optional[float]:
        """
        Estimate card rotation angle (0°, 90°, 180°, 270°).

        Uses aspect ratio and text direction detection.

        Returns:
            Rotation angle in degrees (0, 90, 180, 270) or None
        """
        # Extract card region
        x, y, w, h = card_bbox['x'], card_bbox['y'], card_bbox['w'], card_bbox['h']
        card_region = image[y:y+h, x:x+w]

        if card_region.size == 0:
            return None

        # Check aspect ratio
        # Cards are taller than wide (portrait orientation)
        # If w > h, card is likely rotated 90° or 270°
        if w > h:
            # Card is landscape - likely 90° or 270° rotation
            # Use text detection or other heuristics to determine which
            return 90.0  # Simplified for now
        else:
            # Card is portrait - likely 0° or 180°
            return 0.0

    def crop_to_card(self, image_path: str, padding: int = 10) -> Optional[np.ndarray]:
        """
        Detect card and return cropped image.

        Args:
            image_path: Path to image
            padding: Padding around card in pixels

        Returns:
            Cropped card image or None if detection failed
        """
        result = self.detect_cards(image_path)

        if result['status'] != 'SINGLE_CARD' or result['primary_card'] is None:
            return None

        image = cv2.imread(image_path)
        card = result['primary_card']

        # Extract with padding
        h, w = image.shape[:2]
        x1 = max(0, card['x'] - padding)
        y1 = max(0, card['y'] - padding)
        x2 = min(w, card['x'] + card['w'] + padding)
        y2 = min(h, card['y'] + card['h'] + padding)

        cropped = image[y1:y2, x1:x2]

        return cropped


def main():
    """Test card detection on sample images."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python card_detector.py <image_path>")
        return

    image_path = sys.argv[1]

    detector = CardDetector()
    result = detector.detect_cards(image_path)

    print("="*70)
    print("CARD DETECTION RESULT")
    print("="*70)
    print(f"\nImage: {Path(image_path).name}")
    print(f"Status: {result['status']}")
    print(f"Number of cards: {result['num_cards']}")
    print(f"Is acceptable: {result['is_acceptable']}")

    if result['warnings']:
        print(f"\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning}")

    if result['primary_card']:
        card = result['primary_card']
        print(f"\nPrimary Card:")
        print(f"  Position: ({card['x']}, {card['y']})")
        print(f"  Size: {card['w']}x{card['h']}")
        print(f"  Confidence: {card['confidence']:.3f}")
        print(f"  Aspect Ratio: {card['aspect_ratio']:.2f}")

        if result['rotation_angle'] is not None:
            print(f"  Rotation: {result['rotation_angle']:.0f}°")

    if len(result['bounding_boxes']) > 0:
        print(f"\nAll Detected Cards:")
        for i, card in enumerate(result['bounding_boxes'], 1):
            print(f"  {i}. {card['w']}x{card['h']} @ ({card['x']}, {card['y']}) - conf: {card['confidence']:.3f}")

    # Visualize (optional)
    if result['num_cards'] > 0:
        image = cv2.imread(image_path)

        for card in result['bounding_boxes']:
            color = (0, 255, 0) if card == result['primary_card'] else (0, 0, 255)
            cv2.rectangle(
                image,
                (card['x'], card['y']),
                (card['x'] + card['w'], card['y'] + card['h']),
                color,
                2
            )

        # Save visualization
        output_path = Path(image_path).parent / f"detected_{Path(image_path).name}"
        cv2.imwrite(str(output_path), image)
        print(f"\nVisualization saved to: {output_path}")


if __name__ == "__main__":
    main()
