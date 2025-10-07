#!/usr/bin/env python3
"""
OCR service for extracting text from trading cards.

Uses PaddleOCR for fast, accurate text extraction.
Optimized for One Piece TCG card name and number extraction.
"""
import re
from typing import Dict, List, Optional, Tuple
from PIL import Image
import numpy as np

class CardOCRService:
    """
    Extract text from trading card images using PaddleOCR.

    Focuses on:
    - Card name (top portion)
    - Card number (bottom portion, e.g., OP01-001)
    - Set code extraction
    """

    def __init__(self, lang='en'):
        """
        Initialize OCR service.

        Args:
            lang: Language code (default: 'en')
        """
        try:
            from paddleocr import PaddleOCR
            # Initialize PaddleOCR
            # use_angle_cls=True enables rotated text detection
            # show_log=False reduces noise
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                show_log=False,
                use_gpu=False  # Set to True if CUDA available
            )
            self.enabled = True
        except ImportError:
            print("WARNING: PaddleOCR not installed. OCR verification disabled.")
            print("Install with: pip install paddleocr")
            self.enabled = False

    def extract_text_from_image(self, image_path: str) -> List[Tuple[str, float]]:
        """
        Extract all text from an image with confidence scores.

        Args:
            image_path: Path to image file

        Returns:
            List of (text, confidence) tuples
        """
        if not self.enabled:
            return []

        try:
            result = self.ocr.ocr(image_path, cls=True)

            if not result or not result[0]:
                return []

            # Extract text and confidence
            text_results = []
            for line in result[0]:
                text = line[1][0]  # Text content
                conf = line[1][1]  # Confidence score
                text_results.append((text, conf))

            return text_results
        except Exception as e:
            print(f"OCR error on {image_path}: {e}")
            return []

    def extract_text_from_region(
        self,
        image: Image.Image,
        region: Tuple[int, int, int, int]
    ) -> List[Tuple[str, float]]:
        """
        Extract text from a specific region of an image.

        Args:
            image: PIL Image
            region: (x1, y1, x2, y2) bounding box

        Returns:
            List of (text, confidence) tuples
        """
        if not self.enabled:
            return []

        try:
            # Crop region
            cropped = image.crop(region)

            # Convert to numpy array
            img_array = np.array(cropped)

            # Run OCR
            result = self.ocr.ocr(img_array, cls=True)

            if not result or not result[0]:
                return []

            # Extract text and confidence
            text_results = []
            for line in result[0]:
                text = line[1][0]
                conf = line[1][1]
                text_results.append((text, conf))

            return text_results
        except Exception as e:
            print(f"OCR region error: {e}")
            return []

    def extract_card_info(self, image_path: str) -> Dict[str, any]:
        """
        Extract structured card information from image.

        For One Piece TCG:
        - Card name (top 30% of image)
        - Card number (bottom 20% of image, format: OP01-001, ST01-001, etc.)

        Args:
            image_path: Path to card image

        Returns:
            {
                'name': str,
                'name_confidence': float,
                'card_number': str,
                'number_confidence': float,
                'set_code': str,  # e.g., 'OP01'
                'collector_number': str,  # e.g., '001'
            }
        """
        if not self.enabled:
            return {}

        try:
            # Load image
            image = Image.open(image_path).convert("RGB")
            width, height = image.size

            # Define regions
            # Top 30% for card name
            name_region = (0, 0, width, int(height * 0.3))

            # Bottom 20% for card number
            number_region = (0, int(height * 0.8), width, height)

            # Extract text from regions
            name_texts = self.extract_text_from_region(image, name_region)
            number_texts = self.extract_text_from_region(image, number_region)

            # Process name (highest confidence text in top region)
            card_name = ""
            name_conf = 0.0
            if name_texts:
                # Get longest text with highest confidence
                card_name, name_conf = max(name_texts, key=lambda x: len(x[0]) * x[1])

            # Process card number (look for pattern like OP01-001)
            card_number = ""
            number_conf = 0.0
            set_code = ""
            collector_num = ""

            one_piece_pattern = re.compile(r'(OP|ST|PRB|P)\d+-\d+', re.IGNORECASE)

            for text, conf in number_texts:
                match = one_piece_pattern.search(text)
                if match:
                    card_number = match.group(0).upper()
                    number_conf = conf

                    # Split into set code and collector number
                    parts = card_number.split('-')
                    if len(parts) == 2:
                        set_code = parts[0]
                        collector_num = parts[1]
                    break

            return {
                'name': card_name.strip(),
                'name_confidence': float(name_conf),
                'card_number': card_number,
                'number_confidence': float(number_conf),
                'set_code': set_code,
                'collector_number': collector_num,
            }
        except Exception as e:
            print(f"Card info extraction error: {e}")
            return {}

    def fuzzy_match_name(self, extracted_name: str, candidate_name: str) -> float:
        """
        Calculate fuzzy match score between extracted and candidate names.

        Uses simple normalized Levenshtein distance.

        Args:
            extracted_name: Name from OCR
            candidate_name: Name from database

        Returns:
            Similarity score [0.0, 1.0]
        """
        if not extracted_name or not candidate_name:
            return 0.0

        # Normalize
        name1 = extracted_name.lower().strip()
        name2 = candidate_name.lower().strip()

        # Exact match
        if name1 == name2:
            return 1.0

        # Contains match
        if name1 in name2 or name2 in name1:
            return 0.8

        # Simple character overlap
        # More sophisticated: use python-Levenshtein or fuzzywuzzy
        common = set(name1) & set(name2)
        union = set(name1) | set(name2)

        if not union:
            return 0.0

        return len(common) / len(union)

    def exact_match_number(self, extracted_number: str, candidate_number: str) -> bool:
        """
        Check if card numbers match exactly.

        Args:
            extracted_number: Number from OCR (e.g., "OP01-001")
            candidate_number: Number from database

        Returns:
            True if exact match
        """
        if not extracted_number or not candidate_number:
            return False

        # Normalize
        num1 = extracted_number.upper().strip()
        num2 = candidate_number.upper().strip()

        return num1 == num2
