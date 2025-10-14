/**
 * Zod schemas for runtime validation of manifests.
 * These schemas enforce the contract between pipeline and desktop app.
 */

import { z } from "zod";

// ============================================================================
// Base Types
// ============================================================================

export const GameIdSchema = z.enum([
  "mtg",
  "pokemon",
  "yugioh",
  "onepiece",
  "digimon",
]).or(z.string()); // Allow future TCGs

export const LanguageSchema = z.enum([
  "en",
  "ja",
  "es",
  "fr",
  "de",
  "it",
  "pt",
]).or(z.string()); // Allow future languages

// SHA256 hash validation (64 hex characters)
const sha256Schema = z.string().regex(/^[a-f0-9]{64}$/i, "Invalid SHA256 hash");

// Version format: vYYYY.MM (e.g., "v2025.10")
const versionSchema = z.string().regex(/^v?\d{4}\.\d{2}$/, "Version must be vYYYY.MM format");

// ISO8601 datetime
const iso8601Schema = z.string().datetime();

// POSIX path (forward slashes only)
const posixPathSchema = z.string().regex(/^[^\\]+$/, "Path must use forward slashes (POSIX)");

// ============================================================================
// Card and Image Metadata
// ============================================================================

export const CardCoreSchema = z.object({
  card_id: z.string().min(1), // SHA1(game_id|set_code|collector_number|language|artwork_hash?)
  game_id: GameIdSchema,
  set_code: z.string().min(1),
  set_name: z.string().min(1),
  collector_number: z.string().min(1),
  name: z.string().min(1),
  language: LanguageSchema,
  printing_id: z.string().optional(),
  artwork_hash: z.string().optional(),
  image_url: z.string().url().optional(),
  tcgplayer_id: z.number().int().optional(),
  cardmarket_id: z.number().int().optional(),
});

export const ImageMetaSchema = z.object({
  card_id: z.string().min(1),
  game_id: GameIdSchema,
  set_code: z.string().min(1),
  collector_number: z.string().min(1),
  name: z.string().min(1),
  language: LanguageSchema,
  canonical_sha256: sha256Schema,
  thumb_sha256: sha256Schema,
  created_at: iso8601Schema,
  source_url: z.string().url().optional(),
});

// ============================================================================
// FAISS Index Shards
// ============================================================================

export const ShardMetaSchema = z.object({
  game_id: GameIdSchema,
  set_code: z.string().min(1),
  vector_count: z.number().int().positive(),
  dimension: z.number().int().positive(),
  index_type: z.enum(["IndexFlatIP", "IndexFlatL2", "IndexIVFFlat", "IndexIVFPQ"]), // Strict validation
  created_at: iso8601Schema,
  version: versionSchema,
});

export const IndexShardEntrySchema = z.object({
  game_id: GameIdSchema,
  set_code: z.string().min(1),
  index_path: posixPathSchema,
  ids_path: posixPathSchema,
  meta_path: posixPathSchema,
  index_sha256: sha256Schema,
  ids_sha256: sha256Schema,
  meta_sha256: sha256Schema,
  vector_count: z.number().int().positive(),
});

// ============================================================================
// Index Manifest (Top-level CDN manifest)
// ============================================================================

export const IndexManifestSchema = z.object({
  schema_version: z.string().regex(/^\d+\.\d+\.\d+$/, "Must be semver format (e.g., 1.0.0)"),
  version: versionSchema,
  created_at: iso8601Schema,
  games: z.array(GameIdSchema),
  shards: z.array(IndexShardEntrySchema),
  metadata_snapshot: z.object({
    path: posixPathSchema,
    sha256: sha256Schema,
    size_bytes: z.number().int().nonnegative(),
  }),
  models_manifest: z.object({
    path: posixPathSchema,
    sha256: sha256Schema,
  }),
});

// ============================================================================
// Model Manifest (ONNX models for embedding)
// ============================================================================

export const ModelEntrySchema = z.object({
  model_id: z.string().min(1), // e.g., "dino_v2_small"
  path: posixPathSchema,
  sha256: sha256Schema,
  size_bytes: z.number().int().nonnegative(),
  input_size: z.array(z.number().int().positive()).length(2), // [height, width]
  output_dim: z.number().int().positive(), // e.g., 384
});

export const ModelManifestSchema = z.object({
  schema_version: z.string().regex(/^\d+\.\d+\.\d+$/, "Must be semver format"),
  models: z.array(ModelEntrySchema),
  created_at: iso8601Schema,
});

// ============================================================================
// Price Patches (Versioned updates)
// ============================================================================

export const PriceUpdateSchema = z.object({
  card_id: z.string().min(1),
  tcgplayer_market: z.number().nonnegative().optional(),
  tcgplayer_low: z.number().nonnegative().optional(),
  cardmarket_trend: z.number().nonnegative().optional(),
  updated_at: iso8601Schema,
});

export const PricePatchSchema = z.object({
  version: versionSchema,
  base_version: versionSchema,
  created_at: iso8601Schema,
  updates: z.array(PriceUpdateSchema),
});

// ============================================================================
// Game Configuration
// ============================================================================

const OCRRegionSchema = z.object({
  x: z.number().nonnegative(),
  y: z.number().nonnegative(),
  w: z.number().positive(),
  h: z.number().positive(),
});

export const GameConfigSchema = z.object({
  game_id: GameIdSchema,
  display_name: z.string().min(1),
  collector_number_regex: z.string().min(1),
  set_code_regex: z.string().min(1),
  language_defaults: z.array(LanguageSchema),
  ocr_regions: z.record(z.string(), OCRRegionSchema), // Dynamic keys for game-specific fields
  index_params: z.object({
    nlist: z.number().int().positive(),
    m: z.number().int().positive(),
    nbits: z.number().int().positive(),
  }),
  shard_strategy: z.enum(["per_set", "per_rarity", "by_size"]),
});

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Validates an IndexManifest and returns typed result.
 * Throws ZodError with detailed validation errors if invalid.
 */
export function validateIndexManifest(data: unknown) {
  return IndexManifestSchema.parse(data);
}

/**
 * Validates a ModelManifest and returns typed result.
 */
export function validateModelManifest(data: unknown) {
  return ModelManifestSchema.parse(data);
}

/**
 * Validates a PricePatch and returns typed result.
 */
export function validatePricePatch(data: unknown) {
  return PricePatchSchema.parse(data);
}

/**
 * Safe validation that returns success/error result instead of throwing.
 */
export function safeValidateIndexManifest(data: unknown) {
  return IndexManifestSchema.safeParse(data);
}

export function safeValidateModelManifest(data: unknown) {
  return ModelManifestSchema.safeParse(data);
}

export function safeValidatePricePatch(data: unknown) {
  return PricePatchSchema.safeParse(data);
}
