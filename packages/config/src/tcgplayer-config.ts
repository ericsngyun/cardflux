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
    { categoryId: 1, name: 'Magic', enabled: true },
    { categoryId: 2, name: 'YuGiOh', enabled: true },
    { categoryId: 3, name: 'Pokemon', enabled: true },
    { categoryId: 17, name: 'Cardfight!! Vanguard', enabled: false },
    { categoryId: 19, name: 'Final Fantasy', enabled: false },
    { categoryId: 24, name: 'One Piece', enabled: true },
    { categoryId: 26, name: 'Digimon', enabled: true },
    { categoryId: 28, name: 'Dragon Ball Super', enabled: false },
    { categoryId: 58, name: 'Flesh and Blood', enabled: false },
    { categoryId: 68, name: 'Lorcana', enabled: false },
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
    imageUrl: product.imageUrl,
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
