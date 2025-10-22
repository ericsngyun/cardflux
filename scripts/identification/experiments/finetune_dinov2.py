#!/usr/bin/env python3
"""
Fine-Tune DINOv2 for One Piece TCG Card Identification

This script fine-tunes the DINOv2 model specifically for One Piece TCG cards
to improve visual similarity scoring.

Expected Improvement: +15-25% accuracy
Training Time: 8-16 hours on GPU (10-20 epochs)
GPU Memory Required: ~8-12 GB

Strategy:
1. Contrastive learning: Same card = similar embeddings, different cards = different embeddings
2. Data augmentation: Rotation, brightness, crop to simulate real-world conditions
3. Metric learning: Optimize for card similarity rather than classification

Author: Senior Principal Engineer
Date: 2025-10-21
"""
import sys
import json
import time
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from PIL import Image
from torch.utils.data import Dataset, DataLoader
from transformers import AutoImageProcessor, AutoModel
from tqdm import tqdm
import numpy as np
import random
import cv2

# Set random seeds for reproducibility
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)


class CardDataset(Dataset):
    """
    Dataset for One Piece TCG cards with contrastive learning pairs.

    Each sample returns:
    - anchor: Original card image
    - positive: Augmented version of same card
    - negative: Different card image
    """

    def __init__(self, cards_jsonl_path: str, images_dir: str, processor, augment: bool = True):
        """Initialize dataset."""
        self.images_dir = Path(images_dir)
        self.processor = processor
        self.augment = augment

        # Load card metadata
        self.cards = []
        with open(cards_jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                card = json.loads(line)
                card_id = str(card['productId'])
                image_path = self.images_dir / f"{card_id}.jpg"

                if image_path.exists():
                    self.cards.append({
                        'card_id': card_id,
                        'image_path': str(image_path),
                        'name': card.get('name', 'Unknown')
                    })

        print(f"[DATASET] Loaded {len(self.cards)} cards with images")

    def __len__(self):
        return len(self.cards)

    def __getitem__(self, idx):
        """Get anchor, positive, negative triplet."""
        # Anchor: Original card
        anchor_card = self.cards[idx]
        anchor_image = self._load_image(anchor_card['image_path'])

        # Positive: Augmented version of same card
        positive_image = self._augment_image(anchor_image) if self.augment else anchor_image.copy()

        # Negative: Random different card
        negative_idx = random.randint(0, len(self.cards) - 1)
        while negative_idx == idx:
            negative_idx = random.randint(0, len(self.cards) - 1)

        negative_card = self.cards[negative_idx]
        negative_image = self._load_image(negative_card['image_path'])

        # Preprocess with DINOv2 processor
        anchor = self.processor(images=anchor_image, return_tensors="pt")['pixel_values'][0]
        positive = self.processor(images=positive_image, return_tensors="pt")['pixel_values'][0]
        negative = self.processor(images=negative_image, return_tensors="pt")['pixel_values'][0]

        return {
            'anchor': anchor,
            'positive': positive,
            'negative': negative,
            'card_id': anchor_card['card_id']
        }

    def _load_image(self, image_path: str) -> Image.Image:
        """Load and preprocess image (same as production)."""
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Apply production preprocessing (bilateral filter + contrast)
        filtered = cv2.bilateralFilter(img, d=5, sigmaColor=50, sigmaSpace=50)
        enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)

        return Image.fromarray(enhanced)

    def _augment_image(self, image: Image.Image) -> Image.Image:
        """Apply augmentations to simulate real-world conditions."""
        img_array = np.array(image)

        # Random rotation (-10 to +10 degrees)
        if random.random() > 0.5:
            angle = random.uniform(-10, 10)
            img_array = self._rotate(img_array, angle)

        # Random brightness adjustment (0.85 to 1.15)
        if random.random() > 0.5:
            brightness_factor = random.uniform(0.85, 1.15)
            img_array = np.clip(img_array * brightness_factor, 0, 255).astype(np.uint8)

        # Random crop and resize (90-100% of original)
        if random.random() > 0.5:
            crop_factor = random.uniform(0.90, 1.0)
            img_array = self._random_crop(img_array, crop_factor)

        # Random slight blur (simulate camera focus issues)
        if random.random() > 0.7:
            kernel_size = random.choice([3, 5])
            img_array = cv2.GaussianBlur(img_array, (kernel_size, kernel_size), 0)

        return Image.fromarray(img_array)

    def _rotate(self, img: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by angle degrees."""
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def _random_crop(self, img: np.ndarray, crop_factor: float) -> np.ndarray:
        """Random crop and resize back to original size."""
        h, w = img.shape[:2]
        new_h, new_w = int(h * crop_factor), int(w * crop_factor)

        top = random.randint(0, h - new_h)
        left = random.randint(0, w - new_w)

        cropped = img[top:top+new_h, left:left+new_w]
        resized = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        return resized


class TripletLoss(nn.Module):
    """
    Triplet loss for metric learning.

    Ensures anchor-positive distance < anchor-negative distance by margin.
    """

    def __init__(self, margin: float = 0.3):
        super().__init__()
        self.margin = margin

    def forward(self, anchor_emb, positive_emb, negative_emb):
        """Compute triplet loss."""
        # Cosine similarity (normalized dot product)
        anchor_norm = torch.nn.functional.normalize(anchor_emb, p=2, dim=1)
        positive_norm = torch.nn.functional.normalize(positive_emb, p=2, dim=1)
        negative_norm = torch.nn.functional.normalize(negative_emb, p=2, dim=1)

        # Distances (1 - cosine similarity)
        pos_dist = 1 - (anchor_norm * positive_norm).sum(dim=1)
        neg_dist = 1 - (anchor_norm * negative_norm).sum(dim=1)

        # Triplet loss: max(0, pos_dist - neg_dist + margin)
        loss = torch.clamp(pos_dist - neg_dist + self.margin, min=0.0)

        return loss.mean()


def train_epoch(model, dataloader, optimizer, criterion, device, epoch, total_epochs):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    num_batches = len(dataloader)

    progress_bar = tqdm(dataloader, desc=f"Epoch {epoch}/{total_epochs}")

    for batch_idx, batch in enumerate(progress_bar):
        # Move to device
        anchor = batch['anchor'].to(device)
        positive = batch['positive'].to(device)
        negative = batch['negative'].to(device)

        # Forward pass
        optimizer.zero_grad()

        anchor_emb = model(anchor).last_hidden_state[:, 0]  # CLS token
        positive_emb = model(positive).last_hidden_state[:, 0]
        negative_emb = model(negative).last_hidden_state[:, 0]

        # Compute loss
        loss = criterion(anchor_emb, positive_emb, negative_emb)

        # Backward pass
        loss.backward()
        optimizer.step()

        # Track metrics
        total_loss += loss.item()
        avg_loss = total_loss / (batch_idx + 1)

        progress_bar.set_postfix({'loss': f'{avg_loss:.4f}'})

    return total_loss / num_batches


def validate(model, dataloader, criterion, device):
    """Validate model."""
    model.eval()
    total_loss = 0
    num_batches = len(dataloader)

    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Validating"):
            anchor = batch['anchor'].to(device)
            positive = batch['positive'].to(device)
            negative = batch['negative'].to(device)

            anchor_emb = model(anchor).last_hidden_state[:, 0]
            positive_emb = model(positive).last_hidden_state[:, 0]
            negative_emb = model(negative).last_hidden_state[:, 0]

            loss = criterion(anchor_emb, positive_emb, negative_emb)
            total_loss += loss.item()

    return total_loss / num_batches


def main():
    """Fine-tune DINOv2 on One Piece TCG cards."""
    print("="*100)
    print("DINOV2 FINE-TUNING FOR ONE PIECE TCG")
    print("="*100)
    print()

    # Configuration
    CONFIG = {
        'model_name': 'facebook/dinov2-small',
        'batch_size': 16,  # Adjust based on GPU memory
        'num_epochs': 15,
        'learning_rate': 2e-5,
        'weight_decay': 0.01,
        'margin': 0.3,
        'warmup_epochs': 2,
        'save_every': 5,
        'cards_jsonl': 'data/curated/one-piece.jsonl',
        'images_dir': 'data/images/one-piece',
        'output_dir': 'artifacts/finetuned-models',
    }

    print("Configuration:")
    for key, value in CONFIG.items():
        print(f"  {key}: {value}")
    print()

    # Check GPU availability
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    if device.type == 'cpu':
        print("[WARNING] No GPU detected. Fine-tuning will be VERY slow on CPU.")
        print("[WARNING] Consider using Google Colab, AWS, or other GPU service.")
        response = input("Continue on CPU? (y/n): ")
        if response.lower() != 'y':
            return 1
    else:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU: {gpu_name}")
        print(f"GPU Memory: {gpu_memory:.1f} GB")

    print()

    # Load model and processor
    print("[INIT] Loading DINOv2 model...")
    processor = AutoImageProcessor.from_pretrained(CONFIG['model_name'])
    model = AutoModel.from_pretrained(CONFIG['model_name'])
    model = model.to(device)
    print(f"[OK] Model loaded: {CONFIG['model_name']}")
    print()

    # Create dataset
    print("[INIT] Creating dataset...")
    full_dataset = CardDataset(
        CONFIG['cards_jsonl'],
        CONFIG['images_dir'],
        processor,
        augment=True
    )

    # Split into train/val (90/10)
    train_size = int(0.9 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        full_dataset, [train_size, val_size]
    )

    print(f"[OK] Dataset split: {train_size} train, {val_size} val")
    print()

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=CONFIG['batch_size'],
        shuffle=True,
        num_workers=4,
        pin_memory=(device.type == 'cuda')
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=CONFIG['batch_size'],
        shuffle=False,
        num_workers=4,
        pin_memory=(device.type == 'cuda')
    )

    # Loss and optimizer
    criterion = TripletLoss(margin=CONFIG['margin'])
    optimizer = optim.AdamW(
        model.parameters(),
        lr=CONFIG['learning_rate'],
        weight_decay=CONFIG['weight_decay']
    )

    # Learning rate scheduler (warmup + cosine decay)
    total_steps = len(train_loader) * CONFIG['num_epochs']
    warmup_steps = len(train_loader) * CONFIG['warmup_epochs']

    def lr_lambda(current_step):
        if current_step < warmup_steps:
            return float(current_step) / float(max(1, warmup_steps))
        progress = float(current_step - warmup_steps) / float(max(1, total_steps - warmup_steps))
        return max(0.0, 0.5 * (1.0 + np.cos(np.pi * progress)))

    scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # Training loop
    print("="*100)
    print("TRAINING")
    print("="*100)
    print()

    best_val_loss = float('inf')
    output_dir = Path(CONFIG['output_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)

    training_history = {
        'train_loss': [],
        'val_loss': [],
        'learning_rate': []
    }

    for epoch in range(1, CONFIG['num_epochs'] + 1):
        print(f"\nEpoch {epoch}/{CONFIG['num_epochs']}")
        print("-" * 100)

        # Train
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device, epoch, CONFIG['num_epochs'])

        # Validate
        val_loss = validate(model, val_loader, criterion, device)

        # Learning rate step
        current_lr = optimizer.param_groups[0]['lr']
        scheduler.step()

        # Track metrics
        training_history['train_loss'].append(train_loss)
        training_history['val_loss'].append(val_loss)
        training_history['learning_rate'].append(current_lr)

        print(f"\nEpoch {epoch} Summary:")
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_loss:.4f}")
        print(f"  Learning Rate: {current_lr:.6f}")

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_path = output_dir / "dinov2-onepiece-best.pt"
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'config': CONFIG
            }, best_model_path)
            print(f"  [BEST] Model saved: {best_model_path}")

        # Save checkpoint every N epochs
        if epoch % CONFIG['save_every'] == 0:
            checkpoint_path = output_dir / f"dinov2-onepiece-epoch{epoch}.pt"
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'config': CONFIG
            }, checkpoint_path)
            print(f"  [CHECKPOINT] Saved: {checkpoint_path}")

    # Save final model
    final_model_path = output_dir / "dinov2-onepiece-final.pt"
    torch.save({
        'epoch': CONFIG['num_epochs'],
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'val_loss': val_loss,
        'config': CONFIG
    }, final_model_path)
    print(f"\n[FINAL] Model saved: {final_model_path}")

    # Save training history
    history_path = output_dir / "training_history.json"
    with open(history_path, 'w') as f:
        json.dump(training_history, f, indent=2)
    print(f"[OK] Training history saved: {history_path}")

    print()
    print("="*100)
    print("TRAINING COMPLETE")
    print("="*100)
    print(f"Best Validation Loss: {best_val_loss:.4f}")
    print(f"Best Model: {output_dir / 'dinov2-onepiece-best.pt'}")
    print()
    print("Next Steps:")
    print("1. Test the fine-tuned model with: python test_finetuned_model.py")
    print("2. Compare accuracy vs V1 baseline")
    print("3. If improved, integrate into production_card_identifier.py")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
