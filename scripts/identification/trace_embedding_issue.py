#!/usr/bin/env python3
"""
Trace why OptimizedCardIdentifier produces different embeddings than standalone.
"""
import sys
import numpy as np
import torch
import cv2
from pathlib import Path
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

MODEL_NAME = "facebook/dinov2-small"

def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess image."""
    img_array = np.array(image)
    filtered = cv2.bilateralFilter(img_array, 5, 50, 50)
    enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)
    return Image.fromarray(enhanced)

def get_embedding_method1(image_path, processor, model, device):
    """Method 1: As in OptimizedCardIdentifier (with self.processor, self.model)."""
    image = Image.open(image_path).convert("RGB")
    original_size = image.size
    min_dim = min(original_size)

    if min_dim < 400:
        image = preprocess_image(image)
        scale_factor = 400 / min_dim
        new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        image = preprocess_image(image)

    inputs = processor(images=image, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding

def main():
    image_path = "test-images/one-piece/blackbeard.png"

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # Load model
    processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(device)
    model.eval()

    # Get embedding
    emb = get_embedding_method1(image_path, processor, model, device)

    print(f"\nEmbedding stats:")
    print(f"  Shape: {emb.shape}")
    print(f"  Range: [{emb.min():.6f}, {emb.max():.6f}]")
    print(f"  Mean: {emb.mean():.6f}")
    print(f"  Norm: {np.linalg.norm(emb):.6f}")
    print(f"  First 5: {emb[:5]}")

    # Load FAISS and check
    import faiss
    import json

    index = faiss.read_index("artifacts/faiss/one-piece-dinov2/index.faiss")

    with open("artifacts/faiss/one-piece-dinov2/ids.json", 'r') as f:
        card_ids = json.load(f)

    with open("artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl", 'r') as f:
        metadata = {}
        for line in f:
            if line.strip():
                meta = json.loads(line)
                metadata[meta['id']] = meta

    distances, indices = index.search(np.array([emb]), 5)

    print(f"\nTop 5 matches:")
    for idx, (dist, index_id) in enumerate(zip(distances[0], indices[0])):
        card_id = card_ids[int(index_id)]
        meta = metadata.get(card_id, {})
        print(f"  {idx+1}. {meta.get('name', 'Unknown')} ({card_id}): {dist:.4f}")


if __name__ == "__main__":
    main()
