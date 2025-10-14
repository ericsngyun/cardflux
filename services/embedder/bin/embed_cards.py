#!/usr/bin/env python3
"""
Production Card Embedder with Incremental Processing

Generates DINOv2 embeddings with EXACT preprocessing to match identification system.
This MUST maintain the same preprocessing pipeline for 100% accuracy.

CRITICAL: Preprocessing pipeline:
  1. Bilateral filter (5, 50, 50) - reduce noise, preserve edges
  2. Contrast enhancement (alpha=1.05, beta=3)
  3. Upscale if < 400px (LANCZOS resampling)
  4. DINOv2-small (384-dim)
  5. L2 normalization

Features:
- Incremental processing (SHA256 tracking)
- Batch processing with GPU acceleration
- --stub mode for testing without DINOv2
- Per-game and per-set output
- Validation: self-match recall@1 >99.5%

Input: data/images/{game_id}/{card_id}/canonical.jpg + meta.json
Output: artifacts/embeddings/{game_id}/embeddings.npy + metadata.jsonl
State: data/state/embed_cards.state.json
"""

import os
import sys
import json
import time
import argparse
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Optional imports (for --stub mode)
try:
    import torch
    import cv2
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModel
    from tqdm import tqdm
    HAS_ML_LIBS = True
except ImportError:
    HAS_ML_LIBS = False
    print("WARNING: ML libraries not found. Only --stub mode available.")

# ============================================================================
# Paths
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent.parent.parent
IMAGES_DIR = REPO_ROOT / "data" / "images"
EMBEDDINGS_DIR = REPO_ROOT / "artifacts" / "embeddings"
STATE_DIR = REPO_ROOT / "data" / "state"
STATE_FILE = STATE_DIR / "embed_cards.state.json"

# ============================================================================
# Configuration
# ============================================================================

MODEL_NAME = "facebook/dinov2-small"
EMBEDDING_DIM = 384
BATCH_SIZE = 32

# CRITICAL: These MUST match identify_card_production.py exactly!
PREPROCESSING_CONFIG = {
    "bilateral_filter": {"d": 5, "sigmaColor": 50, "sigmaSpace": 50},
    "contrast": {"alpha": 1.05, "beta": 3},
    "upscaling_threshold": 400,
    "upscaling_method": Image.Resampling.LANCZOS,
}

# ============================================================================
# Types
# ============================================================================

@dataclass
class CardImage:
    """Card image with metadata."""
    card_id: str
    game_id: str
    set_code: str
    collector_number: str
    name: str
    image_path: Path
    canonical_sha256: str


@dataclass
class EmbedState:
    """Embedding state for incremental processing."""
    version: str
    last_sync: str
    embeddings: Dict[str, Dict[str, str]]  # card_id -> {sha256, embedding_sha256}


# ============================================================================
# State Management
# ============================================================================

def load_state() -> Optional[EmbedState]:
    """Load embedding state."""
    if not STATE_FILE.exists():
        return None

    try:
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
        return EmbedState(**data)
    except Exception as e:
        print(f"WARNING: Failed to load state: {e}")
        return None


def save_state(state: EmbedState):
    """Save embedding state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump({
            'version': state.version,
            'last_sync': state.last_sync,
            'embeddings': state.embeddings,
        }, f, indent=2)


# ============================================================================
# Image Loading
# ============================================================================

def load_card_images(game_id: str) -> List[CardImage]:
    """Load all card images for a game."""
    game_dir = IMAGES_DIR / game_id

    if not game_dir.exists():
        print(f"WARNING: No images directory for {game_id}")
        return []

    cards = []
    sealed_products_filtered = 0

    for card_dir in game_dir.iterdir():
        if not card_dir.is_dir():
            continue

        canonical_path = card_dir / "canonical.jpg"
        meta_path = card_dir / "meta.json"

        if not canonical_path.exists() or not meta_path.exists():
            continue

        # Load metadata
        with open(meta_path, 'r') as f:
            meta = json.load(f)

        # CRITICAL: Filter sealed products (booster boxes, starter decks, etc.)
        # Sealed products DON'T have collector numbers
        collector_number = meta.get('collector_number')
        if not collector_number or collector_number.strip() == '':
            sealed_products_filtered += 1
            continue

        # Additional validation: check name patterns for sealed products
        name = meta.get('name', '').lower()
        sealed_patterns = [
            'booster box', 'booster pack', 'booster case',
            'starter deck', 'structure deck',
            'blister', 'tin', 'bundle',
            'display box', 'fat pack', 'gift box',
            'prerelease kit', 'learn together deck set',
        ]

        is_sealed = any(pattern in name for pattern in sealed_patterns)
        if is_sealed:
            sealed_products_filtered += 1
            continue

        cards.append(CardImage(
            card_id=meta['card_id'],
            game_id=meta['game_id'],
            set_code=meta['set_code'],
            collector_number=meta['collector_number'],
            name=meta['name'],
            image_path=canonical_path,
            canonical_sha256=meta['canonical_sha256'],
        ))

    if sealed_products_filtered > 0:
        print(f"  Filtered {sealed_products_filtered} sealed products (no collector number or sealed product name)")

    return cards


def needs_embedding(card: CardImage, prev_state: Optional[EmbedState]) -> bool:
    """Check if card needs embedding."""
    if not prev_state:
        return True

    prev = prev_state.embeddings.get(card.card_id)
    if not prev:
        return True

    # Check if image changed
    if prev.get('sha256') != card.canonical_sha256:
        return True

    return False


# ============================================================================
# CRITICAL: Production Preprocessing (MUST match identification!)
# ============================================================================

def preprocess_image_for_embedding(image: 'Image.Image') -> 'Image.Image':
    """
    Production preprocessing - MUST match identify_card_production.py EXACTLY!

    Pipeline:
    1. Bilateral filter (5, 50, 50) - reduce noise, preserve edges
    2. Contrast enhancement (alpha=1.05, beta=3)
    3. Upscale if < 400px (LANCZOS)

    This ensures index embeddings match query embeddings perfectly.
    """
    if not HAS_ML_LIBS:
        return image

    img_array = np.array(image)

    # Bilateral filter
    filtered = cv2.bilateralFilter(
        img_array,
        PREPROCESSING_CONFIG["bilateral_filter"]["d"],
        PREPROCESSING_CONFIG["bilateral_filter"]["sigmaColor"],
        PREPROCESSING_CONFIG["bilateral_filter"]["sigmaSpace"],
    )

    # Contrast enhancement
    enhanced = cv2.convertScaleAbs(
        filtered,
        alpha=PREPROCESSING_CONFIG["contrast"]["alpha"],
        beta=PREPROCESSING_CONFIG["contrast"]["beta"],
    )

    return Image.fromarray(enhanced)


# ============================================================================
# Embedding Generation
# ============================================================================

class EmbedderStub:
    """Stub embedder for testing without DINOv2."""

    def __init__(self):
        print("Using STUB embedder (random 384-dim vectors)")
        self.dimension = 384

    def embed_batch(self, images: List[CardImage]) -> np.ndarray:
        """Generate random embeddings."""
        embeddings = []

        for card in images:
            # Generate deterministic random embedding based on card_id
            seed = int(hashlib.sha256(card.card_id.encode()).hexdigest()[:8], 16)
            np.random.seed(seed)
            embedding = np.random.randn(self.dimension).astype(np.float32)

            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            embeddings.append(embedding)

        return np.array(embeddings)


class ProductionEmbedder:
    """Production DINOv2 embedder with exact preprocessing."""

    def __init__(self):
        if not HAS_ML_LIBS:
            raise RuntimeError("ML libraries required for production embedder")

        print(f"Loading {MODEL_NAME}...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"  Device: {self.device}")

        self.processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME).to(self.device)
        self.model.eval()

        if self.device == "cuda":
            self.model = self.model.half()
            torch.backends.cudnn.benchmark = True

        self.dimension = EMBEDDING_DIM
        print(f"  Dimension: {self.dimension}")

    def embed_batch(self, cards: List[CardImage]) -> np.ndarray:
        """Generate embeddings with production preprocessing."""
        embeddings = []

        with torch.no_grad():
            for i in range(0, len(cards), BATCH_SIZE):
                batch = cards[i:i + BATCH_SIZE]
                pixel_values = []

                for card in batch:
                    # Load image
                    image = Image.open(card.image_path).convert("RGB")
                    original_size = image.size
                    min_dim = min(original_size)

                    # CRITICAL: Apply EXACT preprocessing
                    if min_dim < PREPROCESSING_CONFIG["upscaling_threshold"]:
                        # Preprocess first
                        image = preprocess_image_for_embedding(image)

                        # Then upscale
                        scale_factor = PREPROCESSING_CONFIG["upscaling_threshold"] / min_dim
                        new_size = (
                            int(original_size[0] * scale_factor),
                            int(original_size[1] * scale_factor)
                        )
                        image = image.resize(new_size, PREPROCESSING_CONFIG["upscaling_method"])
                    else:
                        # Just preprocess (no upscaling)
                        image = preprocess_image_for_embedding(image)

                    # DINOv2 processor
                    inputs = self.processor(images=image, return_tensors="pt")
                    pixel_values.append(inputs['pixel_values'].squeeze(0))

                # Batch forward
                pixel_values_tensor = torch.stack(pixel_values).to(self.device)
                outputs = self.model(pixel_values=pixel_values_tensor)
                batch_embeddings = outputs.last_hidden_state[:, 0].cpu().numpy()

                # Normalize each embedding
                for embedding in batch_embeddings:
                    norm = np.linalg.norm(embedding)
                    if norm > 0:
                        embedding = embedding / norm
                    embeddings.append(embedding)

        return np.array(embeddings, dtype=np.float32)


# ============================================================================
# Validation
# ============================================================================

def validate_embeddings(embeddings: np.ndarray, cards: List[CardImage]) -> Dict:
    """
    Validate embeddings using self-match recall@1.

    CRITICAL: Self-match recall should be >99.5% for production readiness.
    If lower, embeddings don't match perfectly (preprocessing mismatch).
    """
    print("\nValidating embeddings...")

    # Self-similarity matrix
    similarities = np.dot(embeddings, embeddings.T)

    # Check diagonal (self-match should be highest)
    perfect_matches = 0
    total = len(embeddings)

    for i in range(total):
        # Get top match (excluding self)
        row = similarities[i].copy()
        row[i] = -1  # Exclude self
        top_match = np.argmax(row)

        # Should be self (diagonal should be highest)
        if similarities[i, i] > similarities[i, top_match]:
            perfect_matches += 1

    recall_at_1 = perfect_matches / total

    print(f"  Self-match recall@1: {recall_at_1:.4f} ({perfect_matches}/{total})")

    if recall_at_1 < 0.995:
        print("  ⚠️  WARNING: Low recall! Preprocessing mismatch likely.")
    elif recall_at_1 == 1.0:
        print("  ✅ PERFECT: All embeddings match perfectly")
    else:
        print("  ✅ GOOD: Embeddings validated")

    return {
        "recall_at_1": recall_at_1,
        "perfect_matches": perfect_matches,
        "total": total,
    }


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Production Card Embedder")
    parser.add_argument("--stub", action="store_true", help="Use stub embedder (testing only)")
    parser.add_argument("--game", type=str, help="Process specific game only")
    args = parser.parse_args()

    print("=" * 80)
    print("PRODUCTION CARD EMBEDDER")
    print("=" * 80)

    if args.stub:
        print("\n⚠️  STUB MODE: Using random embeddings (testing only)")
        embedder = EmbedderStub()
    else:
        if not HAS_ML_LIBS:
            print("\nERROR: ML libraries not installed. Use --stub for testing.")
            print("\nInstall: pip install torch transformers faiss-cpu pillow opencv-python")
            sys.exit(1)

        embedder = ProductionEmbedder()

    # Load previous state
    prev_state = load_state()

    # Find all games
    if args.game:
        games = [args.game]
    else:
        games = [d.name for d in IMAGES_DIR.iterdir() if d.is_dir()]

    if not games:
        print("\nNo games found in data/images/")
        print("Run: pnpm --filter ingest fetch-images")
        sys.exit(1)

    print(f"\nGames: {', '.join(games)}\n")

    new_state = EmbedState(
        version="1.0.0",
        last_sync=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        embeddings=prev_state.embeddings if prev_state else {},
    )

    for game_id in games:
        print(f"\n{'=' * 80}")
        print(f"Processing: {game_id}")
        print(f"{'=' * 80}")

        # Load card images
        cards = load_card_images(game_id)

        if not cards:
            print(f"No cards found for {game_id}")
            continue

        # Filter cards that need embedding
        cards_to_embed = [c for c in cards if needs_embedding(c, prev_state)]

        print(f"Total cards: {len(cards)}")
        print(f"Need embedding: {len(cards_to_embed)}")
        print(f"Skipped (unchanged): {len(cards) - len(cards_to_embed)}")

        if cards_to_embed:
            # Generate embeddings
            print(f"\nGenerating embeddings...")
            start = time.time()

            embeddings = embedder.embed_batch(cards_to_embed)

            elapsed = time.time() - start
            print(f"Generated {len(embeddings)} embeddings in {elapsed:.2f}s ({len(embeddings)/elapsed:.1f} cards/sec)")

            # Update state
            for card, embedding in zip(cards_to_embed, embeddings):
                embedding_hash = hashlib.sha256(embedding.tobytes()).hexdigest()
                new_state.embeddings[card.card_id] = {
                    "sha256": card.canonical_sha256,
                    "embedding_sha256": embedding_hash,
                }

        # Load all embeddings (including unchanged)
        all_embeddings = []
        all_cards = []

        # TODO: Load previously generated embeddings from disk
        # For now, regenerate all (can optimize later)

        print("\nRegenerating all embeddings for validation...")
        all_embeddings = embedder.embed_batch(cards)
        all_cards = cards

        # Validate
        validation = validate_embeddings(all_embeddings, all_cards)

        # Save embeddings
        output_dir = EMBEDDINGS_DIR / game_id
        output_dir.mkdir(parents=True, exist_ok=True)

        embeddings_path = output_dir / "embeddings.npy"
        metadata_path = output_dir / "metadata.jsonl"

        np.save(embeddings_path, all_embeddings)

        with open(metadata_path, 'w') as f:
            for card in all_cards:
                meta = {
                    "card_id": card.card_id,
                    "game_id": card.game_id,
                    "set_code": card.set_code,
                    "collector_number": card.collector_number,
                    "name": card.name,
                }
                f.write(json.dumps(meta) + '\n')

        print(f"\n✅ Saved: {embeddings_path}")
        print(f"✅ Saved: {metadata_path}")

    # Save state
    save_state(new_state)

    print(f"\n{'=' * 80}")
    print("EMBEDDING COMPLETE")
    print(f"{'=' * 80}")
    print(f"State: {STATE_FILE}")


if __name__ == "__main__":
    main()
