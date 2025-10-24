#!/usr/bin/env python3
"""
Universal Card Number Extraction System
Supports all major TCGs with position-aware, format-specific detection.

Supported TCGs:
- Magic: The Gathering (MTG)
- Yu-Gi-Oh!
- Pokémon
- One Piece Card Game
- Digimon Card Game
- Gundam (Battle Spirits)
- Disney Lorcana

Author: Senior Principal Engineer
"""
import re
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from PIL import Image


class TCG(Enum):
    """Supported Trading Card Games."""
    MTG = "magic"
    YUGIOH = "yugioh"
    POKEMON = "pokemon"
    ONE_PIECE = "one-piece"
    DIGIMON = "digimon"
    GUNDAM = "gundam"
    LORCANA = "lorcana"
    UNKNOWN = "unknown"


@dataclass
class CardNumberResult:
    """Result of card number extraction."""
    card_number: str
    tcg: TCG
    confidence: float
    region: str  # 'bottom_left', 'bottom_center', 'bottom_right'
    set_code: Optional[str] = None
    collector_number: Optional[str] = None
    variant_suffix: Optional[str] = None  # 's', 'a', 'p', etc.


class UniversalCardExtractor:
    """
    Production-grade card number extraction for all major TCGs.

    Features:
    - Multi-region scanning (bottom-left, center, right)
    - Format-specific pattern matching
    - TCG auto-detection
    - Robust OCR with multiple backends
    - Confidence scoring
    """

    # Card number regions (normalized coordinates: x1, y1, x2, y2)
    REGIONS = {
        'bottom_left': (0.0, 0.85, 0.35, 1.0),    # One Piece, Digimon, Lorcana
        'bottom_center': (0.30, 0.88, 0.70, 1.0),  # MTG
        'bottom_right': (0.65, 0.85, 1.0, 1.0),    # Yu-Gi-Oh, Pokémon, Gundam
    }

    # Card number patterns by TCG
    PATTERNS = {
        TCG.MTG: [
            r'\b(\d{1,3})[/ ](\d{1,3})([a-z])?\b',  # 247/302, 247/302s
            r'\b(\d{1,3})\b',                         # 42 (old cards)
        ],
        TCG.YUGIOH: [
            r'\b([A-Z]{3,5})-([A-Z]{2})(\d{3,4})\b',  # POTE-EN001
            r'\b([A-Z]{3,5})-(\d{3,4})\b',             # LOB-001 (older format)
        ],
        TCG.POKEMON: [
            r'\b(\d{1,3})/(\d{1,3})\b',               # 25/102
            r'\b([A-Z]{2,4})(\d{2,3})\b',             # SWSH001, XY01
            r'\b(TG)(\d{2})/TG\d{2}\b',               # TG01/TG30
        ],
        TCG.ONE_PIECE: [
            r'\b([A-Z]{2,4})(\d{2})-(\d{3})\b',       # ST02-004, OP01-001, PRB01-001
            r'\bP-(\d{3})\b',                          # P-001 (promo)
        ],
        TCG.DIGIMON: [
            r'\b([A-Z]{2,3})(\d{1,2})-(\d{3})(_P\d)?\b',  # BT1-001, ST1-01, BT1-001_P1
            r'\bP-(\d{3})\b',                              # P-001 (promo)
        ],
        TCG.GUNDAM: [
            r'\b([A-Z]{2})(\d{2})-(\d{3})\b',         # CB01-001
            r'\bP(\d{3})\b',                           # P001 (promo)
        ],
        TCG.LORCANA: [
            r'\b(\d{1,3})/(\d{1,3})\b',               # 123/204
            r'\bP(\d{3})\b',                           # P001 (promo)
        ],
    }

    # Set code patterns (for cards with separate set codes)
    SET_CODE_PATTERNS = {
        TCG.MTG: r'\b([A-Z]{3,4})\b',  # MOM, BRO, LCI
    }

    def __init__(self, ocr_backend='easy'):
        """
        Initialize universal card extractor.

        Args:
            ocr_backend: 'paddle' or 'easy' (default: 'easy')
        """
        self.ocr_backend = None
        self.ocr = None

        # Initialize OCR (prefer EasyOCR for multi-language support)
        try:
            if ocr_backend == 'paddle':
                from paddleocr import PaddleOCR
                self.ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='en',
                    show_log=False,
                    use_gpu=False
                )
                self.ocr_backend = 'paddle'
            else:
                import easyocr
                self.ocr = easyocr.Reader(['en'], gpu=False, verbose=False)
                self.ocr_backend = 'easy'
        except Exception as e:
            print(f"WARNING: OCR initialization failed: {e}")
            self.ocr_backend = None

    def extract_card_number(
        self,
        image_path: str,
        tcg_hint: Optional[TCG] = None
    ) -> Optional[CardNumberResult]:
        """
        Extract card number from image with TCG auto-detection.

        Args:
            image_path: Path to card image
            tcg_hint: Optional TCG hint to prioritize specific patterns

        Returns:
            CardNumberResult or None if extraction fails
        """
        if not self.ocr_backend:
            return None

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return None

        h, w = image.shape[:2]

        # Try all regions
        best_result = None
        best_confidence = 0.0

        for region_name, (x1, y1, x2, y2) in self.REGIONS.items():
            # Extract region
            region = image[
                int(h * y1):int(h * y2),
                int(w * x1):int(w * x2)
            ]

            # Apply preprocessing for better OCR
            region = self._preprocess_region(region)

            # Extract text from region
            texts = self._extract_text_from_region(region)

            # Try to match card numbers
            for text, conf in texts:
                result = self._match_card_number(text, conf, region_name, tcg_hint)

                if result and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence

        return best_result

    def _preprocess_region(self, region: np.ndarray) -> np.ndarray:
        """
        Preprocess region for better OCR accuracy.

        Args:
            region: Image region (numpy array)

        Returns:
            Preprocessed region
        """
        # Convert to grayscale
        if len(region.shape) == 3:
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        else:
            gray = region

        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(gray, 5, 50, 50)

        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(filtered)

        # Threshold to binary (helps with low contrast text)
        # Try Otsu's thresholding
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Also try inverse (white text on black background)
        _, binary_inv = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Use whichever has more white pixels (text should be minority)
        if np.sum(binary) < np.sum(binary_inv):
            return binary
        return binary_inv

    def _extract_text_from_region(self, region: np.ndarray) -> List[Tuple[str, float]]:
        """
        Extract text from preprocessed region.

        Args:
            region: Preprocessed region

        Returns:
            List of (text, confidence) tuples
        """
        texts = []

        try:
            if self.ocr_backend == 'paddle':
                result = self.ocr.ocr(region, cls=True)
                if result and result[0]:
                    for line in result[0]:
                        text = line[1][0]
                        conf = line[1][1]
                        texts.append((text, conf))

            elif self.ocr_backend == 'easy':
                result = self.ocr.readtext(region)
                for (bbox, text, conf) in result:
                    texts.append((text, conf))

        except Exception as e:
            print(f"OCR extraction error: {e}")

        return texts

    def _match_card_number(
        self,
        text: str,
        confidence: float,
        region: str,
        tcg_hint: Optional[TCG] = None
    ) -> Optional[CardNumberResult]:
        """
        Match extracted text against card number patterns.

        Args:
            text: Extracted text
            confidence: OCR confidence
            region: Region name where text was found
            tcg_hint: Optional TCG hint

        Returns:
            CardNumberResult if match found, None otherwise
        """
        # Normalize text
        text = text.strip().upper().replace(' ', '')

        # Prioritize TCG hint if provided
        tcgs_to_try = [tcg_hint] if tcg_hint else list(TCG)

        for tcg in tcgs_to_try:
            if tcg == TCG.UNKNOWN:
                continue

            patterns = self.PATTERNS.get(tcg, [])

            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    # Extract components
                    card_number = match.group(0)
                    set_code = None
                    collector_number = None
                    variant_suffix = None

                    # Parse based on TCG
                    if tcg == TCG.MTG:
                        # Format: 247/302s
                        if '/' in card_number:
                            parts = card_number.split('/')
                            collector_number = parts[0]
                            # Check for variant suffix
                            if len(match.groups()) >= 3 and match.group(3):
                                variant_suffix = match.group(3)

                    elif tcg == TCG.YUGIOH:
                        # Format: POTE-EN001
                        if '-' in card_number:
                            parts = card_number.split('-')
                            set_code = parts[0]
                            if len(parts) > 1:
                                # May have language code
                                if len(match.groups()) >= 2:
                                    collector_number = match.group(3) if len(match.groups()) >= 3 else match.group(2)

                    elif tcg in [TCG.ONE_PIECE, TCG.DIGIMON, TCG.GUNDAM]:
                        # Format: ST02-004
                        if '-' in card_number:
                            parts = card_number.split('-')
                            set_code = parts[0]
                            collector_number = parts[1]
                            # Check for variant suffix (Digimon _P1)
                            if len(match.groups()) >= 4 and match.group(4):
                                variant_suffix = match.group(4)

                    elif tcg in [TCG.POKEMON, TCG.LORCANA]:
                        # Format: 25/102
                        if '/' in card_number:
                            parts = card_number.split('/')
                            collector_number = parts[0]

                    # Adjust confidence based on region appropriateness
                    adjusted_confidence = self._adjust_confidence(
                        tcg, region, confidence
                    )

                    return CardNumberResult(
                        card_number=card_number,
                        tcg=tcg,
                        confidence=adjusted_confidence,
                        region=region,
                        set_code=set_code,
                        collector_number=collector_number,
                        variant_suffix=variant_suffix
                    )

        return None

    def _adjust_confidence(self, tcg: TCG, region: str, base_confidence: float) -> float:
        """
        Adjust confidence based on expected region for TCG.

        Args:
            tcg: Detected TCG
            region: Region where number was found
            base_confidence: Base OCR confidence

        Returns:
            Adjusted confidence [0.0, 1.0]
        """
        # Expected regions per TCG
        expected_regions = {
            TCG.MTG: 'bottom_center',
            TCG.YUGIOH: 'bottom_right',
            TCG.POKEMON: 'bottom_right',
            TCG.ONE_PIECE: 'bottom_left',
            TCG.DIGIMON: 'bottom_left',
            TCG.GUNDAM: 'bottom_right',
            TCG.LORCANA: 'bottom_left',
        }

        expected = expected_regions.get(tcg)

        # Boost confidence if found in expected region
        if region == expected:
            return min(base_confidence * 1.2, 1.0)

        # Slight penalty if found in unexpected region
        return base_confidence * 0.9

    def extract_set_code(
        self,
        image_path: str,
        tcg: TCG
    ) -> Optional[Tuple[str, float]]:
        """
        Extract set code for TCGs with separate set codes (e.g., MTG).

        Args:
            image_path: Path to card image
            tcg: TCG type

        Returns:
            (set_code, confidence) or None
        """
        if tcg not in self.SET_CODE_PATTERNS:
            return None

        # For MTG, set code is in bottom-left
        image = cv2.imread(image_path)
        if image is None:
            return None

        h, w = image.shape[:2]

        # MTG set code region (bottom-left, small area)
        x1, y1, x2, y2 = 0.0, 0.92, 0.25, 1.0
        region = image[
            int(h * y1):int(h * y2),
            int(w * x1):int(w * x2)
        ]

        # Preprocess
        region = self._preprocess_region(region)

        # Extract text
        texts = self._extract_text_from_region(region)

        # Match pattern
        pattern = self.SET_CODE_PATTERNS[tcg]
        for text, conf in texts:
            text = text.strip().upper()
            match = re.search(pattern, text)
            if match:
                set_code = match.group(1)
                # Validate: MTG set codes are 3-4 uppercase letters
                if 3 <= len(set_code) <= 4 and set_code.isalpha():
                    return (set_code, conf)

        return None


def main():
    """Test the universal card extractor."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python universal_card_extractor.py <image_path> [tcg_hint]")
        print("\nSupported TCG hints: mtg, yugioh, pokemon, one-piece, digimon, gundam, lorcana")
        sys.exit(1)

    image_path = sys.argv[1]
    tcg_hint = None

    if len(sys.argv) > 2:
        tcg_map = {
            'mtg': TCG.MTG,
            'yugioh': TCG.YUGIOH,
            'pokemon': TCG.POKEMON,
            'one-piece': TCG.ONE_PIECE,
            'digimon': TCG.DIGIMON,
            'gundam': TCG.GUNDAM,
            'lorcana': TCG.LORCANA,
        }
        tcg_hint = tcg_map.get(sys.argv[2].lower())

    # Initialize extractor
    print("Initializing Universal Card Extractor...")
    extractor = UniversalCardExtractor(ocr_backend='easy')

    # Extract card number
    print(f"\nExtracting card number from: {image_path}")
    result = extractor.extract_card_number(image_path, tcg_hint=tcg_hint)

    if result:
        print("\n" + "="*60)
        print("CARD NUMBER EXTRACTION RESULT")
        print("="*60)
        print(f"Card Number:      {result.card_number}")
        print(f"TCG:              {result.tcg.value}")
        print(f"Confidence:       {result.confidence:.3f}")
        print(f"Region:           {result.region}")
        if result.set_code:
            print(f"Set Code:         {result.set_code}")
        if result.collector_number:
            print(f"Collector #:      {result.collector_number}")
        if result.variant_suffix:
            print(f"Variant Suffix:   {result.variant_suffix}")
        print("="*60)

        # For MTG, also try to extract set code
        if result.tcg == TCG.MTG:
            set_result = extractor.extract_set_code(image_path, TCG.MTG)
            if set_result:
                set_code, conf = set_result
                print(f"\nExtracted Set Code: {set_code} (confidence: {conf:.3f})")
    else:
        print("\n[!] Failed to extract card number")


if __name__ == "__main__":
    main()
