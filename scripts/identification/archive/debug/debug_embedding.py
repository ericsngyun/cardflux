#!/usr/bin/env python3
"""
Debug script to compare embedding generation between standalone and class implementation.
"""
import sys
import json
import numpy as np
import faiss
import torch
import cv2
from pathlib import Path
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "metadata"
FAISS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "faiss"
IMAGES_DIR = Path(__file__).parent.parent.parent / "data" / "images"

MODEL_NAME = "facebook/dinov2-small"
GAME = "one-piece"

def get_embedding_standalone(image_path: str, processor, model, device):
    """Standalone version - proven to work correctly."""
    print("\n=== STANDALONE EMBEDDING ===")

    image = Image.open(image_path).convert("RGB")
    print(f"1. Loaded image: {image.size}")

    original_size = image.size
    min_dim = min(original_size)
    print(f"2. Min dimension: {min_dim}px")

    if min_dim < 400:
        print("3. Applying preprocessing (small image)...")
        img_array = np.array(image)
        print(f"   - Array shape: {img_array.shape}, dtype: {img_array.dtype}")
        print(f"   - Array range: [{img_array.min()}, {img_array.max()}]")

        filtered = cv2.bilateralFilter(img_array, 5, 50, 50)
        print(f"   - After bilateral: range [{filtered.min()}, {filtered.max()}]")

        enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)
        print(f"   - After enhance: range [{enhanced.min()}, {enhanced.max()}]")

        image = Image.fromarray(enhanced)

        scale_factor = 400 / min_dim
        new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
        print(f"4. Upscaling: {original_size} -> {new_size} (factor: {scale_factor:.2f})")
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        print("3. Applying preprocessing (large image)...")
        img_array = np.array(image)
        filtered = cv2.bilateralFilter(img_array, 5, 50, 50)
        enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)
        image = Image.fromarray(enhanced)

    print(f"5. Final preprocessed size: {image.size}")

    inputs = processor(images=image, return_tensors="pt").to(device)
    print(f"6. Processor output shape: {inputs['pixel_values'].shape}")
    print(f"   - Pixel value range: [{inputs['pixel_values'].min().item():.4f}, {inputs['pixel_values'].max().item():.4f}]")

    with torch.no_grad():
        outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

    print(f"7. Raw embedding shape: {embedding.shape}")
    print(f"   - Embedding range: [{embedding.min():.6f}, {embedding.max():.6f}]")
    print(f"   - Embedding mean: {embedding.mean():.6f}, std: {embedding.std():.6f}")

    norm = np.linalg.norm(embedding)
    print(f"8. L2 norm: {norm:.6f}")

    if norm > 0:
        embedding = embedding / norm

    print(f"9. Normalized embedding:")
    print(f"   - Range: [{embedding.min():.6f}, {embedding.max():.6f}]")
    print(f"   - Mean: {embedding.mean():.6f}, std: {embedding.std():.6f}")
    print(f"   - L2 norm: {np.linalg.norm(embedding):.6f}")
    print(f"   - First 10 values: {embedding[:10]}")

    return embedding


def get_embedding_class_style(image_path: str, processor, model, device):
    """Class implementation - replicating OptimizedCardIdentifier.get_image_embedding()."""
    print("\n=== CLASS-STYLE EMBEDDING ===")

    image = Image.open(image_path).convert("RGB")
    print(f"1. Loaded image: {image.size}")

    original_size = image.size
    min_dim = min(original_size)
    print(f"2. Min dimension: {min_dim}px")

    if min_dim < 400:
        print("3. Applying preprocessing (small image)...")
        img_array = np.array(image)
        print(f"   - Array shape: {img_array.shape}, dtype: {img_array.dtype}")
        print(f"   - Array range: [{img_array.min()}, {img_array.max()}]")

        filtered = cv2.bilateralFilter(img_array, 5, 50, 50)
        print(f"   - After bilateral: range [{filtered.min()}, {filtered.max()}]")

        enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)
        print(f"   - After enhance: range [{enhanced.min()}, {enhanced.max()}]")

        image = Image.fromarray(enhanced)

        scale_factor = 400 / min_dim
        new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
        print(f"4. Upscaling: {original_size} -> {new_size} (factor: {scale_factor:.2f})")
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        print("3. Applying preprocessing (large image)...")
        img_array = np.array(image)
        filtered = cv2.bilateralFilter(img_array, 5, 50, 50)
        enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)
        image = Image.fromarray(enhanced)

    print(f"5. Final preprocessed size: {image.size}")

    inputs = processor(images=image, return_tensors="pt").to(device)
    print(f"6. Processor output shape: {inputs['pixel_values'].shape}")
    print(f"   - Pixel value range: [{inputs['pixel_values'].min().item():.4f}, {inputs['pixel_values'].max().item():.4f}]")

    with torch.no_grad():
        outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

    print(f"7. Raw embedding shape: {embedding.shape}")
    print(f"   - Embedding range: [{embedding.min():.6f}, {embedding.max():.6f}]")
    print(f"   - Embedding mean: {embedding.mean():.6f}, std: {embedding.std():.6f}")

    norm = np.linalg.norm(embedding)
    print(f"8. L2 norm: {norm:.6f}")

    if norm > 0:
        embedding = embedding / norm

    print(f"9. Normalized embedding:")
    print(f"   - Range: [{embedding.min():.6f}, {embedding.max():.6f}]")
    print(f"   - Mean: {embedding.mean():.6f}, std: {embedding.std():.6f}")
    print(f"   - L2 norm: {np.linalg.norm(embedding):.6f}")
    print(f"   - First 10 values: {embedding[:10]}")

    return embedding


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_embedding.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    if not Path(image_path).exists():
        print(f"ERROR: Image not found at {image_path}")
        sys.exit(1)

    print("=" * 80)
    print("EMBEDDING GENERATION DEBUG")
    print(f"Image: {image_path}")
    print("=" * 80)

    # Load model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nDevice: {device}")

    print("\nLoading model...")
    processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(device)
    model.eval()

    # Generate embeddings both ways
    emb1 = get_embedding_standalone(image_path, processor, model, device)
    emb2 = get_embedding_class_style(image_path, processor, model, device)

    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)

    print(f"\nAre embeddings identical? {np.allclose(emb1, emb2, atol=1e-6)}")
    print(f"Max absolute difference: {np.abs(emb1 - emb2).max():.10f}")
    print(f"Mean absolute difference: {np.abs(emb1 - emb2).mean():.10f}")

    # Load FAISS and test
    print("\n" + "=" * 80)
    print("FAISS SEARCH COMPARISON")
    print("=" * 80)

    index_file = FAISS_DIR / f"{GAME}-dinov2" / "index.faiss"
    ids_file = FAISS_DIR / f"{GAME}-dinov2" / "ids.json"

    index = faiss.read_index(str(index_file))

    with open(ids_file, 'r', encoding='utf-8') as f:
        card_ids = json.load(f)

    metadata_file = ARTIFACTS_DIR / "embeddings" / f"{GAME}-dinov2" / "metadata.jsonl"
    metadata = {}
    with open(metadata_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                meta = json.loads(line)
                metadata[meta['id']] = meta

    print("\nStandalone embedding search:")
    distances1, indices1 = index.search(np.array([emb1]), 5)
    for idx, (dist, index_id) in enumerate(zip(distances1[0], indices1[0])):
        card_id = card_ids[int(index_id)]
        meta = metadata.get(card_id, {})
        print(f"  {idx+1}. {meta.get('name', 'Unknown')} ({card_id}): {dist:.4f}")

    print("\nClass-style embedding search:")
    distances2, indices2 = index.search(np.array([emb2]), 5)
    for idx, (dist, index_id) in enumerate(zip(distances2[0], indices2[0])):
        card_id = card_ids[int(index_id)]
        meta = metadata.get(card_id, {})
        print(f"  {idx+1}. {meta.get('name', 'Unknown')} ({card_id}): {dist:.4f}")


if __name__ == "__main__":
    main()
