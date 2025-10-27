#!/usr/bin/env python3
"""
Configuration-Aware Identifier
Applies configuration parameters to ProductionCardIdentifier
"""
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "identification" / "core"))

from production_card_identifier import ProductionCardIdentifier


class ConfigurableIdentifier(ProductionCardIdentifier):
    """
    Extends ProductionCardIdentifier to apply configuration parameters

    This wrapper intercepts configuration and applies parameters before/during identification.
    """

    def __init__(self, config: Dict[str, Any], game: str = "one-piece", verbose: bool = False):
        """
        Args:
            config: Configuration dict with parameters
            game: TCG game
            verbose: Print messages
        """
        self.config = config

        # Extract parameter values
        params = {k: v.get('value') if isinstance(v, dict) else v
                 for k, v in config.get('parameters', {}).items()}

        # Initialize base identifier
        super().__init__(game=game, verbose=verbose, enable_variant_classifier=True)

        # Apply configuration after initialization
        self._apply_configuration(params)

    def _apply_configuration(self, params: Dict[str, Any]):
        """Apply configuration parameters to identifier"""

        # DINOv2 preprocessing parameters (stored for use in _get_image_embedding)
        self.config_bilateral_enabled = params.get('dinov2_preprocessing_bilateral', True)
        self.config_contrast_enabled = params.get('dinov2_preprocessing_contrast', True)
        self.config_bilateral_d = params.get('dinov2_bilateral_d', 5)
        self.config_bilateral_sigma_color = params.get('dinov2_bilateral_sigma_color', 50)
        self.config_bilateral_sigma_space = params.get('dinov2_bilateral_sigma_space', 50)
        self.config_contrast_alpha = params.get('dinov2_contrast_alpha', 1.05)
        self.config_contrast_beta = params.get('dinov2_contrast_beta', 3)

        # ORB configuration
        if hasattr(self, 'orb'):
            orb_nfeatures = params.get('orb_nfeatures', 1000)
            orb_scaleFactor = params.get('orb_scaleFactor', 1.2)
            orb_nlevels = params.get('orb_nlevels', 8)
            orb_edgeThreshold = params.get('orb_edgeThreshold', 15)

            # Recreate ORB with new parameters
            import cv2
            self.orb = cv2.ORB_create(
                nfeatures=orb_nfeatures,
                scaleFactor=orb_scaleFactor,
                nlevels=orb_nlevels,
                edgeThreshold=orb_edgeThreshold,
                firstLevel=0,
                WTA_K=2,
                patchSize=31
            )

        # Store other configuration for runtime use
        self.config_orb_enabled = params.get('orb_enabled', True)
        self.config_orb_lowe_ratio = params.get('orb_lowe_ratio', 0.80)
        self.config_orb_verify_top_n = params.get('orb_verify_top_n', 10)
        self.config_orb_early_stop_visual = params.get('orb_early_stop_visual', 0.85)
        self.config_orb_early_stop_geometric = params.get('orb_early_stop_geometric', 0.80)

        # SIFT configuration
        self.config_sift_enabled = params.get('sift_enabled', True)
        self.config_sift_cascade_threshold = params.get('sift_cascade_threshold', 0.12)

        # AKAZE configuration
        self.config_akaze_enabled = params.get('akaze_enabled', True)
        self.config_akaze_cascade_threshold = params.get('akaze_cascade_threshold', 0.10)

        # Score fusion configuration
        self.config_fusion_visual_high = params.get('fusion_visual_weight_high_geom', 0.75)
        self.config_fusion_geometric_high = params.get('fusion_geometric_weight_high_geom', 0.25)
        self.config_fusion_visual_mid = params.get('fusion_visual_weight_mid_geom', 0.85)
        self.config_fusion_geometric_mid = params.get('fusion_geometric_weight_mid_geom', 0.15)
        self.config_fusion_visual_low = params.get('fusion_visual_weight_low_geom', 0.95)
        self.config_fusion_geometric_low = params.get('fusion_geometric_weight_low_geom', 0.05)

        # Confidence thresholds
        self.config_threshold_high = params.get('threshold_high', 0.65)
        self.config_threshold_moderate = params.get('threshold_moderate', 0.55)
        self.config_threshold_margin = params.get('threshold_margin', 0.05)

        # OCR configuration
        self.config_ocr_enabled = params.get('ocr_enabled', True)
        self.config_ocr_hard_filter = params.get('ocr_hard_filter_enabled', True)
        self.config_ocr_hard_filter_conf = params.get('ocr_hard_filter_confidence', 0.80)
        self.config_ocr_hard_filter_min = params.get('ocr_hard_filter_min_matches', 3)
        self.config_ocr_boost = params.get('ocr_card_number_boost', 0.12)

        # FAISS configuration
        self.config_faiss_top_k = params.get('faiss_top_k', 50)

    def _get_image_embedding(self, image_path: str):
        """Override to use configured preprocessing parameters"""
        from PIL import Image
        import numpy as np
        import cv2

        image = Image.open(image_path).convert("RGB")
        img_array = np.array(image)

        # Apply configured preprocessing
        if self.config_bilateral_enabled:
            img_array = cv2.bilateralFilter(
                img_array,
                self.config_bilateral_d,
                self.config_bilateral_sigma_color,
                self.config_bilateral_sigma_space
            )

        if self.config_contrast_enabled:
            img_array = cv2.convertScaleAbs(
                img_array,
                alpha=self.config_contrast_alpha,
                beta=self.config_contrast_beta
            )

        image = Image.fromarray(img_array)

        # Generate embedding
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        import torch
        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state[:, 0].cpu().numpy()[0]

        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def identify(self, image_path: str, top_k: int = None, use_geometric: bool = None, tcg_hint: str = None):
        """Override to use configured parameters"""

        # Use config values if not overridden
        if top_k is None:
            top_k = self.config_faiss_top_k
        if use_geometric is None:
            use_geometric = self.config_orb_enabled

        # Call parent identify with configured parameters
        result = super().identify(image_path, top_k, use_geometric, tcg_hint)

        # Apply configured thresholds to confidence determination
        best = result['best_match']
        margin = 0.0
        if len(result['matches']) > 1:
            margin = best['final_score'] - result['matches'][1]['final_score']

        # Re-evaluate confidence with configured thresholds
        confidence = "LOW"
        if best['final_score'] >= self.config_threshold_high:
            confidence = "HIGH"
        elif best['final_score'] >= self.config_threshold_moderate and margin >= self.config_threshold_margin:
            confidence = "HIGH"
        elif best['final_score'] >= self.config_threshold_moderate:
            confidence = "MODERATE"
        elif best['geometric_score'] > 0.3 and best['visual_score'] > 0.65:
            confidence = "MODERATE"
        elif margin >= self.config_threshold_margin * 1.5:
            confidence = "MODERATE"

        result['confidence'] = confidence

        return result

    def _compute_orb_similarity(self, query_path: str, candidate_path: str) -> float:
        """Override to use configured Lowe's ratio"""
        import cv2
        import numpy as np
        from pathlib import Path

        try:
            img1 = cv2.imread(query_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(candidate_path, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None:
                return 0.0

            # Preprocessing (same as parent)
            img1 = cv2.bilateralFilter(img1, 5, 50, 50)
            img2 = cv2.bilateralFilter(img2, 5, 50, 50)

            min_size = 400
            if min(img1.shape) < min_size:
                scale = min_size / min(img1.shape)
                img1 = cv2.resize(img1, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            if min(img2.shape) < min_size:
                scale = min_size / min(img2.shape)
                img2 = cv2.resize(img2, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img1 = clahe.apply(img1)
            img2 = clahe.apply(img2)

            # Detect features
            kp1, des1 = self.orb.detectAndCompute(img1, None)

            if des1 is None or len(des1) < 8:
                return 0.0

            # Get candidate features
            candidate_id = Path(candidate_path).stem

            if hasattr(self, 'precomputed_keypoints') and self.precomputed_keypoints is not None and candidate_id in self.precomputed_keypoints:
                ref_data = self.precomputed_keypoints[candidate_id].item()
                des2 = ref_data.get('descriptors')
                if des2 is None or len(des2) < 8:
                    return 0.0
                num_kp2 = ref_data.get('num_keypoints', len(des2))
            else:
                kp2, des2 = self.orb.detectAndCompute(img2, None)
                if des2 is None or len(des2) < 8:
                    return 0.0
                num_kp2 = len(kp2)

            # Match with configured Lowe's ratio
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)

            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < self.config_orb_lowe_ratio * n.distance:
                        good_matches.append(m)

            if len(good_matches) < 3:
                return 0.0

            # Calculate score
            num_keypoints_max = max(len(kp1), num_kp2)
            num_keypoints_min = min(len(kp1), num_kp2)

            match_ratio = len(good_matches) / num_keypoints_max
            coverage_ratio = len(good_matches) / num_keypoints_min

            avg_distance = np.mean([m.distance for m in good_matches])
            distance_quality = 1.0 / (1.0 + avg_distance / 40.0)

            score = (match_ratio * 0.5 + coverage_ratio * 0.3 + distance_quality * 0.20)
            final_score = min(score * 2.2, 1.0)

            return final_score

        except Exception as e:
            if self.verbose:
                print(f"  Warning: ORB matching error: {e}")
            return 0.0

    def _compute_geometric_similarity_hybrid(self, query_path: str, candidate_path: str) -> float:
        """Override to use configured cascade thresholds"""

        # SIFT (if enabled)
        if self.config_sift_enabled:
            sift_score = self._compute_sift_similarity(query_path, candidate_path)
            if sift_score > self.config_sift_cascade_threshold:
                return sift_score
        else:
            sift_score = 0.0

        # ORB
        orb_score = self._compute_orb_similarity(query_path, candidate_path)
        if orb_score > self.config_akaze_cascade_threshold:
            return orb_score

        # AKAZE (if enabled)
        if self.config_akaze_enabled:
            akaze_score = self._compute_akaze_similarity(query_path, candidate_path)
            return max(sift_score, orb_score, akaze_score)

        return max(sift_score, orb_score)


if __name__ == "__main__":
    print("ConfigurableIdentifier Module")
    print("Use this to apply configuration parameters to identifier")
