/**
 * Zod schemas for runtime validation of manifests.
 * These schemas enforce the contract between pipeline and desktop app.
 */

import { z } from "zod";

export const IndexShardEntrySchema = z.object({
  game_id: z.string(),
  set_code: z.string(),
  index_path: z.string(),
  ids_path: z.string(),
  meta_path: z.string(),
  index_sha256: z.string().length(64),
  ids_sha256: z.string().length(64),
  meta_sha256: z.string().length(64),
  vector_count: z.number().int().positive(),
});

export const IndexManifestSchema = z.object({
  schema_version: z.string(),
  version: z.string(),
  created_at: z.string().datetime(),
  games: z.array(z.string()),
  shards: z.array(IndexShardEntrySchema),
  metadata_snapshot: z.object({
    path: z.string(),
    sha256: z.string().length(64),
    size_bytes: z.number().int().nonnegative(),
  }),
  models_manifest: z.object({
    path: z.string(),
    sha256: z.string().length(64),
  }),
});

export const ModelEntrySchema = z.object({
  model_id: z.string(),
  path: z.string(),
  sha256: z.string().length(64),
  size_bytes: z.number().int().nonnegative(),
  input_size: z.array(z.number().int().positive()),
  output_dim: z.number().int().positive(),
});

export const ModelManifestSchema = z.object({
  schema_version: z.string(),
  models: z.array(ModelEntrySchema),
  created_at: z.string().datetime(),
});

export const PriceUpdateSchema = z.object({
  card_id: z.string(),
  tcgplayer_market: z.number().optional(),
  tcgplayer_low: z.number().optional(),
  cardmarket_trend: z.number().optional(),
  updated_at: z.string().datetime(),
});

export const PricePatchSchema = z.object({
  version: z.string(),
  base_version: z.string(),
  created_at: z.string().datetime(),
  updates: z.array(PriceUpdateSchema),
});

export const ImageMetaSchema = z.object({
  card_id: z.string(),
  game_id: z.string(),
  set_code: z.string(),
  collector_number: z.string(),
  name: z.string(),
  language: z.string(),
  canonical_sha256: z.string().length(64),
  thumb_sha256: z.string().length(64),
  created_at: z.string().datetime(),
  source_url: z.string().url().optional(),
});

export const ShardMetaSchema = z.object({
  game_id: z.string(),
  set_code: z.string(),
  vector_count: z.number().int().positive(),
  dimension: z.number().int().positive(),
  index_type: z.string(),
  created_at: z.string().datetime(),
  version: z.string(),
});
