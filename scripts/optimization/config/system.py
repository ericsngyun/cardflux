#!/usr/bin/env python3
"""
Configuration Management System
Handles config versioning, inheritance, and parameter sweeps
"""
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from copy import deepcopy
import itertools


@dataclass
class ConfigParameter:
    """Definition of a configuration parameter"""
    name: str
    value: Any
    param_type: str  # "int", "float", "bool", "string", "enum"
    valid_range: Optional[tuple] = None  # For numeric types
    valid_values: Optional[List[Any]] = None  # For enum types
    description: str = ""
    category: str = "general"  # For organization: "dinov2", "orb", "faiss", "fusion", etc.

    def validate(self) -> bool:
        """Validate parameter value"""
        if self.param_type in ["int", "float"]:
            if self.valid_range:
                return self.valid_range[0] <= self.value <= self.valid_range[1]
        elif self.param_type == "enum":
            if self.valid_values:
                return self.value in self.valid_values
        elif self.param_type == "bool":
            return isinstance(self.value, bool)
        return True


@dataclass
class Configuration:
    """Complete system configuration"""
    config_id: str
    name: str
    description: str
    parameters: Dict[str, ConfigParameter]
    parent_config_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: time.strftime('%Y-%m-%d %H:%M:%S'))
    git_commit: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def get_param_value(self, name: str) -> Any:
        """Get parameter value by name"""
        if name not in self.parameters:
            raise KeyError(f"Parameter '{name}' not found in configuration")
        return self.parameters[name].value

    def set_param_value(self, name: str, value: Any):
        """Set parameter value by name"""
        if name not in self.parameters:
            raise KeyError(f"Parameter '{name}' not found in configuration")
        self.parameters[name].value = value
        if not self.parameters[name].validate():
            raise ValueError(f"Invalid value {value} for parameter '{name}'")

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'config_id': self.config_id,
            'name': self.name,
            'description': self.description,
            'parameters': {k: asdict(v) for k, v in self.parameters.items()},
            'parent_config_id': self.parent_config_id,
            'created_at': self.created_at,
            'git_commit': self.git_commit,
            'tags': self.tags
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Configuration':
        """Load from dictionary"""
        params = {
            k: ConfigParameter(**v)
            for k, v in data['parameters'].items()
        }
        return Configuration(
            config_id=data['config_id'],
            name=data['name'],
            description=data['description'],
            parameters=params,
            parent_config_id=data.get('parent_config_id'),
            created_at=data['created_at'],
            git_commit=data.get('git_commit'),
            tags=data.get('tags', [])
        )

    def compute_hash(self) -> str:
        """Compute hash of parameter values for quick comparison"""
        # Sort parameters for consistent hashing
        param_str = json.dumps(
            {k: v.value for k, v in sorted(self.parameters.items())},
            sort_keys=True
        )
        return hashlib.md5(param_str.encode()).hexdigest()[:8]


class ConfigurationManager:
    """
    Manages configurations: creation, versioning, inheritance, sweeps
    """

    def __init__(self, config_dir: str = None):
        """
        Args:
            config_dir: Directory to store configurations
        """
        if config_dir is None:
            config_dir = Path(__file__).parent / "configs"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.configs: Dict[str, Configuration] = {}
        self._load_all_configs()

    def _load_all_configs(self):
        """Load all configs from disk"""
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config = Configuration.from_dict(data)
                    self.configs[config.config_id] = config
            except Exception as e:
                print(f"Warning: Failed to load config {config_file}: {e}")

    def create_baseline_config(self) -> Configuration:
        """
        Create baseline configuration from current system

        This represents the current production configuration as the starting point.
        """
        params = {
            # DINOv2 Configuration
            "dinov2_model": ConfigParameter(
                name="dinov2_model",
                value="facebook/dinov2-small",
                param_type="enum",
                valid_values=["facebook/dinov2-small", "facebook/dinov2-base", "facebook/dinov2-large"],
                description="DINOv2 model size",
                category="dinov2"
            ),
            "dinov2_preprocessing_bilateral": ConfigParameter(
                name="dinov2_preprocessing_bilateral",
                value=True,
                param_type="bool",
                description="Apply bilateral filter preprocessing",
                category="dinov2"
            ),
            "dinov2_preprocessing_contrast": ConfigParameter(
                name="dinov2_preprocessing_contrast",
                value=True,
                param_type="bool",
                description="Apply contrast enhancement preprocessing",
                category="dinov2"
            ),
            "dinov2_bilateral_d": ConfigParameter(
                name="dinov2_bilateral_d",
                value=5,
                param_type="int",
                valid_range=(3, 15),
                description="Bilateral filter diameter",
                category="dinov2"
            ),
            "dinov2_bilateral_sigma_color": ConfigParameter(
                name="dinov2_bilateral_sigma_color",
                value=50,
                param_type="int",
                valid_range=(10, 150),
                description="Bilateral filter sigma color",
                category="dinov2"
            ),
            "dinov2_bilateral_sigma_space": ConfigParameter(
                name="dinov2_bilateral_sigma_space",
                value=50,
                param_type="int",
                valid_range=(10, 150),
                description="Bilateral filter sigma space",
                category="dinov2"
            ),
            "dinov2_contrast_alpha": ConfigParameter(
                name="dinov2_contrast_alpha",
                value=1.05,
                param_type="float",
                valid_range=(0.8, 1.5),
                description="Contrast enhancement alpha",
                category="dinov2"
            ),
            "dinov2_contrast_beta": ConfigParameter(
                name="dinov2_contrast_beta",
                value=3,
                param_type="int",
                valid_range=(0, 20),
                description="Contrast enhancement beta",
                category="dinov2"
            ),

            # FAISS Configuration
            "faiss_index_type": ConfigParameter(
                name="faiss_index_type",
                value="Flat",
                param_type="enum",
                valid_values=["Flat", "IVFFlat", "HNSW"],
                description="FAISS index type",
                category="faiss"
            ),
            "faiss_top_k": ConfigParameter(
                name="faiss_top_k",
                value=50,
                param_type="int",
                valid_range=(10, 200),
                description="Number of candidates to retrieve",
                category="faiss"
            ),

            # ORB Configuration
            "orb_enabled": ConfigParameter(
                name="orb_enabled",
                value=True,
                param_type="bool",
                description="Enable ORB geometric verification",
                category="orb"
            ),
            "orb_nfeatures": ConfigParameter(
                name="orb_nfeatures",
                value=1000,
                param_type="int",
                valid_range=(100, 5000),
                description="Number of ORB features",
                category="orb"
            ),
            "orb_scaleFactor": ConfigParameter(
                name="orb_scaleFactor",
                value=1.2,
                param_type="float",
                valid_range=(1.1, 2.0),
                description="ORB scale factor",
                category="orb"
            ),
            "orb_nlevels": ConfigParameter(
                name="orb_nlevels",
                value=8,
                param_type="int",
                valid_range=(4, 16),
                description="ORB pyramid levels",
                category="orb"
            ),
            "orb_edgeThreshold": ConfigParameter(
                name="orb_edgeThreshold",
                value=15,
                param_type="int",
                valid_range=(5, 50),
                description="ORB edge threshold",
                category="orb"
            ),
            "orb_lowe_ratio": ConfigParameter(
                name="orb_lowe_ratio",
                value=0.80,
                param_type="float",
                valid_range=(0.6, 0.9),
                description="Lowe's ratio test threshold",
                category="orb"
            ),
            "orb_verify_top_n": ConfigParameter(
                name="orb_verify_top_n",
                value=10,
                param_type="int",
                valid_range=(5, 50),
                description="Number of top candidates to verify with ORB",
                category="orb"
            ),
            "orb_early_stop_visual": ConfigParameter(
                name="orb_early_stop_visual",
                value=0.85,
                param_type="float",
                valid_range=(0.7, 0.95),
                description="Visual score threshold for early stopping",
                category="orb"
            ),
            "orb_early_stop_geometric": ConfigParameter(
                name="orb_early_stop_geometric",
                value=0.80,
                param_type="float",
                valid_range=(0.5, 1.0),
                description="Geometric score threshold for early stopping",
                category="orb"
            ),

            # SIFT Configuration
            "sift_enabled": ConfigParameter(
                name="sift_enabled",
                value=True,
                param_type="bool",
                description="Enable SIFT in cascade",
                category="sift"
            ),
            "sift_nfeatures": ConfigParameter(
                name="sift_nfeatures",
                value=1000,
                param_type="int",
                valid_range=(100, 5000),
                description="Number of SIFT features",
                category="sift"
            ),
            "sift_cascade_threshold": ConfigParameter(
                name="sift_cascade_threshold",
                value=0.12,
                param_type="float",
                valid_range=(0.05, 0.3),
                description="SIFT score threshold for cascade",
                category="sift"
            ),

            # AKAZE Configuration
            "akaze_enabled": ConfigParameter(
                name="akaze_enabled",
                value=True,
                param_type="bool",
                description="Enable AKAZE in cascade",
                category="akaze"
            ),
            "akaze_cascade_threshold": ConfigParameter(
                name="akaze_cascade_threshold",
                value=0.10,
                param_type="float",
                valid_range=(0.05, 0.3),
                description="ORB score threshold before trying AKAZE",
                category="akaze"
            ),

            # Score Fusion Configuration
            "fusion_strategy": ConfigParameter(
                name="fusion_strategy",
                value="dynamic",
                param_type="enum",
                valid_values=["fixed", "dynamic", "learned"],
                description="Score fusion strategy",
                category="fusion"
            ),
            "fusion_visual_weight_high_geom": ConfigParameter(
                name="fusion_visual_weight_high_geom",
                value=0.75,
                param_type="float",
                valid_range=(0.5, 1.0),
                description="Visual weight when geometric > 0.15",
                category="fusion"
            ),
            "fusion_geometric_weight_high_geom": ConfigParameter(
                name="fusion_geometric_weight_high_geom",
                value=0.25,
                param_type="float",
                valid_range=(0.0, 0.5),
                description="Geometric weight when geometric > 0.15",
                category="fusion"
            ),
            "fusion_visual_weight_mid_geom": ConfigParameter(
                name="fusion_visual_weight_mid_geom",
                value=0.85,
                param_type="float",
                valid_range=(0.5, 1.0),
                description="Visual weight when geometric 0.05-0.15",
                category="fusion"
            ),
            "fusion_geometric_weight_mid_geom": ConfigParameter(
                name="fusion_geometric_weight_mid_geom",
                value=0.15,
                param_type="float",
                valid_range=(0.0, 0.5),
                description="Geometric weight when geometric 0.05-0.15",
                category="fusion"
            ),
            "fusion_visual_weight_low_geom": ConfigParameter(
                name="fusion_visual_weight_low_geom",
                value=0.95,
                param_type="float",
                valid_range=(0.8, 1.0),
                description="Visual weight when geometric < 0.05",
                category="fusion"
            ),
            "fusion_geometric_weight_low_geom": ConfigParameter(
                name="fusion_geometric_weight_low_geom",
                value=0.05,
                param_type="float",
                valid_range=(0.0, 0.2),
                description="Geometric weight when geometric < 0.05",
                category="fusion"
            ),

            # Confidence Thresholds
            "threshold_high": ConfigParameter(
                name="threshold_high",
                value=0.65,
                param_type="float",
                valid_range=(0.5, 0.9),
                description="High confidence threshold",
                category="confidence"
            ),
            "threshold_moderate": ConfigParameter(
                name="threshold_moderate",
                value=0.55,
                param_type="float",
                valid_range=(0.4, 0.8),
                description="Moderate confidence threshold",
                category="confidence"
            ),
            "threshold_margin": ConfigParameter(
                name="threshold_margin",
                value=0.05,
                param_type="float",
                valid_range=(0.02, 0.15),
                description="Margin for confidence boost",
                category="confidence"
            ),

            # OCR Configuration
            "ocr_enabled": ConfigParameter(
                name="ocr_enabled",
                value=True,
                param_type="bool",
                description="Enable OCR card number extraction",
                category="ocr"
            ),
            "ocr_hard_filter_enabled": ConfigParameter(
                name="ocr_hard_filter_enabled",
                value=True,
                param_type="bool",
                description="Enable OCR hard filter (narrow to matching cards)",
                category="ocr"
            ),
            "ocr_hard_filter_confidence": ConfigParameter(
                name="ocr_hard_filter_confidence",
                value=0.80,
                param_type="float",
                valid_range=(0.6, 0.95),
                description="OCR confidence threshold for hard filter",
                category="ocr"
            ),
            "ocr_hard_filter_min_matches": ConfigParameter(
                name="ocr_hard_filter_min_matches",
                value=3,
                param_type="int",
                valid_range=(1, 10),
                description="Minimum matching cards for hard filter",
                category="ocr"
            ),
            "ocr_card_number_boost": ConfigParameter(
                name="ocr_card_number_boost",
                value=0.12,
                param_type="float",
                valid_range=(0.0, 0.30),
                description="Score boost for card number match",
                category="ocr"
            ),
        }

        config = Configuration(
            config_id=f"baseline_{int(time.time())}",
            name="Baseline Configuration",
            description="Current production system configuration",
            parameters=params,
            tags=["baseline", "production"]
        )

        self._save_config(config)
        return config

    def create_variant(self, parent_config: Configuration, name: str,
                      description: str, param_changes: Dict[str, Any],
                      tags: List[str] = None) -> Configuration:
        """
        Create a variant configuration from a parent

        Args:
            parent_config: Parent configuration
            name: Name for new config
            description: Description of changes
            param_changes: Dict of {param_name: new_value}
            tags: Optional tags

        Returns:
            New Configuration object
        """
        # Deep copy parent parameters
        new_params = deepcopy(parent_config.parameters)

        # Apply changes
        for param_name, new_value in param_changes.items():
            if param_name not in new_params:
                raise KeyError(f"Parameter '{param_name}' not found in parent config")
            new_params[param_name].value = new_value
            if not new_params[param_name].validate():
                raise ValueError(f"Invalid value {new_value} for parameter '{param_name}'")

        # Create new config
        config = Configuration(
            config_id=f"variant_{int(time.time())}_{parent_config.compute_hash()}",
            name=name,
            description=description,
            parameters=new_params,
            parent_config_id=parent_config.config_id,
            tags=tags or []
        )

        self._save_config(config)
        return config

    def generate_parameter_sweep(self, base_config: Configuration,
                                 param_ranges: Dict[str, List[Any]],
                                 max_configs: int = 100) -> List[Configuration]:
        """
        Generate configurations for parameter sweep

        Args:
            base_config: Base configuration
            param_ranges: Dict of {param_name: [value1, value2, ...]}
            max_configs: Maximum number of configs to generate

        Returns:
            List of Configuration objects
        """
        param_names = list(param_ranges.keys())
        param_values = [param_ranges[name] for name in param_names]

        # Generate all combinations
        combinations = list(itertools.product(*param_values))

        # Limit to max_configs
        if len(combinations) > max_configs:
            print(f"Warning: {len(combinations)} combinations generated, limiting to {max_configs}")
            # Sample evenly
            step = len(combinations) // max_configs
            combinations = combinations[::step][:max_configs]

        configs = []
        for combo in combinations:
            param_changes = dict(zip(param_names, combo))

            # Create descriptive name
            name = f"sweep_{'-'.join(f'{k}={v}' for k, v in param_changes.items())}"

            config = self.create_variant(
                parent_config=base_config,
                name=name,
                description=f"Parameter sweep: {param_changes}",
                param_changes=param_changes,
                tags=["sweep"]
            )
            configs.append(config)

        print(f"Generated {len(configs)} configurations for parameter sweep")
        return configs

    def _save_config(self, config: Configuration):
        """Save configuration to disk"""
        config_file = self.config_dir / f"{config.config_id}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2)

        self.configs[config.config_id] = config

    def load_config(self, config_id: str) -> Configuration:
        """Load configuration by ID"""
        if config_id in self.configs:
            return self.configs[config_id]

        config_file = self.config_dir / f"{config_id}.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration not found: {config_id}")

        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            config = Configuration.from_dict(data)
            self.configs[config_id] = config
            return config

    def list_configs(self, tags: Optional[List[str]] = None) -> List[Configuration]:
        """List all configurations, optionally filtered by tags"""
        configs = list(self.configs.values())

        if tags:
            configs = [c for c in configs if any(tag in c.tags for tag in tags)]

        return sorted(configs, key=lambda c: c.created_at, reverse=True)

    def delete_config(self, config_id: str):
        """Delete a configuration"""
        config_file = self.config_dir / f"{config_id}.json"
        if config_file.exists():
            config_file.unlink()

        if config_id in self.configs:
            del self.configs[config_id]


if __name__ == "__main__":
    # Example usage
    manager = ConfigurationManager()

    # Create baseline
    baseline = manager.create_baseline_config()
    print(f"Created baseline config: {baseline.config_id}")

    # Create a variant
    variant = manager.create_variant(
        parent_config=baseline,
        name="Faster ORB",
        description="Reduce ORB features for speed",
        param_changes={"orb_nfeatures": 500, "orb_verify_top_n": 5},
        tags=["speed-optimization"]
    )
    print(f"Created variant config: {variant.config_id}")

    # List configs
    print("\nAll configs:")
    for config in manager.list_configs():
        print(f"  {config.config_id}: {config.name}")
