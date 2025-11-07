#!/usr/bin/env python3
"""
Camera Performance Diagnostic Tool

Diagnoses why camera captures identify slower than test images.
Compares image properties, file sizes, preprocessing, and timing.

Usage:
    python diagnose_camera_performance.py <camera_capture.jpg> <test_image.jpg>

Author: Senior Principal Engineer
Date: 2025-11-07
"""
import sys
import cv2
import numpy as np
from pathlib import Path
import time
import json
from typing import Dict, Tuple

def analyze_image(image_path: str) -> Dict:
    """Analyze image properties and preprocessing characteristics."""
    img = cv2.imread(image_path)
    if img is None:
        return {"error": f"Could not read image: {image_path}"}

    path_obj = Path(image_path)
    file_size_kb = path_obj.stat().st_size / 1024

    # Basic properties
    height, width = img.shape[:2]
    channels = img.shape[2] if len(img.shape) > 2 else 1

    # Color space analysis
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if channels == 3 else img

    # Blur detection (Laplacian variance)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = laplacian.var()

    # Brightness
    mean_brightness = np.mean(gray)

    # Contrast
    contrast = np.std(gray)

    # Compression artifacts (JPEG quality estimation via high-frequency content)
    dct = cv2.dct(np.float32(gray) / 255.0)
    high_freq_energy = np.sum(np.abs(dct[32:, 32:])) / np.sum(np.abs(dct))

    # Edge density
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.count_nonzero(edges) / (width * height)

    # Noise estimation (using high-frequency components)
    noise_estimate = np.std(laplacian)

    return {
        "path": str(path_obj.name),
        "file_size_kb": round(file_size_kb, 2),
        "dimensions": f"{width}x{height}",
        "width": width,
        "height": height,
        "channels": channels,
        "megapixels": round(width * height / 1_000_000, 2),
        "blur_score": round(blur_score, 2),
        "mean_brightness": round(mean_brightness, 2),
        "contrast": round(contrast, 2),
        "high_freq_energy": round(high_freq_energy, 4),
        "edge_density": round(edge_density, 4),
        "noise_estimate": round(noise_estimate, 2),
    }

def time_preprocessing(image_path: str) -> Dict:
    """Time the DINOv2 preprocessing pipeline."""
    img = cv2.imread(image_path)
    if img is None:
        return {"error": f"Could not read image: {image_path}"}

    timings = {}

    # Time: Bilateral filter
    start = time.time()
    filtered = cv2.bilateralFilter(img, d=5, sigmaColor=50, sigmaSpace=50)
    timings['bilateral_filter_ms'] = round((time.time() - start) * 1000, 2)

    # Time: Contrast enhancement
    start = time.time()
    enhanced = cv2.convertScaleAbs(filtered, alpha=1.05, beta=3)
    timings['contrast_enhance_ms'] = round((time.time() - start) * 1000, 2)

    # Time: Resize to 224x224 (DINOv2 input)
    start = time.time()
    resized = cv2.resize(enhanced, (224, 224), interpolation=cv2.INTER_LANCZOS4)
    timings['resize_ms'] = round((time.time() - start) * 1000, 2)

    # Time: RGB conversion (simulated)
    start = time.time()
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    timings['rgb_convert_ms'] = round((time.time() - start) * 1000, 2)

    # Total preprocessing time
    timings['total_preprocess_ms'] = round(sum(timings.values()), 2)

    return timings

def compare_images(camera_path: str, test_path: str):
    """Compare camera capture vs test image."""
    print("="*80)
    print("CAMERA PERFORMANCE DIAGNOSTIC")
    print("="*80)
    print()

    # Analyze both images
    print("1. IMAGE PROPERTIES ANALYSIS")
    print("-" * 80)

    camera_props = analyze_image(camera_path)
    test_props = analyze_image(test_path)

    if "error" in camera_props or "error" in test_props:
        print("ERROR:", camera_props.get("error") or test_props.get("error"))
        return

    # Print side-by-side comparison
    print(f"{'Property':<25} {'Camera Capture':>20} {'Test Image':>20} {'Difference':>12}")
    print("-" * 80)

    for key in camera_props.keys():
        if key == "path":
            print(f"{'File':<25} {camera_props[key]:>20} {test_props[key]:>20}")
        elif isinstance(camera_props[key], (int, float)):
            cam_val = camera_props[key]
            test_val = test_props[key]
            diff = cam_val - test_val
            diff_pct = (diff / test_val * 100) if test_val != 0 else 0

            print(f"{key:<25} {cam_val:>20.2f} {test_val:>20.2f} {diff:>+10.2f} ({diff_pct:>+6.1f}%)")
        else:
            print(f"{key:<25} {str(camera_props[key]):>20} {str(test_props[key]):>20}")

    print()
    print("2. PREPROCESSING TIMING ANALYSIS")
    print("-" * 80)

    camera_timings = time_preprocessing(camera_path)
    test_timings = time_preprocessing(test_path)

    print(f"{'Operation':<30} {'Camera (ms)':>15} {'Test (ms)':>15} {'Diff (ms)':>12}")
    print("-" * 80)

    for key in camera_timings.keys():
        cam_time = camera_timings[key]
        test_time = test_timings[key]
        diff = cam_time - test_time
        print(f"{key:<30} {cam_time:>15.2f} {test_time:>15.2f} {diff:>+12.2f}")

    print()
    print("3. DIAGNOSTIC INSIGHTS")
    print("-" * 80)

    insights = []

    # Resolution difference
    if camera_props['megapixels'] > test_props['megapixels'] * 1.5:
        insights.append(f"⚠️  RESOLUTION OVERHEAD: Camera capture is {camera_props['megapixels']:.1f}MP vs test {test_props['megapixels']:.1f}MP")
        insights.append(f"   → Bilateral filter processes {camera_props['megapixels'] / test_props['megapixels']:.1f}x more pixels")
        insights.append(f"   → Recommendation: Downscale camera capture to 1280x720 before identification")

    # File size difference
    if camera_props['file_size_kb'] > test_props['file_size_kb'] * 2:
        insights.append(f"⚠️  FILE SIZE OVERHEAD: Camera {camera_props['file_size_kb']:.0f}KB vs test {test_props['file_size_kb']:.0f}KB")
        insights.append(f"   → {camera_props['file_size_kb'] / test_props['file_size_kb']:.1f}x larger file = more disk I/O")
        insights.append(f"   → Recommendation: Use JPEG quality 0.85 instead of 0.98")

    # Blur difference
    if camera_props['blur_score'] < test_props['blur_score'] * 0.7:
        insights.append(f"⚠️  BLUR DETECTED: Camera blur score {camera_props['blur_score']:.0f} vs test {test_props['blur_score']:.0f}")
        insights.append(f"   → Camera capture may be out of focus or motion-blurred")
        insights.append(f"   → Recommendation: Improve camera focus, lighting, or stability")

    # Compression artifacts
    if camera_props['high_freq_energy'] < test_props['high_freq_energy'] * 0.8:
        insights.append(f"⚠️  COMPRESSION ARTIFACTS: Camera has {camera_props['high_freq_energy']:.4f} high-freq energy vs test {test_props['high_freq_energy']:.4f}")
        insights.append(f"   → Heavy JPEG compression detected")
        insights.append(f"   → May affect geometric matching (ORB keypoints)")

    # Preprocessing time
    total_diff = camera_timings['total_preprocess_ms'] - test_timings['total_preprocess_ms']
    if total_diff > 50:
        insights.append(f"⚠️  PREPROCESSING OVERHEAD: Camera takes +{total_diff:.0f}ms longer to preprocess")
        insights.append(f"   → Bilateral filter: +{camera_timings['bilateral_filter_ms'] - test_timings['bilateral_filter_ms']:.0f}ms (resolution dependent)")
        insights.append(f"   → Recommendation: Downscale before preprocessing")

    if not insights:
        insights.append("✅ No significant performance issues detected!")
        insights.append("   Camera and test images have similar characteristics.")

    for insight in insights:
        print(insight)

    print()
    print("4. RECOMMENDED FIXES")
    print("-" * 80)

    fixes = []

    # Based on insights, suggest fixes
    if camera_props['megapixels'] > 2.0:  # > 1920x1080
        fixes.append("1. DOWNSCALE CAMERA CAPTURES")
        fixes.append("   Location: apps/desktop/src/renderer/components/CameraView.tsx:593")
        fixes.append("   Change: Add downscaling before saving capture")
        fixes.append("   Code:")
        fixes.append("   ```typescript")
        fixes.append("   // Before saving, downscale to max 1280x720 (0.92 MP)")
        fixes.append("   const maxWidth = 1280;")
        fixes.append("   const maxHeight = 720;")
        fixes.append("   if (canvas.width > maxWidth || canvas.height > maxHeight) {")
        fixes.append("     const scale = Math.min(maxWidth / canvas.width, maxHeight / canvas.height);")
        fixes.append("     const scaledCanvas = document.createElement('canvas');")
        fixes.append("     scaledCanvas.width = canvas.width * scale;")
        fixes.append("     scaledCanvas.height = canvas.height * scale;")
        fixes.append("     const ctx = scaledCanvas.getContext('2d');")
        fixes.append("     ctx.drawImage(canvas, 0, 0, scaledCanvas.width, scaledCanvas.height);")
        fixes.append("     imageData = scaledCanvas.toDataURL('image/jpeg', 0.85);")
        fixes.append("   }")
        fixes.append("   ```")
        fixes.append("   Impact: ~50-70% faster identification")
        fixes.append("")

    if camera_props['file_size_kb'] > 500:
        fixes.append("2. REDUCE JPEG QUALITY")
        fixes.append("   Location: apps/desktop/src/renderer/constants.ts:13")
        fixes.append("   Change: CAPTURE_JPEG_QUALITY from 0.98 to 0.85")
        fixes.append("   Impact: ~30-40% smaller file, negligible quality loss for card identification")
        fixes.append("")

    fixes.append("3. MONITOR REAL-WORLD CAMERA TIMING")
    fixes.append("   Add timing instrumentation in identification_service.py to measure:")
    fixes.append("   - File read time")
    fixes.append("   - Preprocessing time")
    fixes.append("   - Feature extraction time")
    fixes.append("   - Geometric verification time")
    fixes.append("")

    for fix in fixes:
        print(fix)

    print()
    print("="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)

    # Save report
    report = {
        "camera": {
            "properties": camera_props,
            "timings": camera_timings,
        },
        "test": {
            "properties": test_props,
            "timings": test_timings,
        },
        "insights": insights,
        "fixes": fixes,
    }

    report_path = Path("camera_performance_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"📄 Full report saved to: {report_path}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python diagnose_camera_performance.py <camera_capture.jpg> <test_image.jpg>")
        print()
        print("Example:")
        print("  python diagnose_camera_performance.py ~/AppData/Local/Temp/cardflux/capture-123.jpg test-images/one-piece/bege.png")
        sys.exit(1)

    camera_path = sys.argv[1]
    test_path = sys.argv[2]

    if not Path(camera_path).exists():
        print(f"ERROR: Camera capture not found: {camera_path}")
        sys.exit(1)

    if not Path(test_path).exists():
        print(f"ERROR: Test image not found: {test_path}")
        sys.exit(1)

    compare_images(camera_path, test_path)

if __name__ == "__main__":
    main()
