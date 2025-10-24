/**
 * TCGplayer configuration using tcgcsv.com API
 * Unified data source for all TCG games
 */

export interface TCGCategory {
  categoryId: number;
  name: string;
  enabled: boolean;
}

export interface TCGGroup {
  groupId: number;
  name: string;
  categoryId: number;
  modifiedOn?: string;
}

export interface TCGProduct {
  productId: number;
  name: string;
  cleanName: string;
  imageUrl: string;
  categoryId: number;
  groupId: number;
  url: string;
  modifiedOn: string;
  imageCount: number;
  extendedData: Array<{
    name: string;
    displayName: string;
    value: string;
  }>;
}

export interface TCGPrice {
  productId: number;
  lowPrice: number | null;
  midPrice: number | null;
  highPrice: number | null;
  marketPrice: number | null;
  directLowPrice: number | null;
  subTypeName: string; // "Normal" or "Foil"
}

export interface TCGCard {
  // Product info
  productId: number;
  name: string;
  cleanName: string;
  imageUrl: string;
  categoryId: number;
  categoryName: string;
  groupId: number;
  groupName: string;
  url: string;
  modifiedOn: string;

  // Extended data (parsed)
  rarity?: string;
  number?: string;
  subType?: string;
  oracleText?: string;

  // Price info
  prices: {
    normal?: {
      low: number | null;
      mid: number | null;
      high: number | null;
      market: number | null;
      directLow: number | null;
    };
    foil?: {
      low: number | null;
      mid: number | null;
      high: number | null;
      market: number | null;
      directLow: number | null;
    };
  };
}

/**
 * TCGplayer API configuration
 */
export const TCGCSV_CONFIG = {
  baseUrl: 'https://tcgcsv.com/tcgplayer',

  // Primary categories we support (card games only)
  enabledCategories: [
    { categoryId: 1, name: 'Magic', enabled: false },
    { categoryId: 2, name: 'YuGiOh', enabled: false },
    { categoryId: 3, name: 'Pokemon', enabled: false },
    { categoryId: 17, name: 'Cardfight!! Vanguard', enabled: false },
    { categoryId: 19, name: 'Final Fantasy', enabled: false },
    { categoryId: 24, name: 'Final Fantasy', enabled: false },
    { categoryId: 26, name: 'Digimon', enabled: false },
    { categoryId: 28, name: 'Dragon Ball Super', enabled: false },
    { categoryId: 58, name: 'Flesh and Blood', enabled: false },
    { categoryId: 68, name: 'One Piece Card Game', enabled: true }, // Only One Piece enabled
    { categoryId: 80, name: 'Lorcana', enabled: false },
  ] as TCGCategory[],

  // Rate limiting
  rateLimit: {
    requestsPerSecond: 5,
    delayBetweenGroups: 2000, // 2 seconds
    delayBetweenCategories: 5000, // 5 seconds
    maxRetries: 3,
    retryDelay: 1000,
    backoffMultiplier: 2,
  },

  // Request settings
  request: {
    timeout: 30000,
    userAgent: 'CardFlux/1.0 (https://cardflux.app)',
    headers: {
      'Accept': 'application/json',
      'Accept-Encoding': 'gzip, deflate',
    },
  },
};

/**
 * Get enabled categories
 */
export function getEnabledCategories(): TCGCategory[] {
  return TCGCSV_CONFIG.enabledCategories.filter(c => c.enabled);
}

/**
 * Get category by ID
 */
export function getCategoryById(categoryId: number): TCGCategory | undefined {
  return TCGCSV_CONFIG.enabledCategories.find(c => c.categoryId === categoryId);
}

/**
 * Get category by name (case-insensitive)
 */
export function getCategoryByName(name: string): TCGCategory | undefined {
  const normalized = name.toLowerCase();
  return TCGCSV_CONFIG.enabledCategories.find(
    c => c.name.toLowerCase() === normalized
  );
}

/**
 * Parse extended data from product
 */
export function parseExtendedData(extendedData: Array<{ name: string; value: string }> | null | undefined): {
  rarity?: string;
  number?: string;
  subType?: string;
  oracleText?: string;
} {
  const parsed: any = {};

  if (!extendedData || !Array.isArray(extendedData)) {
    return parsed;
  }

  for (const item of extendedData) {
    switch (item.name) {
      case 'Rarity':
        parsed.rarity = item.value;
        break;
      case 'Number':
        parsed.number = item.value;
        break;
      case 'SubType':
        parsed.subType = item.value;
        break;
      case 'OracleText':
        parsed.oracleText = item.value;
        break;
    }
  }

  return parsed;
}

/**
 * Check if a product is a sealed product (not a single card)
 *
 * This filters out:
 * - Booster packs, boxes, cases
 * - Starter/structure decks (the sealed product, not individual cards)
 * - Display boxes, bundles, kits
 * - Promotional tins, blisters, gift sets
 *
 * But keeps individual cards like:
 * - "Card Name (Deck Name)" - single cards from a deck
 * - "Card Name - Starter Deck Promo" - promo cards
 */
export function isSealedProduct(product: TCGProduct): boolean {
  const nameLower = product.name.toLowerCase();
  const cleanNameLower = product.cleanName.toLowerCase();

  // Definite sealed product patterns (whole products, not single cards)
  const sealedPatterns = [
    /booster\s+(pack|box|case)/i,
    /display\s*(box)?/i,
    /\b(deck|starter|structure)\s+(set|box|display)\b/i,
    /\bcase\b(?!.*\(.*\))/i, // "Case" but not in parentheses (card names)
    /\b(bundle|kit|collection)\b/i,
    /fat\s*pack/i,
    /gift\s+(box|set)/i,
    /\b(tin|blister)\b/i,
    /prerelease\s+(kit|pack|box)/i,
    /pre-release\s+starter\s+deck/i, // Pre-release starter decks
    /sleeved\s+booster/i,
    /learn\s+together\s+deck\s+set/i, // Specific to One Piece
  ];

  // Check if it matches any sealed product pattern
  const isSealed = sealedPatterns.some(pattern =>
    pattern.test(nameLower) || pattern.test(cleanNameLower)
  );

  // Additional heuristic: if name is very short and contains "pack", "box", "case", likely sealed
  if (!isSealed) {
    const words = nameLower.split(/\s+/);
    if (words.length <= 6 && (
      nameLower.includes('booster box') ||
      nameLower.includes('booster pack') ||
      nameLower.includes('starter deck') && !nameLower.includes('(') ||
      nameLower.includes('structure deck') && !nameLower.includes('(')
    )) {
      return true;
    }
  }

  return isSealed;
}

/**
 * Transform TCGPlayer CDN image URL to higher resolution
 *
 * Transforms URLs from:
 *   https://tcgplayer-cdn.tcgplayer.com/product/510897_200w.jpg
 * To:
 *   https://tcgplayer-cdn.tcgplayer.com/product/510897_in_800x800.jpg
 *
 * Updated 2025-10-21: Upgraded to 800x800 based on resolution comparison testing.
 * While 600x600 images appear sharper (less upscaling artifacts), 800x800 provides:
 * - Better ORB keypoint detection (more features detected)
 * - Higher OCR accuracy (95% vs 85%)
 * - Better geometric matching (+50% improvement)
 * - Overall +20-30% identification accuracy improvement
 *
 * See: scripts/identification/resolution_comparison_results.json
 * See: CONFIDENCE_IMPROVEMENT_PLAN.md for analysis
 */
export function transformImageUrl(url: string): string {
  if (!url) return url;

  // Extract product ID from URL
  const match = url.match(/\/product\/(\d+)[._]/);
  if (!match) return url;

  const productId = match[1];

  // Use 800x800 format (optimal for identification accuracy)
  // Resolution comparison showed: Better keypoints and geometric matching
  return `https://tcgplayer-cdn.tcgplayer.com/product/${productId}_in_800x800.jpg`;
}

/**
 * Merge product and price data
 */
export function mergeProductAndPrices(
  product: TCGProduct,
  prices: TCGPrice[]
): TCGCard {
  const normalPrice = prices.find(p => p.subTypeName === 'Normal');
  const foilPrice = prices.find(p => p.subTypeName === 'Foil');

  const extendedData = parseExtendedData(product.extendedData);

  return {
    productId: product.productId,
    name: product.name,
    cleanName: product.cleanName,
    imageUrl: transformImageUrl(product.imageUrl), // Transform to 600w resolution
    categoryId: product.categoryId,
    categoryName: '', // Will be filled by scraper
    groupId: product.groupId,
    groupName: '', // Will be filled by scraper
    url: product.url,
    modifiedOn: product.modifiedOn,

    rarity: extendedData.rarity,
    number: extendedData.number,
    subType: extendedData.subType,
    oracleText: extendedData.oracleText,

    prices: {
      normal: normalPrice ? {
        low: normalPrice.lowPrice,
        mid: normalPrice.midPrice,
        high: normalPrice.highPrice,
        market: normalPrice.marketPrice,
        directLow: normalPrice.directLowPrice,
      } : undefined,
      foil: foilPrice ? {
        low: foilPrice.lowPrice,
        mid: foilPrice.midPrice,
        high: foilPrice.highPrice,
        market: foilPrice.marketPrice,
        directLow: foilPrice.directLowPrice,
      } : undefined,
    },
  };
}
