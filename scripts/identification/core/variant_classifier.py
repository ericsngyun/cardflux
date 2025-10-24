#!/usr/bin/env python3
"""
Variant Classifier for Trading Card Identification

Classifies card variants (Alternate Art, Manga Rare, Parallel, Championship, etc.)
using multi-modal approach: visual similarity + text extraction + metadata matching.

Critical for One Piece TCG which has 15.5% variant cards (748/4815).

Architecture:
    Stage 1: Base card identification (card number)
    Stage 2: Variant candidate clustering (same card number)
    Stage 3: Visual fine-grained comparison (DINOv2 patch-level)
    Stage 4: Text extraction and matching (variant keywords)
    Stage 5: Multi-modal scoring and ranking

Author: Senior Principal Engineer
Date: 2025-10-16
"""
import sys
import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

warnings.filterwarnings('ignore')

try:
    import numpy as np
    import cv2
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModel
    import easyocr
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("\nPlease install: pip install numpy opencv-python pillow torch transformers easyocr")
    sys.exit(1)


class VariantType(Enum):
    """One Piece TCG variant types."""
    BASE = "base"
    ALTERNATE_ART = "alternate_art"
    MANGA_RARE = "manga_rare"
    PARALLEL = "parallel"
    SPECIAL = "special"
    CHAMPIONSHIP = "championship"
    WINNER = "winner"
    TREASURE = "treasure"
    PROMO = "promo"
    STAFF = "staff"
    WANTED_POSTER = "wanted_poster"
    ANNIVERSARY = "anniversary"
    JUDGE_PACK = "judge_pack"
    REPRINT = "reprint"
    UNKNOWN = "unknown"


@dataclass
class VariantCandidate:
    """Represents a card variant candidate."""
    card_id: str
    product_id: str
    name: str
    number: str
    variant_type: VariantType
    visual_similarity: float = 0.0
    text_match_score: float = 0.0
    foil_match_score: float = 0.0
    final_score: float = 0.0
    metadata: dict = None
    extracted_text: List[str] = None


class VariantClassifier:
    """
    Multi-modal variant classifier for One Piece TCG cards.

    Handles 15.5% of database (748 variant cards) including:
    - Alternate Art (341 cards)
    - Parallel (165 cards)
    - Winner/Championship (195 cards)
    - And many more...

    Uses:
    - DINOv2 patch-level visual comparison
    - EasyOCR text extraction
    - Foil detection matching
    - Metadata keyword analysis
    """

    def __init__(self, verbose: bool = True):
        """Initialize variant classifier."""
        self.verbose = verbose

        if self.verbose:
            print("="*70)
            print("VARIANT CLASSIFIER - Initializing")
            print("="*70)

        # Load DINOv2 for fine-grained visual comparison
        if self.verbose:
            print("\n[1/2] Loading DINOv2 vision model...")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
        self.model = AutoModel.from_pretrained("facebook/dinov2-small").to(self.device)
        self.model.eval()

        if self.verbose:
            print(f"  [OK] Model loaded on {self.device}")

        # Initialize OCR reader
        if self.verbose:
            print("\n[2/2] Initializing OCR (EasyOCR)...")

        self.ocr_reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available(), verbose=False)

        if self.verbose:
            print(f"  [OK] OCR ready")
            print("\n" + "="*70)
            print("VARIANT CLASSIFIER - Ready")
            print("="*70 + "\n")

    def classify_variant(
        self,
        query_image_path: str,
        base_card_number: str,
        variant_candidates: List[Dict],
        query_foil_detected: bool = False,
        query_foil_type: str = None
    ) -> List[VariantCandidate]:
        """
        Classify which variant of a card this image represents.

        Args:
            query_image_path: Path to query card image
            base_card_number: The card number (e.g., "OP09-093")
            variant_candidates: List of candidate variants with same card number
            query_foil_detected: Whether foil was detected on query
            query_foil_type: Type of foil detected (rainbow, holo, etc.)

        Returns:
            Ranked list of VariantCandidate objects with scores
        """
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"VARIANT CLASSIFICATION")
            print(f"{'='*70}")
            print(f"Base card number: {base_card_number}")
            print(f"Candidates: {len(variant_candidates)}")
            print(f"Query foil: {query_foil_detected} ({query_foil_type})")

        # Stage 1: Parse variant types from metadata
        if self.verbose:
            print(f"\n[Stage 1] Parsing variant types...")

        candidates = []
        for meta in variant_candidates:
            variant_type = self._detect_variant_type(meta['name'])

            candidate = VariantCandidate(
                card_id=meta.get('id', meta.get('card_id', '')),
                product_id=str(meta.get('productId', meta.get('product_id', ''))),
                name=meta['name'],
                number=meta.get('number', base_card_number),
                variant_type=variant_type,
                metadata=meta
            )
            candidates.append(candidate)

        if self.verbose:
            type_counts = {}
            for c in candidates:
                type_counts[c.variant_type.value] = type_counts.get(c.variant_type.value, 0) + 1
            print(f"  [OK] Variant types:")
            for vtype, count in sorted(type_counts.items()):
                print(f"    {vtype:20s}: {count} candidates")

        # Stage 2: Extract text from query image
        if self.verbose:
            print(f"\n[Stage 2] Text extraction from query...")

        query_text = self._extract_text(query_image_path)

        if self.verbose:
            if query_text:
                print(f"  [OK] Extracted {len(query_text)} text regions:")
                for text in query_text[:5]:  # Show first 5
                    print(f"    - {text}")
            else:
                print(f"  [--] No text extracted")

        # Stage 3: Visual fine-grained comparison
        if self.verbose:
            print(f"\n[Stage 3] Visual fine-grained comparison...")

        query_embedding = self._get_patch_embedding(query_image_path)

        for candidate in candidates:
            # Find candidate image
            candidate_image = self._find_candidate_image(candidate.card_id)

            if candidate_image:
                candidate_embedding = self._get_patch_embedding(candidate_image)
                similarity = self._compute_cosine_similarity(query_embedding, candidate_embedding)
                candidate.visual_similarity = similarity

        if self.verbose:
            avg_sim = np.mean([c.visual_similarity for c in candidates if c.visual_similarity > 0])
            print(f"  [OK] Average visual similarity: {avg_sim:.3f}")

        # Stage 4: Text matching score
        if self.verbose:
            print(f"\n[Stage 4] Text-based variant matching...")

        for candidate in candidates:
            text_score = self._compute_text_match_score(
                query_text,
                candidate.variant_type,
                candidate.name
            )
            candidate.text_match_score = text_score

        # Stage 5: Foil matching score
        if query_foil_detected:
            if self.verbose:
                print(f"\n[Stage 5] Foil-aware variant matching...")

            for candidate in candidates:
                foil_score = self._compute_foil_match_score(
                    candidate.name,
                    candidate.variant_type,
                    query_foil_type
                )
                candidate.foil_match_score = foil_score

        # Stage 6: Multi-modal fusion
        if self.verbose:
            print(f"\n[Stage 6] Multi-modal score fusion...")

        for candidate in candidates:
            # Adaptive weighting based on available signals
            weight_visual = 0.50
            weight_text = 0.30
            weight_foil = 0.20

            # If text extraction failed, rely more on visual
            if not query_text:
                weight_visual = 0.70
                weight_text = 0.10
                weight_foil = 0.20

            # If no foil detected, redistribute weight
            if not query_foil_detected:
                weight_visual = 0.60
                weight_text = 0.40
                weight_foil = 0.0

            # Compute final score
            final_score = (
                candidate.visual_similarity * weight_visual +
                candidate.text_match_score * weight_text +
                candidate.foil_match_score * weight_foil
            )

            candidate.final_score = final_score

        # Sort by final score (descending)
        candidates.sort(key=lambda x: x.final_score, reverse=True)

        if self.verbose:
            print(f"\n{'='*70}")
            print(f"TOP 5 VARIANT MATCHES")
            print(f"{'='*70}")
            for i, c in enumerate(candidates[:5], 1):
                print(f"\n{i}. {c.name}")
                print(f"   Type: {c.variant_type.value}")
                print(f"   Final Score: {c.final_score:.3f}")
                print(f"   - Visual:  {c.visual_similarity:.3f}")
                print(f"   - Text:    {c.text_match_score:.3f}")
                print(f"   - Foil:    {c.foil_match_score:.3f}")

        return candidates

    def _detect_variant_type(self, card_name: str) -> VariantType:
        """Detect variant type from card name."""
        name_lower = card_name.lower()

        # Priority order (most specific first)
        if 'manga' in name_lower:
            return VariantType.MANGA_RARE
        elif 'alternate art' in name_lower or 'alt art' in name_lower:
            return VariantType.ALTERNATE_ART
        elif 'wanted poster' in name_lower:
            return VariantType.WANTED_POSTER
        elif 'winner' in name_lower:
            return VariantType.WINNER
        elif 'championship' in name_lower:
            return VariantType.CHAMPIONSHIP
        elif 'anniversary' in name_lower:
            return VariantType.ANNIVERSARY
        elif 'judge pack' in name_lower:
            return VariantType.JUDGE_PACK
        elif 'treasure' in name_lower:
            return VariantType.TREASURE
        elif 'parallel' in name_lower:
            return VariantType.PARALLEL
        elif 'special' in name_lower:
            return VariantType.SPECIAL
        elif 'promo' in name_lower or 'promotion' in name_lower:
            return VariantType.PROMO
        elif 'staff' in name_lower:
            return VariantType.STAFF
        elif 'reprint' in name_lower:
            return VariantType.REPRINT
        elif '(' not in card_name or card_name.endswith(')'):
            # Likely base version (no parenthetical variant info)
            return VariantType.BASE
        else:
            return VariantType.UNKNOWN

    def _extract_text(self, image_path: str) -> List[str]:
        """Extract text from image using OCR."""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return []

            # Preprocess for better OCR
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # OCR
            results = self.ocr_reader.readtext(enhanced, detail=0)

            # Clean and filter results
            texts = []
            for text in results:
                text = text.strip()
                if len(text) >= 2:  # Minimum 2 characters
                    texts.append(text)

            return texts

        except Exception as e:
            if self.verbose:
                print(f"  Warning: OCR failed: {e}")
            return []

    def _get_patch_embedding(self, image_path: str) -> np.ndarray:
        """
        Get DINOv2 patch-level embedding for fine-grained comparison.

        Uses all patch tokens (not just CLS) for better variant discrimination.
        """
        image = Image.open(image_path).convert("RGB")

        # Preprocess (match identification pipeline)
        img_array = np.array(image)
        filtered = cv2.bilateralFilter(img_array, 5, 50, 50)
        enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)
        image = Image.fromarray(enhanced)

        # Generate embedding
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use mean of all patch tokens (not just CLS)
            # This captures more fine-grained details
            patch_embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()[0]

        # Normalize
        patch_embeddings = patch_embeddings / np.linalg.norm(patch_embeddings)
        return patch_embeddings

    def _compute_cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        return float(np.dot(emb1, emb2))

    def _compute_text_match_score(
        self,
        extracted_text: List[str],
        variant_type: VariantType,
        candidate_name: str
    ) -> float:
        """
        Compute text matching score based on extracted text and variant type.

        Higher score if extracted text contains variant-specific keywords.
        """
        if not extracted_text:
            return 0.0

        score = 0.0

        # Combine all extracted text
        all_text = ' '.join(extracted_text).lower()
        candidate_lower = candidate_name.lower()

        # Variant-specific keyword matching
        variant_keywords = {
            VariantType.MANGA_RARE: ['manga', 'mn', 'rare'],
            VariantType.ALTERNATE_ART: ['alternate', 'alt', 'art', 'aa'],
            VariantType.WANTED_POSTER: ['wanted', 'poster'],
            VariantType.PARALLEL: ['parallel', 'p-'],
            VariantType.CHAMPIONSHIP: ['championship', 'champ'],
            VariantType.WINNER: ['winner', '1st', 'first'],
            VariantType.ANNIVERSARY: ['anniversary', 'anniv'],
            VariantType.JUDGE_PACK: ['judge', 'pack'],
            VariantType.TREASURE: ['treasure'],
            VariantType.SPECIAL: ['special', 'sp'],
            VariantType.PROMO: ['promo', 'promotion'],
            VariantType.STAFF: ['staff'],
        }

        keywords = variant_keywords.get(variant_type, [])

        # Check for keyword matches
        matches = 0
        for keyword in keywords:
            if keyword in all_text:
                matches += 1

        if matches > 0:
            score += 0.5 + (matches * 0.1)  # 0.5 base + 0.1 per match

        # Check if card number appears in text
        if any(num in all_text for num in ['op09', 'op03', 'st03', 'st17'] if num in candidate_lower):
            score += 0.2

        # Cap at 1.0
        return min(score, 1.0)

    def _compute_foil_match_score(
        self,
        candidate_name: str,
        variant_type: VariantType,
        query_foil_type: str
    ) -> float:
        """
        Compute foil matching score.

        Higher score if candidate variant type aligns with detected foil type.
        """
        name_lower = candidate_name.lower()

        score = 0.0

        # Foil-heavy variants
        foil_variants = {
            VariantType.MANGA_RARE,
            VariantType.ALTERNATE_ART,
            VariantType.PARALLEL,
            VariantType.CHAMPIONSHIP,
            VariantType.WINNER,
            VariantType.SPECIAL
        }

        if variant_type in foil_variants:
            score += 0.5

        # Check for foil keywords in name
        foil_keywords = ['foil', 'holo', 'rainbow', 'texture', 'parallel', 'manga']
        for keyword in foil_keywords:
            if keyword in name_lower:
                score += 0.2
                break

        # Specific foil type matching
        if query_foil_type:
            if query_foil_type == 'rainbow' and 'rainbow' in name_lower:
                score += 0.3
            elif query_foil_type == 'texture' and ('manga' in name_lower or 'texture' in name_lower):
                score += 0.3

        # Cap at 1.0
        return min(score, 1.0)

    def _find_candidate_image(self, card_id: str) -> Optional[str]:
        """Find candidate image path."""
        images_dir = Path(__file__).parent.parent.parent / "data" / "images" / "one-piece"

        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            img_path = images_dir / f"{card_id}{ext}"
            if img_path.exists():
                return str(img_path)

        return None


def main():
    """Test variant classifier."""
    import argparse

    parser = argparse.ArgumentParser(description='Test variant classifier')
    parser.add_argument('image', help='Path to card image')
    parser.add_argument('--card-number', required=True, help='Base card number (e.g., OP09-093)')
    parser.add_argument('--metadata', required=True, help='Path to metadata JSON with candidates')

    args = parser.parse_args()

    # Load metadata
    with open(args.metadata, 'r') as f:
        candidates = json.load(f)

    # Initialize classifier
    classifier = VariantClassifier(verbose=True)

    # Classify
    results = classifier.classify_variant(
        query_image_path=args.image,
        base_card_number=args.card_number,
        variant_candidates=candidates,
        query_foil_detected=True,  # TODO: integrate with foil detector
        query_foil_type='texture'
    )

    print(f"\n{'='*70}")
    print(f"BEST MATCH: {results[0].name}")
    print(f"Variant Type: {results[0].variant_type.value}")
    print(f"Final Score: {results[0].final_score:.3f}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
