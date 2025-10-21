"""
Google Colab Fine-Tuning Notebook for One Piece TCG DINOv2

INSTRUCTIONS:
1. Go to https://colab.research.google.com
2. Create new notebook
3. Enable GPU: Runtime -> Change runtime type -> Hardware accelerator -> GPU (T4)
4. Copy-paste the cells below into separate code cells
5. Run each cell in order
6. Wait ~3-4 hours for training
7. Download the trained model file

Author: Senior Principal Engineer
Date: 2025-10-21
"""

# ============================================================================
# CELL 1: Setup and Install Dependencies
# ============================================================================

# Check GPU availability
import torch
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"GPU Name: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print("\n✅ GPU detected! Ready for training.")
else:
    print("\n⚠️  WARNING: No GPU detected!")
    print("Go to Runtime -> Change runtime type -> Hardware accelerator -> GPU")
    raise RuntimeError("GPU required for training")

# Install dependencies
print("\nInstalling dependencies...")
!pip install -q transformers pillow opencv-python tqdm tabulate

print("✅ Dependencies installed!")


# ============================================================================
# CELL 2: Upload Your Dataset
# ============================================================================

print("="*80)
print("DATASET UPLOAD")
print("="*80)
print("\nYou need to upload 3 things:")
print("1. one-piece.jsonl (card metadata)")
print("2. images folder (5,113 card images)")
print("3. Test images (optional, for validation)")
print()
print("Options:")
print("A) Upload files directly (click folder icon on left, upload)")
print("B) Mount Google Drive (if you already uploaded there)")
print()

# Option B: Mount Google Drive (recommended if files are large)
from google.colab import drive
drive.mount('/content/drive')

print("\n✅ Google Drive mounted!")
print("\nIf you uploaded files to Drive, update these paths:")
print("  JSONL: /content/drive/MyDrive/cardflux/data/curated/one-piece.jsonl")
print("  Images: /content/drive/MyDrive/cardflux/data/images/one-piece/")


# ============================================================================
# CELL 2.5: Unzip Images (Run this if images are in a zip file)
# ============================================================================

import zipfile
import shutil

# ⚠️  EDIT THIS: Path to your images zip file in Google Drive
IMAGES_ZIP_PATH = "/content/drive/MyDrive/cardflux/data/one-piece-images.zip"  # ← Update this!

# Where to extract (local Colab storage, much faster than Drive)
EXTRACT_TO = "/content/images"

print("="*80)
print("UNZIPPING IMAGES")
print("="*80)
print()

if os.path.exists(IMAGES_ZIP_PATH):
    print(f"✅ Found zip file: {IMAGES_ZIP_PATH}")
    
    # Check if already extracted
    if os.path.exists(EXTRACT_TO) and len(os.listdir(EXTRACT_TO)) > 1000:
        print(f"⚠️  Images already extracted to {EXTRACT_TO}")
        print(f"   ({len(os.listdir(EXTRACT_TO))} files found)")
        print()
        
        user_input = input("Re-extract? (y/N): ")
        if user_input.lower() != 'y':
            print("✅ Using existing images")
        else:
            print("Removing old files...")
            shutil.rmtree(EXTRACT_TO)
            os.makedirs(EXTRACT_TO)
    else:
        os.makedirs(EXTRACT_TO, exist_ok=True)
    
    if not os.path.exists(EXTRACT_TO) or len(os.listdir(EXTRACT_TO)) < 1000:
        print(f"Extracting to {EXTRACT_TO}...")
        print("⏱️  This will take 2-3 minutes for ~5,000 images")
        print()
        
        with zipfile.ZipFile(IMAGES_ZIP_PATH, 'r') as zip_ref:
            # Show progress
            total_files = len(zip_ref.namelist())
            print(f"Total files in zip: {total_files}")
            
            for i, file in enumerate(zip_ref.namelist(), 1):
                zip_ref.extract(file, EXTRACT_TO)
                if i % 500 == 0:
                    print(f"  Extracted {i}/{total_files} files...")
        
        # Check what was extracted
        extracted_files = []
        for root, dirs, files in os.walk(EXTRACT_TO):
            extracted_files.extend([os.path.join(root, f) for f in files if f.endswith(('.jpg', '.jpeg', '.png'))])
        
        print()
        print(f"✅ Extraction complete!")
        print(f"   Total images: {len(extracted_files)}")
        
        # If images are in a subdirectory (e.g., one-piece/), move them up
        if len(os.listdir(EXTRACT_TO)) == 1 and os.path.isdir(os.path.join(EXTRACT_TO, os.listdir(EXTRACT_TO)[0])):
            subdir = os.path.join(EXTRACT_TO, os.listdir(EXTRACT_TO)[0])
            print(f"   Moving images from subdirectory: {subdir}")
            
            for file in os.listdir(subdir):
                shutil.move(os.path.join(subdir, file), EXTRACT_TO)
            
            os.rmdir(subdir)
            print("   ✅ Images moved to root of extract directory")
        
        print()
        print(f"📁 Images location: {EXTRACT_TO}")
else:
    print(f"❌ Zip file not found: {IMAGES_ZIP_PATH}")
    print()
    print("Options:")
    print("1. Update IMAGES_ZIP_PATH above to point to your zip file")
    print("2. OR skip this cell if images are already unzipped in Drive")
    print("3. OR upload zip file to: /content/drive/MyDrive/cardflux/data/")
    print()

print("="*80)


# ============================================================================
# CELL 3: Configure Paths (EDIT THIS)
# ============================================================================

# ⚠️  EDIT THESE PATHS to match your setup

# Option A: Images are in Google Drive (unzipped)
# CARDS_JSONL = "/content/drive/MyDrive/cardflux/data/curated/one-piece.jsonl"
# IMAGES_DIR = "/content/drive/MyDrive/cardflux/data/images/one-piece"

# Option B: Images were unzipped to local Colab storage (FASTER - recommended!)
CARDS_JSONL = "/content/drive/MyDrive/cardflux/data/curated/one-piece.jsonl"
IMAGES_DIR = "/content/images"  # ← Use this if you ran CELL 2.5

OUTPUT_DIR = "/content/finetuned-models"

# Verify paths exist
import os
from pathlib import Path

if not os.path.exists(CARDS_JSONL):
    print(f"❌ ERROR: JSONL not found at {CARDS_JSONL}")
    print("Update CARDS_JSONL path above")
else:
    print(f"✅ Found JSONL: {CARDS_JSONL}")

if not os.path.exists(IMAGES_DIR):
    print(f"❌ ERROR: Images directory not found at {IMAGES_DIR}")
    print("Update IMAGES_DIR path above")
else:
    num_images = len(list(Path(IMAGES_DIR).glob("*.jpg")))
    print(f"✅ Found {num_images} images in {IMAGES_DIR}")

# Create output directory
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
print(f"✅ Output directory: {OUTPUT_DIR}")


# ============================================================================
# CELL 3.5: Verify Setup (Run this to check paths before training)
# ============================================================================

print("="*80)
print("VERIFYING SETUP")
print("="*80)
print()

# Check JSONL
if os.path.exists(CARDS_JSONL):
    with open(CARDS_JSONL, 'r') as f:
        sample_line = f.readline()
        sample_card = json.loads(sample_line)
    
    print("✅ JSONL file found")
    print(f"   Path: {CARDS_JSONL}")
    print(f"   Sample card: {sample_card.get('name', 'Unknown')}")
    print(f"   Product ID: {sample_card.get('productId', 'N/A')}")
else:
    print(f"❌ JSONL file NOT found: {CARDS_JSONL}")
    print("   Update CARDS_JSONL path in CELL 3")

print()

# Check images directory
if os.path.exists(IMAGES_DIR):
    image_files = [f for f in os.listdir(IMAGES_DIR) if f.endswith(('.jpg', '.jpeg', '.png'))]
    
    print("✅ Images directory found")
    print(f"   Path: {IMAGES_DIR}")
    print(f"   Total images: {len(image_files)}")
    
    if len(image_files) > 0:
        print(f"   Sample files: {image_files[:5]}")
        
        # Check if sample card's image exists
        sample_id = str(sample_card.get('productId', ''))
        found = False
        for ext in ['.jpg', '.jpeg', '.png']:
            if f"{sample_id}{ext}" in image_files:
                print(f"   ✅ Sample card image found: {sample_id}{ext}")
                found = True
                break
        
        if not found:
            print(f"   ⚠️  Sample card image NOT found: {sample_id}.jpg")
            print(f"   Check if card IDs match filenames")
    else:
        print("   ❌ No image files found in directory!")
        print("   Did you run CELL 2.5 to unzip images?")
else:
    print(f"❌ Images directory NOT found: {IMAGES_DIR}")
    print("   Options:")
    print("   1. Run CELL 2.5 to unzip images")
    print("   2. Update IMAGES_DIR path in CELL 3")

print()
print("="*80)

# Stop here if any issues
if not os.path.exists(CARDS_JSONL) or not os.path.exists(IMAGES_DIR):
    print("\n❌ Setup incomplete! Fix paths above before continuing.")
elif len(image_files) == 0:
    print("\n❌ No images found! Run CELL 2.5 to extract images.")
else:
    print("\n✅ Setup looks good! Continue to CELL 4.")


# ============================================================================
# CELL 4: Define Dataset Class
# ============================================================================

import json
import random
import numpy as np
import cv2
from PIL import Image
from torch.utils.data import Dataset

class CardDataset(Dataset):
    """Dataset for One Piece TCG cards with contrastive learning pairs."""

    def __init__(self, cards_jsonl_path, images_dir, processor, augment=True):
        self.images_dir = Path(images_dir)
        self.processor = processor
        self.augment = augment

        # Debug: Check if paths exist
        print(f"[DEBUG] JSONL path: {cards_jsonl_path}")
        print(f"[DEBUG] JSONL exists: {Path(cards_jsonl_path).exists()}")
        print(f"[DEBUG] Images dir: {images_dir}")
        print(f"[DEBUG] Images dir exists: {Path(images_dir).exists()}")
        
        if Path(images_dir).exists():
            # Check what files are in the directory
            image_files = list(Path(images_dir).glob("*"))
            print(f"[DEBUG] Files in images dir: {len(image_files)}")
            if len(image_files) > 0:
                print(f"[DEBUG] Sample files: {[f.name for f in image_files[:5]]}")
        
        # Load card metadata
        self.cards = []
        skipped = 0
        
        with open(cards_jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                    
                try:
                    card = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[WARN] Line {line_num}: Invalid JSON - {e}")
                    continue
                
                card_id = str(card.get('productId', ''))
                if not card_id:
                    skipped += 1
                    continue
                
                # Try multiple extensions
                image_path = None
                for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                    candidate = self.images_dir / f"{card_id}{ext}"
                    if candidate.exists():
                        image_path = candidate
                        break
                
                if image_path:
                    self.cards.append({
                        'card_id': card_id,
                        'image_path': str(image_path),
                        'name': card.get('name', 'Unknown')
                    })
                else:
                    skipped += 1

        print(f"✅ Loaded {len(self.cards)} cards with images")
        print(f"⚠️  Skipped {skipped} cards (no image found)")
        
        if len(self.cards) == 0:
            print("\n❌ ERROR: No cards loaded!")
            print("\nTroubleshooting:")
            print("1. Check CARDS_JSONL path is correct")
            print("2. Check IMAGES_DIR path is correct") 
            print("3. Make sure you ran CELL 2.5 to unzip images")
            print("4. Verify card IDs match image filenames")
            print(f"\nExpected format: {images_dir}/{{productId}}.jpg")
            raise ValueError("No cards loaded! Check paths above.")

    def __len__(self):
        return len(self.cards)

    def __getitem__(self, idx):
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

        # Preprocess
        anchor = self.processor(images=anchor_image, return_tensors="pt")['pixel_values'][0]
        positive = self.processor(images=positive_image, return_tensors="pt")['pixel_values'][0]
        negative = self.processor(images=negative_image, return_tensors="pt")['pixel_values'][0]

        return {
            'anchor': anchor,
            'positive': positive,
            'negative': negative,
            'card_id': anchor_card['card_id']
        }

    def _load_image(self, image_path):
        """Load and preprocess image (same as production)."""
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Apply production preprocessing
        filtered = cv2.bilateralFilter(img, d=5, sigmaColor=50, sigmaSpace=50)
        enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)

        return Image.fromarray(enhanced)

    def _augment_image(self, image):
        """Apply augmentations."""
        img_array = np.array(image)

        # Random rotation (-10 to +10 degrees)
        if random.random() > 0.5:
            angle = random.uniform(-10, 10)
            img_array = self._rotate(img_array, angle)

        # Random brightness (0.85 to 1.15)
        if random.random() > 0.5:
            brightness = random.uniform(0.85, 1.15)
            img_array = np.clip(img_array * brightness, 0, 255).astype(np.uint8)

        # Random crop (90-100%)
        if random.random() > 0.5:
            crop_factor = random.uniform(0.90, 1.0)
            img_array = self._random_crop(img_array, crop_factor)

        # Random blur
        if random.random() > 0.7:
            kernel_size = random.choice([3, 5])
            img_array = cv2.GaussianBlur(img_array, (kernel_size, kernel_size), 0)

        return Image.fromarray(img_array)

    def _rotate(self, img, angle):
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
        return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

    def _random_crop(self, img, crop_factor):
        h, w = img.shape[:2]
        new_h, new_w = int(h * crop_factor), int(w * crop_factor)
        top = random.randint(0, h - new_h)
        left = random.randint(0, w - new_w)
        cropped = img[top:top+new_h, left:left+new_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

print("✅ Dataset class defined")


# ============================================================================
# CELL 5: Define Triplet Loss
# ============================================================================

import torch.nn as nn

class TripletLoss(nn.Module):
    """Triplet loss for metric learning."""

    def __init__(self, margin=0.3):
        super().__init__()
        self.margin = margin

    def forward(self, anchor_emb, positive_emb, negative_emb):
        # Normalize embeddings
        anchor_norm = torch.nn.functional.normalize(anchor_emb, p=2, dim=1)
        positive_norm = torch.nn.functional.normalize(positive_emb, p=2, dim=1)
        negative_norm = torch.nn.functional.normalize(negative_emb, p=2, dim=1)

        # Compute distances (1 - cosine similarity)
        pos_dist = 1 - (anchor_norm * positive_norm).sum(dim=1)
        neg_dist = 1 - (anchor_norm * negative_norm).sum(dim=1)

        # Triplet loss
        loss = torch.clamp(pos_dist - neg_dist + self.margin, min=0.0)
        return loss.mean()

print("✅ Triplet loss defined")


# ============================================================================
# CELL 6: Training Configuration
# ============================================================================

# Training hyperparameters
CONFIG = {
    'model_name': 'facebook/dinov2-small',
    'batch_size': 16,          # Reduce to 8 if OOM
    'num_epochs': 15,          # ~3-4 hours on T4 GPU
    'learning_rate': 2e-5,
    'weight_decay': 0.01,
    'margin': 0.3,
    'warmup_epochs': 2,
    'save_every': 5,
}

print("="*80)
print("TRAINING CONFIGURATION")
print("="*80)
for key, value in CONFIG.items():
    print(f"  {key}: {value}")
print()

# Set random seeds
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)

print("✅ Configuration set")


# ============================================================================
# CELL 7: Load Model and Create Datasets
# ============================================================================

from transformers import AutoImageProcessor, AutoModel
from torch.utils.data import DataLoader, random_split
import torch.optim as optim

device = torch.device('cuda')
print(f"Device: {device}")
print()

# Load model
print("Loading DINOv2 model...")
processor = AutoImageProcessor.from_pretrained(CONFIG['model_name'])
model = AutoModel.from_pretrained(CONFIG['model_name'])
model = model.to(device)
print(f"✅ Model loaded: {CONFIG['model_name']}")
print()

# Create dataset
print("Creating dataset...")
full_dataset = CardDataset(CARDS_JSONL, IMAGES_DIR, processor, augment=True)

# Split train/val (90/10)
train_size = int(0.9 * len(full_dataset))
val_size = len(full_dataset) - train_size
train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])
print(f"✅ Dataset split: {train_size} train, {val_size} val")
print()

# Create dataloaders
train_loader = DataLoader(
    train_dataset,
    batch_size=CONFIG['batch_size'],
    shuffle=True,
    num_workers=2,
    pin_memory=True
)

val_loader = DataLoader(
    val_dataset,
    batch_size=CONFIG['batch_size'],
    shuffle=False,
    num_workers=2,
    pin_memory=True
)

print(f"✅ DataLoaders created")
print(f"   Train batches: {len(train_loader)}")
print(f"   Val batches: {len(val_loader)}")


# ============================================================================
# CELL 8: Setup Optimizer and Scheduler
# ============================================================================

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

print("✅ Optimizer and scheduler ready")


# ============================================================================
# CELL 9: Define Training Functions
# ============================================================================

from tqdm import tqdm

def train_epoch(model, dataloader, optimizer, criterion, device, epoch, total_epochs):
    """Train for one epoch."""
    model.train()
    total_loss = 0

    progress_bar = tqdm(dataloader, desc=f"Epoch {epoch}/{total_epochs}")

    for batch_idx, batch in enumerate(progress_bar):
        anchor = batch['anchor'].to(device)
        positive = batch['positive'].to(device)
        negative = batch['negative'].to(device)

        optimizer.zero_grad()

        anchor_emb = model(anchor).last_hidden_state[:, 0]
        positive_emb = model(positive).last_hidden_state[:, 0]
        negative_emb = model(negative).last_hidden_state[:, 0]

        loss = criterion(anchor_emb, positive_emb, negative_emb)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        avg_loss = total_loss / (batch_idx + 1)
        progress_bar.set_postfix({'loss': f'{avg_loss:.4f}'})

    return total_loss / len(dataloader)


def validate(model, dataloader, criterion, device):
    """Validate model."""
    model.eval()
    total_loss = 0

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

    return total_loss / len(dataloader)

print("✅ Training functions defined")


# ============================================================================
# CELL 10: START TRAINING (This will take 3-4 hours)
# ============================================================================

print("="*80)
print("STARTING TRAINING")
print("="*80)
print()
print("⏱️  Estimated time: 3-4 hours on T4 GPU")
print("☕ Grab a coffee, this will take a while...")
print()

best_val_loss = float('inf')
training_history = {
    'train_loss': [],
    'val_loss': [],
    'learning_rate': []
}

for epoch in range(1, CONFIG['num_epochs'] + 1):
    print(f"\nEpoch {epoch}/{CONFIG['num_epochs']}")
    print("-" * 80)

    # Train
    train_loss = train_epoch(
        model, train_loader, optimizer, criterion,
        device, epoch, CONFIG['num_epochs']
    )

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
        best_model_path = Path(OUTPUT_DIR) / "dinov2-onepiece-best.pt"
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'val_loss': val_loss,
            'config': CONFIG
        }, best_model_path)
        print(f"  ✅ [BEST] Model saved: {best_model_path}")

    # Save checkpoint
    if epoch % CONFIG['save_every'] == 0:
        checkpoint_path = Path(OUTPUT_DIR) / f"dinov2-onepiece-epoch{epoch}.pt"
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'val_loss': val_loss,
            'config': CONFIG
        }, checkpoint_path)
        print(f"  ✅ [CHECKPOINT] Saved: {checkpoint_path}")

# Save final model
final_model_path = Path(OUTPUT_DIR) / "dinov2-onepiece-final.pt"
torch.save({
    'epoch': CONFIG['num_epochs'],
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'val_loss': val_loss,
    'config': CONFIG
}, final_model_path)

print()
print("="*80)
print("TRAINING COMPLETE! 🎉")
print("="*80)
print(f"Best Validation Loss: {best_val_loss:.4f}")
print(f"Best Model: {OUTPUT_DIR}/dinov2-onepiece-best.pt")
print()


# ============================================================================
# CELL 11: Save Training History and Visualize
# ============================================================================

# Save training history
history_path = Path(OUTPUT_DIR) / "training_history.json"
with open(history_path, 'w') as f:
    json.dump(training_history, f, indent=2)
print(f"✅ Training history saved: {history_path}")

# Plot training curves
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

# Loss curves
epochs = range(1, len(training_history['train_loss']) + 1)
ax1.plot(epochs, training_history['train_loss'], 'b-', label='Train Loss')
ax1.plot(epochs, training_history['val_loss'], 'r-', label='Val Loss')
ax1.set_xlabel('Epoch')
ax1.set_ylabel('Loss')
ax1.set_title('Training and Validation Loss')
ax1.legend()
ax1.grid(True)

# Learning rate
ax2.plot(epochs, training_history['learning_rate'], 'g-')
ax2.set_xlabel('Epoch')
ax2.set_ylabel('Learning Rate')
ax2.set_title('Learning Rate Schedule')
ax2.grid(True)

plt.tight_layout()
plt.savefig(Path(OUTPUT_DIR) / 'training_curves.png', dpi=150)
plt.show()

print("✅ Training curves saved")


# ============================================================================
# CELL 12: Download Trained Model
# ============================================================================

from google.colab import files

print("="*80)
print("DOWNLOAD TRAINED MODEL")
print("="*80)
print()

best_model_path = Path(OUTPUT_DIR) / "dinov2-onepiece-best.pt"
model_size_mb = best_model_path.stat().st_size / 1024 / 1024

print(f"Model: {best_model_path}")
print(f"Size: {model_size_mb:.1f} MB")
print()
print("Downloading...")

files.download(str(best_model_path))

print()
print("✅ Download complete!")
print()
print("Next steps:")
print("1. Place downloaded file in: artifacts/finetuned-models/dinov2-onepiece-best.pt")
print("2. Run: python scripts/identification/test_finetuned_model.py")
print("3. If improved, integrate into production!")


# ============================================================================
# CELL 13: (Optional) Copy to Google Drive
# ============================================================================

# Alternatively, copy to Google Drive instead of downloading
import shutil

drive_output = "/content/drive/MyDrive/cardflux-finetuned"
Path(drive_output).mkdir(parents=True, exist_ok=True)

shutil.copy(
    str(Path(OUTPUT_DIR) / "dinov2-onepiece-best.pt"),
    f"{drive_output}/dinov2-onepiece-best.pt"
)

shutil.copy(
    str(Path(OUTPUT_DIR) / "training_history.json"),
    f"{drive_output}/training_history.json"
)

shutil.copy(
    str(Path(OUTPUT_DIR) / "training_curves.png"),
    f"{drive_output}/training_curves.png"
)

print(f"✅ Files copied to Google Drive: {drive_output}")
print("You can access them from your Drive anytime!")
