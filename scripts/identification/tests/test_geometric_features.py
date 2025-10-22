#!/usr/bin/env python3
"""
Test different feature detectors to find best solution for watermarked images.
"""
import cv2
import numpy as np
from pathlib import Path
import time

def test_orb(img1, img2, name="ORB"):
    """Test ORB feature matching."""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")

    start = time.time()

    # Create detector
    orb = cv2.ORB_create(nfeatures=500)

    # Detect keypoints
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)

    print(f"Query keypoints: {len(kp1) if kp1 else 0}")
    print(f"Database keypoints: {len(kp2) if kp2 else 0}")

    if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
        print(f"Insufficient keypoints")
        return 0.0

    # Match
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)

    # Ratio test
    good = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.75 * n.distance:
                good.append(m)

    print(f"Good matches: {len(good)}")

    if len(good) < 4:
        print(f"Too few good matches")
        return 0.0

    # Calculate score
    ratio = len(good) / max(len(kp1), len(kp2))
    score = min(ratio * 3.0, 1.0)

    elapsed = (time.time() - start) * 1000
    print(f"Score: {score:.4f}")
    print(f"Time: {elapsed:.1f}ms")

    return score


def test_sift(img1, img2, name="SIFT"):
    """Test SIFT feature matching."""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")

    start = time.time()

    # Create detector
    sift = cv2.SIFT_create(nfeatures=500)

    # Detect keypoints
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)

    print(f"Query keypoints: {len(kp1) if kp1 else 0}")
    print(f"Database keypoints: {len(kp2) if kp2 else 0}")

    if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
        print(f"Insufficient keypoints")
        return 0.0

    # Match with FLANN
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    matches = flann.knnMatch(des1, des2, k=2)

    # Ratio test
    good = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.7 * n.distance:
                good.append(m)

    print(f"Good matches: {len(good)}")

    if len(good) < 4:
        print(f"Too few good matches")
        return 0.0

    # Calculate score
    ratio = len(good) / max(len(kp1), len(kp2))
    score = min(ratio * 2.0, 1.0)

    elapsed = (time.time() - start) * 1000
    print(f"Score: {score:.4f}")
    print(f"Time: {elapsed:.1f}ms")

    return score


def test_akaze(img1, img2, name="AKAZE"):
    """Test AKAZE feature matching."""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")

    start = time.time()

    # Create detector
    akaze = cv2.AKAZE_create()

    # Detect keypoints
    kp1, des1 = akaze.detectAndCompute(img1, None)
    kp2, des2 = akaze.detectAndCompute(img2, None)

    print(f"Query keypoints: {len(kp1) if kp1 else 0}")
    print(f"Database keypoints: {len(kp2) if kp2 else 0}")

    if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
        print(f"Insufficient keypoints")
        return 0.0

    # Match
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)

    # Ratio test
    good = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.75 * n.distance:
                good.append(m)

    print(f"Good matches: {len(good)}")

    if len(good) < 4:
        print(f"Too few good matches")
        return 0.0

    # Calculate score
    ratio = len(good) / max(len(kp1), len(kp2))
    score = min(ratio * 2.5, 1.0)

    elapsed = (time.time() - start) * 1000
    print(f"Score: {score:.4f}")
    print(f"Time: {elapsed:.1f}ms")

    return score


def main():
    # Test images
    query_path = "test-images/one-piece/blackbeard.png"
    db_path = "data/images/one-piece/597035.jpg"

    print("="*60)
    print("GEOMETRIC FEATURE DETECTOR COMPARISON")
    print("="*60)
    print(f"Query: {query_path} (clean card photo)")
    print(f"Database: {db_path} (watermarked image)")

    # Load images
    img1 = cv2.imread(query_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(db_path, cv2.IMREAD_GRAYSCALE)

    if img1 is None or img2 is None:
        print("ERROR: Could not load images")
        return

    print(f"\nQuery shape: {img1.shape}")
    print(f"Database shape: {img2.shape}")

    # Minimal upscaling for small images
    if min(img1.shape) < 200:
        scale = 200 / min(img1.shape)
        img1 = cv2.resize(img1, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        print(f"Upscaled query to: {img1.shape}")

    if min(img2.shape) < 200:
        scale = 200 / min(img2.shape)
        img2 = cv2.resize(img2, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        print(f"Upscaled database to: {img2.shape}")

    # Test all detectors
    orb_score = test_orb(img1, img2)
    sift_score = test_sift(img1, img2)
    akaze_score = test_akaze(img1, img2)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"ORB:   {orb_score:.4f}")
    print(f"SIFT:  {sift_score:.4f}")
    print(f"AKAZE: {akaze_score:.4f}")
    print(f"\nBest: {'SIFT' if sift_score >= max(orb_score, akaze_score) else ('AKAZE' if akaze_score > orb_score else 'ORB')}")


if __name__ == "__main__":
    main()
