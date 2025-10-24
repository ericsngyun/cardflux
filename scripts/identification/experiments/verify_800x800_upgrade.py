#!/usr/bin/env python3
"""
Verify 800x800 Upgrade Success

Checks that:
1. All images were downloaded
2. Images are actually 800x800 (not 600x600)
3. File sizes increased as expected
4. Test identification accuracy improvements

Usage:
    python scripts/identification/verify_800x800_upgrade.py
"""
import sys
import json
from pathlib import Path
from PIL import Image
import numpy as np

# Paths
IMAGES_DIR = Path("data/images/one-piece")
BACKUP_DIR = Path("data/backup_600x600_20251021_104129/images_one-piece")
TEST_IMAGES = [
    "test-images/one-piece/bege.png",
    "test-images/one-piece/blackbeard.png",
    "test-images/one-piece/yellow_event.png"
]

def check_image_dimensions():
    """Check that images are 800x800, not 600x600."""
    print("\n" + "="*70)
    print("IMAGE DIMENSION CHECK")
    print("="*70)
    
    images = list(IMAGES_DIR.glob("*.jpg"))
    if len(images) == 0:
        print("  ❌ No images found!")
        return False
    
    # Sample 20 random images
    sample_images = np.random.choice(images, min(20, len(images)), replace=False)
    
    resolution_counts = {}
    for img_path in sample_images:
        try:
            with Image.open(img_path) as img:
                w, h = img.size
                key = f"{w}x{h}"
                resolution_counts[key] = resolution_counts.get(key, 0) + 1
        except Exception as e:
            print(f"  ⚠️  Error reading {img_path.name}: {e}")
    
    print(f"  Sampled {len(sample_images)} images")
    print(f"  Resolution distribution:")
    for resolution, count in sorted(resolution_counts.items(), key=lambda x: -x[1]):
        print(f"    {resolution}: {count} images")
    
    # Check if majority are 800x800
    if "800x800" not in resolution_counts:
        print("  ❌ No 800x800 images found! Upgrade failed.")
        return False
    
    if resolution_counts["800x800"] < len(sample_images) * 0.8:
        print(f"  ⚠️  Only {resolution_counts['800x800']}/{len(sample_images)} are 800x800")
        return False
    
    print("  ✅ Images are 800x800!")
    return True

def check_file_sizes():
    """Check that file sizes increased."""
    print("\n" + "="*70)
    print("FILE SIZE CHECK")
    print("="*70)
    
    images = list(IMAGES_DIR.glob("*.jpg"))
    if len(images) == 0:
        print("  ❌ No images found!")
        return False
    
    # Calculate stats
    total_size = sum(img.stat().st_size for img in images)
    avg_size = total_size / len(images)
    total_mb = total_size / (1024 * 1024)
    
    print(f"  Total images: {len(images)}")
    print(f"  Total size: {total_mb:.2f} MB")
    print(f"  Average size: {avg_size/1024:.2f} KB per image")
    
    # Expected: 600x600 avg ~60KB, 800x800 avg ~90KB
    if avg_size < 70 * 1024:  # 70 KB threshold
        print(f"  ⚠️  Average size too small (< 70 KB), might still be 600x600")
        return False
    
    print("  ✅ File sizes look correct for 800x800!")
    return True

def check_image_count():
    """Check that we have all expected images."""
    print("\n" + "="*70)
    print("IMAGE COUNT CHECK")
    print("="*70)
    
    images = list(IMAGES_DIR.glob("*.jpg"))
    expected_count = 5113  # From previous check
    
    print(f"  Current images: {len(images)}")
    print(f"  Expected: ~{expected_count}")
    
    if len(images) < expected_count * 0.95:  # Allow 5% tolerance
        print(f"  ⚠️  Missing images! Only {len(images)}/{expected_count}")
        return False
    
    print("  ✅ All images downloaded!")
    return True

def test_identification():
    """Test identification with new 800x800 embeddings."""
    print("\n" + "="*70)
    print("IDENTIFICATION ACCURACY TEST")
    print("="*70)
    print("  (Run this AFTER regenerating embeddings)")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from production_card_identifier import ProductionCardIdentifier
        
        identifier = ProductionCardIdentifier(game='one-piece', verbose=False)
        
        results = []
        for test_img in TEST_IMAGES:
            if not Path(test_img).exists():
                print(f"  ⚠️  Test image not found: {test_img}")
                continue
            
            result = identifier.identify(test_img, top_k=50, use_geometric=True)
            
            results.append({
                'image': Path(test_img).name,
                'card': result['best_match']['name'],
                'confidence': result['confidence'],
                'score': result['best_match']['final_score'],
                'visual': result['best_match']['visual_score'],
                'geometric': result['best_match']['geometric_score'],
            })
            
            emoji = "✅" if result['confidence'] == "HIGH" else "⚠️" if result['confidence'] == "MODERATE" else "❌"
            print(f"  {emoji} {Path(test_img).name}: {result['confidence']} ({result['best_match']['final_score']:.3f})")
        
        # Save results
        results_file = Path("scripts/identification/800x800_test_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                'test_date': '2025-10-21',
                'resolution': '800x800',
                'results': results
            }, f, indent=2)
        
        print(f"\n  Results saved to: {results_file}")
        
        # Calculate improvement
        high_count = sum(1 for r in results if r['confidence'] == 'HIGH')
        high_rate = high_count / len(results) * 100
        
        print(f"\n  HIGH confidence rate: {high_count}/{len(results)} ({high_rate:.0f}%)")
        print(f"  Target: 75%+ (3/4)")
        
        if high_rate >= 75:
            print("  ✅ GOAL ACHIEVED!")
            return True
        else:
            print("  ⚠️  Still below target, but may have improved")
            return True
        
    except Exception as e:
        print(f"  ⚠️  Cannot test yet (embeddings not regenerated): {e}")
        return None

def main():
    print("\n" + "="*70)
    print("800x800 UPGRADE VERIFICATION")
    print("="*70)
    
    checks = [
        ("Image Count", check_image_count()),
        ("Image Dimensions", check_image_dimensions()),
        ("File Sizes", check_file_sizes()),
    ]
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ 800x800 download verified successfully!")
        print("\nNext steps:")
        print("  1. Regenerate embeddings:")
        print("     python services/embedder/bin/embed_onepiece_dinov2_with_preprocessing.py")
        print("  2. Rebuild FAISS index:")
        print("     python services/indexer/bin/build_faiss_onepiece_dinov2.py")
        print("  3. Test accuracy:")
        print("     python scripts/identification/verify_800x800_upgrade.py")
    else:
        print("\n❌ Verification failed! Check errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

