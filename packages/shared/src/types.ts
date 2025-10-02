/**
 * Core type definitions for CardFlux pipeline and desktop app.
 * These types are shared across all services and apps.
 */

export type GameId =
  | "mtg"
  | "pokemon"
  | "yugioh"
  | "onepiece"
  | "digimon"
  | string; // Allow future TCGs

export type Language = "en" | "ja" | "es" | "fr" | "de" | "it" | "pt" | string;

/**
 * Minimal card data for normalization pipeline.
 */
export interface CardCore {
  card_id: string; // Deterministic: SHA1(game_id|set_code|collector_number|language|artwork_hash?)
  game_id: GameId;
  set_code: string;
  set_name: string;
  collector_number: string;
  name: string;
  language: Language;
  printing_id?: string; // Optional: for tracking source data
  artwork_hash?: string; // Optional: for multi-art cards (One Piece)
  image_url?: string; // Source URL for fetching
  tcgplayer_id?: number;
  cardmarket_id?: number;
}

/**
 * Metadata stored per image directory.
 */
export interface ImageMeta {
  card_id: string;
  game_id: GameId;
  set_code: string;
  collector_number: string;
  name: string;
  language: Language;
  canonical_sha256: string; // Hash of canonical.jpg
  thumb_sha256: string;
  created_at: string; // ISO8601
  source_url?: string;
}

/**
 * Per-set FAISS shard metadata.
 */
export interface ShardMeta {
  game_id: GameId;
  set_code: string;
  vector_count: number;
  dimension: number;
  index_type: string; // e.g., "IVF64,PQ4"
  created_at: string;
  version: string; // e.g., "v2025.10"
}

/**
 * Single shard entry in index manifest.
 */
export interface IndexShardEntry {
  game_id: GameId;
  set_code: string;
  index_path: string; // POSIX: artifacts/faiss/{game}/{version}/index_ivfpq_shard_{set}.faiss
  ids_path: string; // POSIX
  meta_path: string; // POSIX
  index_sha256: string;
  ids_sha256: string;
  meta_sha256: string;
  vector_count: number;
}

/**
 * Top-level index manifest (published to CDN).
 */
export interface IndexManifest {
  schema_version: string; // e.g., "1.0.0"
  version: string; // e.g., "2025.10"
  created_at: string; // ISO8601
  games: GameId[];
  shards: IndexShardEntry[];
  metadata_snapshot: {
    path: string; // POSIX: artifacts/metadata/{version}/cards.sqlite.ro
    sha256: string;
    size_bytes: number;
  };
  models_manifest: {
    path: string; // POSIX: artifacts/models/model_manifest.json
    sha256: string;
  };
}

/**
 * Model manifest (ONNX models for embedding).
 */
export interface ModelManifest {
  schema_version: string;
  models: ModelEntry[];
  created_at: string;
}

export interface ModelEntry {
  model_id: string; // e.g., "dino_v2_small"
  path: string; // POSIX: artifacts/models/dino_v2_small.onnx
  sha256: string;
  size_bytes: number;
  input_size: number[]; // e.g., [224, 224]
  output_dim: number; // e.g., 384
}

/**
 * Price patch (versioned updates to SQLite).
 */
export interface PricePatch {
  version: string;
  base_version: string; // Which metadata version this applies to
  created_at: string;
  updates: PriceUpdate[];
}

export interface PriceUpdate {
  card_id: string;
  tcgplayer_market?: number;
  tcgplayer_low?: number;
  cardmarket_trend?: number;
  updated_at: string;
}

/**
 * Per-game configuration (loaded from packages/config).
 */
export interface GameConfig {
  game_id: GameId;
  display_name: string;
  collector_number_regex: string;
  set_code_regex: string;
  language_defaults: Language[];
  ocr_regions: {
    set_code: { x: number; y: number; w: number; h: number };
    collector_number: { x: number; y: number; w: number; h: number };
    [key: string]: { x: number; y: number; w: number; h: number }; // Game-specific fields
  };
  index_params: {
    nlist: number;
    m: number;
    nbits: number;
  };
  shard_strategy: "per_set"; // Future: "per_rarity", "by_size"
}
