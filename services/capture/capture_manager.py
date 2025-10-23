#!/usr/bin/env python3
"""
Capture Manager - Automated Card Image Collection System

Saves captured card images with rich metadata for future model improvement.
Creates a feedback loop: Demo captures → Training data → Better model → Better demos

Features:
- Auto-save every identification (optional)
- Multiple image formats (original, preprocessed, cropped)
- Rich metadata (confidence, OCR, features)
- User feedback tracking (correct/incorrect)
- Git-friendly structure
- Privacy compliant (no PII)

Author: Senior Principal Engineer
Date: 2025-10-23
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import warnings

warnings.filterwarnings('ignore')

try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError:
    print("WARNING: OpenCV/PIL not available. Install with: pip install opencv-python pillow")
    cv2 = None
    Image = None


class CaptureManager:
    """
    Manages capture storage and metadata for model improvement.

    Directory structure:
        data/captures/{game}/{date}/capture_{id}/
            ├── original.jpg       # High-res original photo
            ├── preprocessed.jpg   # After preprocessing
            ├── cropped.jpg        # Auto-cropped card only
            └── metadata.json      # Full capture metadata
    """

    def __init__(self, base_dir: str = None, auto_save: bool = True):
        """
        Initialize capture manager.

        Args:
            base_dir: Base directory for captures (default: data/captures/)
            auto_save: Auto-save every identification (default: True)
        """
        if base_dir is None:
            # Default to repo root / data / captures
            base_dir = Path(__file__).parent.parent.parent / "data" / "captures"

        self.base_dir = Path(base_dir)
        self.auto_save = auto_save

        # Create base directory
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats_file = self.base_dir / "statistics.json"
        self.stats = self._load_statistics()

    def save_capture(
        self,
        image_path: str,
        identification_result: Dict,
        game: str = "one-piece",
        save_original: bool = True,
        save_preprocessed: bool = True,
        save_cropped: bool = True,
    ) -> Dict:
        """
        Save captured card image with metadata.

        Args:
            image_path: Path to captured image
            identification_result: Full identification result dict
            game: Game name (default: one-piece)
            save_original: Save high-res original (default: True)
            save_preprocessed: Save preprocessed image (default: True)
            save_cropped: Save cropped card only (default: True)

        Returns:
            Capture info with capture_id and paths
        """
        if not self.auto_save:
            return {"capture_id": None, "skipped": True, "reason": "auto_save disabled"}

        # Generate unique capture ID
        capture_id = self._generate_capture_id()

        # Create capture directory
        today = datetime.now().strftime("%Y-%m-%d")
        capture_dir = self.base_dir / game / today / f"capture_{capture_id}"
        capture_dir.mkdir(parents=True, exist_ok=True)

        # Save images
        saved_images = {}

        if save_original and os.path.exists(image_path):
            original_path = capture_dir / "original.jpg"
            shutil.copy2(image_path, original_path)
            saved_images['original'] = str(original_path.relative_to(self.base_dir))

        if save_cropped and cv2 is not None:
            cropped_path = self._save_cropped_card(image_path, capture_dir / "cropped.jpg")
            if cropped_path:
                saved_images['cropped'] = str(cropped_path.relative_to(self.base_dir))

        # Create metadata
        metadata = self._create_metadata(
            capture_id=capture_id,
            game=game,
            saved_images=saved_images,
            identification_result=identification_result,
            image_path=image_path
        )

        # Save metadata
        metadata_path = capture_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Update index
        self._update_index(game, capture_id, metadata)

        # Update statistics
        self._update_statistics(game, metadata)

        return {
            "capture_id": capture_id,
            "capture_dir": str(capture_dir),
            "saved_images": saved_images,
            "metadata_path": str(metadata_path)
        }

    def mark_feedback(
        self,
        capture_id: str,
        game: str,
        correct: bool,
        true_id: Optional[int] = None,
        notes: Optional[str] = None
    ):
        """
        Add user feedback to a capture.

        Args:
            capture_id: Capture ID to update
            game: Game name
            correct: Was identification correct?
            true_id: If incorrect, the correct product ID
            notes: Optional notes
        """
        # Find capture metadata
        metadata_path = self._find_capture_metadata(capture_id, game)
        if not metadata_path:
            raise FileNotFoundError(f"Capture {capture_id} not found")

        # Load metadata
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # Update feedback
        metadata['user_feedback'] = {
            'correct': correct,
            'true_id': true_id,
            'notes': notes,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Save updated metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Update statistics
        self.stats['user_verified'][
            'correct' if correct else 'incorrect'
        ] += 1
        self._save_statistics()

        return metadata

    def get_captures_by_date(
        self,
        game: str,
        date: str,
        confidence_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all captures for a specific date.

        Args:
            game: Game name
            date: Date string (YYYY-MM-DD)
            confidence_filter: Filter by confidence (HIGH/MODERATE/LOW)

        Returns:
            List of capture metadata
        """
        date_dir = self.base_dir / game / date
        if not date_dir.exists():
            return []

        captures = []
        for capture_dir in date_dir.glob("capture_*"):
            metadata_path = capture_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                # Apply confidence filter
                if confidence_filter:
                    if metadata['identification']['confidence'] != confidence_filter:
                        continue

                captures.append(metadata)

        return captures

    def get_statistics(self) -> Dict:
        """Get capture statistics."""
        return self.stats

    def cleanup_old_captures(self, days: int = 30):
        """
        Delete captures older than N days.

        Args:
            days: Delete captures older than this many days
        """
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0

        for game_dir in self.base_dir.glob("*/"):
            if not game_dir.is_dir():
                continue

            for date_dir in game_dir.glob("*/"):
                if not date_dir.is_dir():
                    continue

                # Check if directory is old
                dir_mtime = date_dir.stat().st_mtime
                if dir_mtime < cutoff_date:
                    # Delete directory
                    shutil.rmtree(date_dir)
                    deleted_count += 1

        print(f"Cleaned up {deleted_count} old capture directories (>{days} days)")

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _generate_capture_id(self) -> str:
        """Generate unique capture ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(os.urandom(8)).hexdigest()[:6]
        return f"{timestamp}_{random_suffix}"

    def _save_cropped_card(self, image_path: str, output_path: Path) -> Optional[Path]:
        """
        Auto-crop card from image and save.

        Args:
            image_path: Path to original image
            output_path: Where to save cropped image

        Returns:
            Path to cropped image, or None if failed
        """
        if cv2 is None:
            return None

        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return None

            # Simple card detection (you can enhance this)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Find largest contour (likely the card)
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)

                # Add small padding
                padding = 10
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(img.shape[1] - x, w + 2*padding)
                h = min(img.shape[0] - y, h + 2*padding)

                # Crop
                cropped = img[y:y+h, x:x+w]

                # Save
                cv2.imwrite(str(output_path), cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
                return output_path

            return None

        except Exception as e:
            print(f"Warning: Failed to crop card: {e}")
            return None

    def _create_metadata(
        self,
        capture_id: str,
        game: str,
        saved_images: Dict,
        identification_result: Dict,
        image_path: str
    ) -> Dict:
        """Create metadata dictionary for capture."""
        # Extract identification info
        best_match = identification_result.get('best_match', {})
        scores = identification_result.get('scores', {})
        features = identification_result.get('features', {})
        timing = identification_result.get('timing', {})

        # Auto-detect capture conditions
        conditions = self._detect_capture_conditions(image_path)

        metadata = {
            "capture_id": capture_id,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "game": game,

            "images": saved_images,

            "identification": {
                "predicted_id": best_match.get('product_id'),
                "predicted_name": best_match.get('name'),
                "predicted_number": best_match.get('number'),
                "confidence": identification_result.get('confidence'),
                "final_score": scores.get('final', 0.0),
                "visual_score": scores.get('visual', 0.0),
                "geometric_score": scores.get('geometric', 0.0),
                "top_3_matches": [
                    {
                        "id": m.get('product_id'),
                        "name": m.get('name'),
                        "number": m.get('number'),
                        "score": m.get('final_score', 0.0)
                    }
                    for m in identification_result.get('top_matches', [])[:3]
                ] if 'top_matches' in identification_result else []
            },

            "features": {
                "ocr_detected": features.get('cardNumber') is not None,
                "ocr_number": features.get('cardNumber'),
                "ocr_confidence": getattr(features.get('cardNumber'), 'confidence', 0.0) if features.get('cardNumber') else 0.0,
                "foil_detected": features.get('foil', False),
                "foil_type": features.get('foilType', 'none'),
                "quality_score": identification_result.get('quality_check', {}).get('sharpness_score', 0.0)
            },

            "user_feedback": {
                "correct": None,
                "true_id": None,
                "notes": None
            },

            "capture_conditions": conditions,

            "performance": {
                "total_ms": timing.get('total_ms', 0),
                "dinov2_ms": timing.get('dinov2_ms', 0),
                "faiss_ms": timing.get('faiss_ms', 0),
                "geometric_ms": timing.get('geometric_ms', 0)
            },

            "version": {
                "app_version": "0.2.2",
                "model_version": "dinov2-small-v1",
                "identifier_version": "v3.2"
            }
        }

        return metadata

    def _detect_capture_conditions(self, image_path: str) -> Dict:
        """Auto-detect capture conditions from image."""
        conditions = {
            "lighting": "unknown",
            "distance": "unknown",
            "orientation": "unknown"
        }

        if cv2 is None:
            return conditions

        try:
            img = cv2.imread(image_path)
            if img is None:
                return conditions

            # Detect lighting (brightness)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)

            if brightness < 80:
                conditions['lighting'] = 'poor'
            elif brightness < 150:
                conditions['lighting'] = 'moderate'
            else:
                conditions['lighting'] = 'good'

            # Detect distance (card size relative to frame)
            h, w = img.shape[:2]
            frame_area = h * w

            # Simple thresholding to detect card
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                card_area = cv2.contourArea(largest_contour)
                area_ratio = card_area / frame_area

                if area_ratio > 0.6:
                    conditions['distance'] = 'close_up'
                elif area_ratio > 0.3:
                    conditions['distance'] = 'medium'
                else:
                    conditions['distance'] = 'far'

            # Detect orientation (simplified - just check aspect ratio)
            aspect = w / h
            if 0.6 <= aspect <= 0.8:
                conditions['orientation'] = 'upright'
            elif 1.25 <= aspect <= 1.67:
                conditions['orientation'] = 'rotated_90'
            else:
                conditions['orientation'] = 'unknown'

        except Exception:
            pass

        return conditions

    def _update_index(self, game: str, capture_id: str, metadata: Dict):
        """Update captures index (JSONL format)."""
        index_file = self.base_dir / game / "captures_index.jsonl"
        index_file.parent.mkdir(parents=True, exist_ok=True)

        # Append to index
        with open(index_file, 'a', encoding='utf-8') as f:
            index_entry = {
                "capture_id": capture_id,
                "timestamp": metadata['timestamp'],
                "predicted_name": metadata['identification']['predicted_name'],
                "confidence": metadata['identification']['confidence'],
                "capture_dir": f"{datetime.now().strftime('%Y-%m-%d')}/capture_{capture_id}"
            }
            f.write(json.dumps(index_entry, ensure_ascii=False) + '\n')

    def _find_capture_metadata(self, capture_id: str, game: str) -> Optional[Path]:
        """Find metadata file for a capture ID."""
        game_dir = self.base_dir / game

        for date_dir in game_dir.glob("*/"):
            metadata_path = date_dir / f"capture_{capture_id}" / "metadata.json"
            if metadata_path.exists():
                return metadata_path

        return None

    def _load_statistics(self) -> Dict:
        """Load capture statistics."""
        if self.stats_file.exists():
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Default statistics
        return {
            "total_captures": 0,
            "by_game": {},
            "by_confidence": {
                "HIGH": 0,
                "MODERATE": 0,
                "LOW": 0
            },
            "user_verified": {
                "correct": 0,
                "incorrect": 0,
                "unverified": 0
            },
            "storage_size_mb": 0.0,
            "last_updated": datetime.utcnow().isoformat() + 'Z'
        }

    def _update_statistics(self, game: str, metadata: Dict):
        """Update capture statistics."""
        self.stats['total_captures'] += 1

        # By game
        if game not in self.stats['by_game']:
            self.stats['by_game'][game] = 0
        self.stats['by_game'][game] += 1

        # By confidence
        confidence = metadata['identification']['confidence']
        if confidence in self.stats['by_confidence']:
            self.stats['by_confidence'][confidence] += 1

        # User verified (starts unverified)
        self.stats['user_verified']['unverified'] += 1

        # Update timestamp
        self.stats['last_updated'] = datetime.utcnow().isoformat() + 'Z'

        self._save_statistics()

    def _save_statistics(self):
        """Save statistics to disk."""
        # Calculate storage size
        total_size = sum(
            f.stat().st_size
            for f in self.base_dir.rglob('*') if f.is_file()
        )
        self.stats['storage_size_mb'] = total_size / (1024 * 1024)

        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2)


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Capture Manager CLI")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show capture statistics')

    # List command
    list_parser = subparsers.add_parser('list', help='List captures')
    list_parser.add_argument('--game', default='one-piece', help='Game name')
    list_parser.add_argument('--date', help='Date (YYYY-MM-DD)')
    list_parser.add_argument('--confidence', choices=['HIGH', 'MODERATE', 'LOW'], help='Filter by confidence')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Delete old captures')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Delete captures older than N days')

    args = parser.parse_args()

    manager = CaptureManager()

    if args.command == 'stats':
        stats = manager.get_statistics()
        print(json.dumps(stats, indent=2))

    elif args.command == 'list':
        date = args.date or datetime.now().strftime("%Y-%m-%d")
        captures = manager.get_captures_by_date(args.game, date, args.confidence)
        print(f"Found {len(captures)} captures for {args.game} on {date}")
        for cap in captures:
            print(f"  - {cap['capture_id']}: {cap['identification']['predicted_name']} ({cap['identification']['confidence']})")

    elif args.command == 'cleanup':
        manager.cleanup_old_captures(args.days)

    else:
        parser.print_help()
