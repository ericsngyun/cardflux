#!/usr/bin/env python3
"""
Card Detection Module for Live Camera Feed

Detects trading cards in video frames using edge detection and contour analysis.
Handles cards at various distances, angles, and positions in frame.

Features:
- Real-time card boundary detection
- Edge-based contour detection
- Perspective correction for angled cards
- Auto-crop to card boundaries
- Quality validation (blur, glare, lighting)

Author: Senior Principal Engineer
Date: 2025-10-16
"""
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from enum import Enum


class CardDetectionStatus(Enum):
    """Status of card detection"""
    NO_CARD = "no_card"
    CARD_DETECTED = "card_detected"
    CARD_TOO_FAR = "card_too_far"
    CARD_TOO_CLOSE = "card_too_close"
    CARD_ANGLED = "card_angled"
    CARD_READY = "card_ready"
    POOR_LIGHTING = "poor_lighting"
    TOO_BLURRY = "too_blurry"
    GLARE_DETECTED = "glare_detected"


@dataclass
class CardDetectionResult:
    """Result of card detection"""
    status: CardDetectionStatus
    confidence: float  # 0.0 to 1.0
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
    corners: Optional[np.ndarray] = None  # 4 corners of card
    cropped_card: Optional[np.ndarray] = None  # Cropped and perspective-corrected image
    quality_score: float = 0.0  # 0.0 to 1.0
    warnings: List[str] = None  # Warnings about image quality

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class CardDetector:
    """
    Detects trading cards in camera frames using edge detection.

    Uses multi-stage pipeline:
    1. Preprocessing (grayscale, blur, edge detection)
    2. Contour detection and filtering
    3. Card shape validation (aspect ratio, area)
    4. Perspective correction
    5. Quality validation
    """

    # Standard TCG card aspect ratio (2.5" x 3.5" = 0.714)
    CARD_ASPECT_RATIO = 2.5 / 3.5  # Width / Height
    ASPECT_RATIO_TOLERANCE = 0.15  # 15% tolerance

    # Minimum/maximum card size (as fraction of frame)
    MIN_CARD_AREA = 0.05  # 5% of frame
    MAX_CARD_AREA = 0.85  # 85% of frame
    OPTIMAL_CARD_AREA = 0.30  # 30% of frame

    # Edge detection thresholds
    CANNY_LOW = 50
    CANNY_HIGH = 150

    # Quality thresholds
    MIN_SHARPNESS = 50  # Laplacian variance
    MIN_BRIGHTNESS = 50
    MAX_BRIGHTNESS = 220
    MAX_GLARE_THRESHOLD = 240  # Pixel values above this are glare

    def __init__(self, frame_width: int = 1920, frame_height: int = 1080):
        """
        Initialize card detector.

        Args:
            frame_width: Width of camera frame
            frame_height: Height of camera frame
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.frame_area = frame_width * frame_height

    def detect_card(self, frame: np.ndarray, return_visualization: bool = False) -> CardDetectionResult:
        """
        Detect card in frame.

        Args:
            frame: Input frame (BGR color image from camera)
            return_visualization: If True, include visualization overlay

        Returns:
            CardDetectionResult with status, bbox, and cropped card
        """
        if frame is None or frame.size == 0:
            return CardDetectionResult(
                status=CardDetectionStatus.NO_CARD,
                confidence=0.0,
                warnings=["Empty frame"]
            )

        # Stage 1: Preprocessing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # Stage 2: Edge detection
        edges = cv2.Canny(filtered, self.CANNY_LOW, self.CANNY_HIGH)

        # Dilate edges to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Stage 3: Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return CardDetectionResult(
                status=CardDetectionStatus.NO_CARD,
                confidence=0.0,
                warnings=["No contours detected"]
            )

        # Stage 4: Find card-like contour
        card_contour = self._find_card_contour(contours)

        if card_contour is None:
            return CardDetectionResult(
                status=CardDetectionStatus.NO_CARD,
                confidence=0.0,
                warnings=["No card-shaped contour found"]
            )

        # Stage 5: Approximate contour to quadrilateral
        epsilon = 0.02 * cv2.arcLength(card_contour, True)
        approx = cv2.approxPolyDP(card_contour, epsilon, True)

        # We need 4 corners for a card
        if len(approx) != 4:
            return CardDetectionResult(
                status=CardDetectionStatus.CARD_DETECTED,
                confidence=0.5,
                warnings=[f"Contour has {len(approx)} corners (expected 4)"]
            )

        # Stage 6: Get card corners and bounding box
        corners = approx.reshape(4, 2)
        x, y, w, h = cv2.boundingRect(card_contour)

        # Stage 7: Validate card properties
        card_area = w * h
        area_ratio = card_area / self.frame_area
        aspect_ratio = w / h if h > 0 else 0

        # Check aspect ratio (allow rotation - could be 0.714 or 1.4)
        expected_ratios = [self.CARD_ASPECT_RATIO, 1.0 / self.CARD_ASPECT_RATIO]
        aspect_valid = any(
            abs(aspect_ratio - expected) < self.ASPECT_RATIO_TOLERANCE
            for expected in expected_ratios
        )

        warnings = []
        status = CardDetectionStatus.CARD_DETECTED

        # Check size
        if area_ratio < self.MIN_CARD_AREA:
            status = CardDetectionStatus.CARD_TOO_FAR
            warnings.append(f"Card too far (covers {area_ratio*100:.1f}% of frame)")
        elif area_ratio > self.MAX_CARD_AREA:
            status = CardDetectionStatus.CARD_TOO_CLOSE
            warnings.append(f"Card too close (covers {area_ratio*100:.1f}% of frame)")

        # Check aspect ratio
        if not aspect_valid:
            status = CardDetectionStatus.CARD_ANGLED
            warnings.append(f"Card aspect ratio unusual: {aspect_ratio:.2f}")

        # Stage 8: Perspective correction
        cropped_card = self._correct_perspective(frame, corners, aspect_ratio)

        if cropped_card is None:
            return CardDetectionResult(
                status=status,
                confidence=0.5,
                bbox=(x, y, w, h),
                corners=corners,
                warnings=warnings + ["Perspective correction failed"]
            )

        # Stage 9: Quality validation
        quality_result = self._check_quality(cropped_card)

        # Update status based on quality
        if quality_result['is_blurry']:
            status = CardDetectionStatus.TOO_BLURRY
            warnings.append("Card image is blurry")

        if quality_result['has_glare']:
            status = CardDetectionStatus.GLARE_DETECTED
            warnings.append("Glare detected on card")

        if quality_result['poor_lighting']:
            status = CardDetectionStatus.POOR_LIGHTING
            warnings.append("Poor lighting conditions")

        # If all checks passed and card is good size, mark as READY
        if (status == CardDetectionStatus.CARD_DETECTED and
            self.MIN_CARD_AREA * 1.5 < area_ratio < self.MAX_CARD_AREA * 0.8):
            status = CardDetectionStatus.CARD_READY

        # Calculate confidence score
        confidence = self._calculate_confidence(
            aspect_valid=aspect_valid,
            area_ratio=area_ratio,
            quality_score=quality_result['quality_score']
        )

        return CardDetectionResult(
            status=status,
            confidence=confidence,
            bbox=(x, y, w, h),
            corners=corners,
            cropped_card=cropped_card,
            quality_score=quality_result['quality_score'],
            warnings=warnings
        )

    def _find_card_contour(self, contours: List[np.ndarray]) -> Optional[np.ndarray]:
        """
        Find the contour most likely to be a card.

        Args:
            contours: List of detected contours

        Returns:
            Best card contour or None
        """
        best_contour = None
        best_score = 0

        for contour in contours:
            # Calculate area
            area = cv2.contourArea(contour)

            # Skip if too small or too large
            area_ratio = area / self.frame_area
            if area_ratio < self.MIN_CARD_AREA or area_ratio > self.MAX_CARD_AREA:
                continue

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)

            # Calculate aspect ratio
            aspect_ratio = w / h if h > 0 else 0

            # Score based on aspect ratio and area
            expected_ratios = [self.CARD_ASPECT_RATIO, 1.0 / self.CARD_ASPECT_RATIO]
            aspect_score = max([
                1.0 - abs(aspect_ratio - expected) / expected
                for expected in expected_ratios
            ])

            # Prefer cards near optimal size
            size_score = 1.0 - abs(area_ratio - self.OPTIMAL_CARD_AREA) / self.OPTIMAL_CARD_AREA
            size_score = max(0, min(1.0, size_score))

            # Combined score
            score = aspect_score * 0.7 + size_score * 0.3

            if score > best_score:
                best_score = score
                best_contour = contour

        return best_contour if best_score > 0.5 else None

    def _correct_perspective(self, frame: np.ndarray, corners: np.ndarray, aspect_ratio: float) -> Optional[np.ndarray]:
        """
        Apply perspective correction to extract card.

        Args:
            frame: Input frame
            corners: 4 corners of card
            aspect_ratio: Detected aspect ratio

        Returns:
            Perspective-corrected card image or None
        """
        try:
            # Sort corners: top-left, top-right, bottom-right, bottom-left
            corners = self._sort_corners(corners)

            # Calculate output dimensions
            # Standard card is 2.5" x 3.5", target 600px height
            if abs(aspect_ratio - self.CARD_ASPECT_RATIO) < abs(aspect_ratio - (1.0 / self.CARD_ASPECT_RATIO)):
                # Card is oriented normally (portrait)
                output_w = int(600 * self.CARD_ASPECT_RATIO)
                output_h = 600
            else:
                # Card is rotated (landscape)
                output_w = 600
                output_h = int(600 * self.CARD_ASPECT_RATIO)

            # Define destination corners
            dst_corners = np.array([
                [0, 0],
                [output_w - 1, 0],
                [output_w - 1, output_h - 1],
                [0, output_h - 1]
            ], dtype=np.float32)

            # Calculate perspective transform
            corners_float = corners.astype(np.float32)
            matrix = cv2.getPerspectiveTransform(corners_float, dst_corners)

            # Apply transform
            result = cv2.warpPerspective(frame, matrix, (output_w, output_h))

            return result
        except Exception as e:
            print(f"[CardDetector] Perspective correction error: {e}")
            return None

    def _sort_corners(self, corners: np.ndarray) -> np.ndarray:
        """
        Sort corners in order: top-left, top-right, bottom-right, bottom-left.

        Args:
            corners: 4x2 array of corner coordinates

        Returns:
            Sorted corners
        """
        # Calculate centroid
        centroid = np.mean(corners, axis=0)

        # Calculate angles from centroid
        angles = np.arctan2(corners[:, 1] - centroid[1], corners[:, 0] - centroid[0])

        # Sort by angle
        sorted_indices = np.argsort(angles)
        sorted_corners = corners[sorted_indices]

        # Rotate so top-left is first (smallest y + x)
        sums = sorted_corners[:, 0] + sorted_corners[:, 1]
        top_left_idx = np.argmin(sums)
        sorted_corners = np.roll(sorted_corners, -top_left_idx, axis=0)

        return sorted_corners

    def _check_quality(self, image: np.ndarray) -> Dict:
        """
        Check image quality (sharpness, lighting, glare).

        Args:
            image: Cropped card image

        Returns:
            Dictionary with quality metrics
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Check sharpness (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = laplacian.var()
        is_blurry = sharpness < self.MIN_SHARPNESS

        # Check brightness
        brightness = np.mean(gray)
        poor_lighting = brightness < self.MIN_BRIGHTNESS or brightness > self.MAX_BRIGHTNESS

        # Check for glare (bright spots)
        glare_pixels = np.sum(gray > self.MAX_GLARE_THRESHOLD)
        glare_ratio = glare_pixels / gray.size
        has_glare = glare_ratio > 0.05  # More than 5% bright pixels

        # Calculate overall quality score
        sharpness_score = min(1.0, sharpness / 200.0)  # Normalize to 0-1
        brightness_score = 1.0 - abs(brightness - 135) / 135  # Optimal around 135
        brightness_score = max(0, min(1.0, brightness_score))
        glare_score = 1.0 - (glare_ratio / 0.1)  # Penalize glare
        glare_score = max(0, min(1.0, glare_score))

        quality_score = (sharpness_score * 0.5 + brightness_score * 0.3 + glare_score * 0.2)

        return {
            'is_blurry': is_blurry,
            'poor_lighting': poor_lighting,
            'has_glare': has_glare,
            'sharpness': sharpness,
            'brightness': brightness,
            'glare_ratio': glare_ratio,
            'quality_score': quality_score
        }

    def _calculate_confidence(self, aspect_valid: bool, area_ratio: float, quality_score: float) -> float:
        """
        Calculate overall detection confidence.

        Args:
            aspect_valid: Whether aspect ratio is valid
            area_ratio: Card area as fraction of frame
            quality_score: Image quality score (0-1)

        Returns:
            Confidence score (0-1)
        """
        # Aspect ratio component
        aspect_conf = 1.0 if aspect_valid else 0.5

        # Size component (prefer cards near optimal size)
        size_diff = abs(area_ratio - self.OPTIMAL_CARD_AREA)
        size_conf = max(0, 1.0 - (size_diff / self.OPTIMAL_CARD_AREA))

        # Combine
        confidence = aspect_conf * 0.4 + size_conf * 0.3 + quality_score * 0.3

        return max(0, min(1.0, confidence))

    def create_visualization(self, frame: np.ndarray, result: CardDetectionResult) -> np.ndarray:
        """
        Create visualization overlay showing detection result.

        Args:
            frame: Input frame
            result: Detection result

        Returns:
            Frame with visualization overlay
        """
        vis = frame.copy()

        # Draw card boundary if detected
        if result.corners is not None:
            # Determine color based on status
            if result.status == CardDetectionStatus.CARD_READY:
                color = (0, 255, 0)  # Green
            elif result.status in [CardDetectionStatus.TOO_BLURRY, CardDetectionStatus.GLARE_DETECTED]:
                color = (0, 165, 255)  # Orange
            elif result.status in [CardDetectionStatus.CARD_TOO_FAR, CardDetectionStatus.CARD_TOO_CLOSE]:
                color = (0, 255, 255)  # Yellow
            else:
                color = (255, 0, 0)  # Blue

            # Draw card outline
            cv2.polylines(vis, [result.corners.astype(np.int32)], True, color, 3)

            # Draw corner circles
            for corner in result.corners:
                cv2.circle(vis, tuple(corner.astype(int)), 8, color, -1)

        # Draw status text
        status_text = result.status.value.replace('_', ' ').title()
        conf_text = f"Conf: {result.confidence:.0%}"
        quality_text = f"Quality: {result.quality_score:.0%}"

        # Background for text
        cv2.rectangle(vis, (10, 10), (400, 120), (0, 0, 0), -1)

        # Status
        cv2.putText(vis, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(vis, conf_text, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(vis, quality_text, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Draw warnings
        if result.warnings:
            y_offset = 150
            for warning in result.warnings[:3]:  # Show max 3 warnings
                cv2.putText(vis, f"! {warning}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                y_offset += 25

        return vis


def test_card_detector():
    """Test card detector with webcam."""
    import sys

    detector = CardDetector()

    # Open webcam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    print("Card Detector Test")
    print("==================")
    print("Press SPACE to capture card")
    print("Press Q to quit")
    print("")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect card
        result = detector.detect_card(frame)

        # Create visualization
        vis = detector.create_visualization(frame, result)

        # Show result
        cv2.imshow('Card Detection', cv2.resize(vis, (960, 540)))

        # Handle keys
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            if result.status == CardDetectionStatus.CARD_READY and result.cropped_card is not None:
                # Save cropped card
                filename = f"card_capture_{int(time.time())}.jpg"
                cv2.imwrite(filename, result.cropped_card)
                print(f"Saved: {filename}")
            else:
                print(f"Cannot capture: {result.status.value}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    import time
    test_card_detector()
