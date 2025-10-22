#!/usr/bin/env python3
"""
Test card detection on all test images
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from polished_card_detector import PolishedCardDetector
import cv2

def test_all_images():
    """Test card detection on all test images."""

    test_dir = Path("test-images/one-piece")
    detector = PolishedCardDetector()

    # Find all images
    image_files = list(test_dir.glob("*.png")) + list(test_dir.glob("*.jpg"))
    image_files = sorted([f for f in image_files if not f.name.startswith(('cropped_', 'detected_'))])

    print("="*80)
    print("CARD DETECTION TEST SUITE")
    print("="*80)
    print(f"Testing {len(image_files)} images\n")

    results = []

    for img_path in image_files:
        result = detector.detect_and_crop(str(img_path))

        status_symbol = {
            'perfect': '[OK]',
            'good': '[OK]',
            'poor_quality': '[!!]',
            'no_card': '[XX]',
            'multiple_cards': '[!!]',
            'partial_card': '[!!]'
        }.get(result['status'].value, '[??]')

        print(f"{status_symbol} {img_path.name:50s} | {result['status'].value:15s} | "
              f"Conf: {result['confidence']:.2f} | Quality: {result['quality_score']:.2f}")

        results.append({
            'file': img_path.name,
            'status': result['status'].value,
            'confidence': result['confidence'],
            'quality': result['quality_score'],
            'acceptable': result['is_acceptable']
        })

        # Save cropped version
        if result['cropped_image'] is not None:
            cropped_path = test_dir / f"cropped_{img_path.name}"
            cv2.imwrite(str(cropped_path), result['cropped_image'])

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    perfect = sum(1 for r in results if r['status'] == 'perfect')
    good = sum(1 for r in results if r['status'] == 'good')
    acceptable = sum(1 for r in results if r['acceptable'])

    print(f"Perfect: {perfect}/{len(results)}")
    print(f"Good: {good}/{len(results)}")
    print(f"Acceptable: {acceptable}/{len(results)} ({acceptable/len(results)*100:.1f}%)")

    if acceptable < len(results):
        print(f"\n[WARNING] {len(results) - acceptable} images not acceptable:")
        for r in results:
            if not r['acceptable']:
                print(f"  - {r['file']}: {r['status']}")

if __name__ == "__main__":
    test_all_images()
