#!/usr/bin/env python3
"""Test Fast Identifier v2 on all One Piece test images"""

import os
import json
import subprocess
import time
from pathlib import Path

TEST_DIR = Path("test-images/one-piece")
IDENTIFIER = "scripts/identification/core/fast_card_identifier.py"

def main():
    results = []

    # Find all test images
    images = sorted(TEST_DIR.glob("*.png")) + sorted(TEST_DIR.glob("*.jpg"))
    images = [img for img in images if not img.stem.startswith('ground_truth')]

    print(f"Testing {len(images)} images with Fast Identifier v2...\n")
    print("="*80)

    for img_path in images:
        print(f"\nTesting: {img_path.name}")
        print("-" * 80)

        try:
            result = subprocess.run(
                ["python", IDENTIFIER, str(img_path), "--quiet"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                match = data['best_match']

                results.append({
                    'image': img_path.name,
                    'matched_card': match['name'],
                    'card_number': match['number'],
                    'confidence': data['confidence'],
                    'final_score': data['scores']['final'],
                    'visual_score': data['scores']['visual'],
                    'geometric_score': data['scores']['geometric'],
                    'time_ms': data['timing']['total_ms'],
                    'success': True
                })

                print(f"[OK] MATCH: {match['name']} ({match['number']})")
                print(f"   Confidence: {data['confidence']}")
                print(f"   Score: {data['scores']['final']:.4f} (visual: {data['scores']['visual']:.4f}, geometric: {data['scores']['geometric']:.4f})")
                print(f"   Time: {data['timing']['total_ms']:.0f}ms")

            else:
                print(f"[FAIL] ERROR: {result.stderr}")
                results.append({
                    'image': img_path.name,
                    'success': False,
                    'error': result.stderr
                })

        except Exception as e:
            print(f"[FAIL] EXCEPTION: {e}")
            results.append({
                'image': img_path.name,
                'success': False,
                'error': str(e)
            })

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]

    print(f"\nTotal Images: {len(results)}")
    print(f"[OK] Successful: {len(successful)}")
    print(f"[FAIL] Failed: {len(failed)}")

    if successful:
        avg_time = sum(r['time_ms'] for r in successful) / len(successful)
        high_conf = len([r for r in successful if r['confidence'] == 'HIGH'])
        mod_conf = len([r for r in successful if r['confidence'] == 'MODERATE'])
        low_conf = len([r for r in successful if r['confidence'] == 'LOW'])

        print(f"\nAverage Time: {avg_time:.0f}ms")
        print(f"Confidence Distribution:")
        print(f"  HIGH: {high_conf}/{len(successful)} ({100*high_conf/len(successful):.0f}%)")
        print(f"  MODERATE: {mod_conf}/{len(successful)} ({100*mod_conf/len(successful) if successful else 0:.0f}%)")
        print(f"  LOW: {low_conf}/{len(successful)} ({100*low_conf/len(successful) if successful else 0:.0f}%)")

    if failed:
        print(f"\n[FAIL] Failed Tests:")
        for r in failed:
            print(f"  - {r['image']}: {r.get('error', 'Unknown error')}")

    # Save detailed results
    output_file = "test-results/fast_identifier_v2_test_results.json"
    os.makedirs("test-results", exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'results': results
        }, f, indent=2)

    print(f"\n[INFO] Detailed results saved to: {output_file}")
    print("="*80)

if __name__ == "__main__":
    main()
