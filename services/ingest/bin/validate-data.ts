#!/usr/bin/env node
/**
 * Data validation and quality checks for TCGplayer scraped data
 */

import * as fs from 'fs';
import * as path from 'path';
import { getEnabledCategories } from '@cardflux/config/tcgplayer-config';
import { parseJsonLines, logger, formatBytes } from '@cardflux/shared';
import type { TCGCard } from '@cardflux/config/tcgplayer-config';

const CURATED_DIR = path.resolve(__dirname, '../../../data/curated');

interface ValidationResult {
  category: string;
  totalCards: number;
  validCards: number;
  invalidCards: number;
  issues: Array<{
    type: string;
    count: number;
    examples: string[];
  }>;
}

interface ValidationIssue {
  cardName: string;
  productId: number;
  issue: string;
}

/**
 * Validate a single card
 */
function validateCard(card: TCGCard): string[] {
  const issues: string[] = [];

  // Required fields
  if (!card.productId) issues.push('Missing productId');
  if (!card.name) issues.push('Missing name');
  if (!card.categoryId) issues.push('Missing categoryId');
  if (!card.categoryName) issues.push('Missing categoryName');
  if (!card.groupId) issues.push('Missing groupId');

  // Image validation
  if (card.imageUrl) {
    if (!card.imageUrl.startsWith('http')) {
      issues.push('Invalid imageUrl (not HTTP/HTTPS)');
    }
    if (!card.imageUrl.includes('tcgplayer')) {
      issues.push('ImageUrl not from TCGplayer CDN');
    }
  } else {
    issues.push('Missing imageUrl');
  }

  // Price validation
  if (!card.prices.normal && !card.prices.foil) {
    issues.push('No price data (neither normal nor foil)');
  }

  if (card.prices.normal) {
    if (card.prices.normal.market === null || card.prices.normal.market === undefined) {
      issues.push('Normal market price is null');
    }
    if (card.prices.normal.market && card.prices.normal.market < 0) {
      issues.push('Negative normal market price');
    }
    if (card.prices.normal.market && card.prices.normal.market > 100000) {
      issues.push('Suspiciously high normal market price');
    }
  }

  if (card.prices.foil) {
    if (card.prices.foil.market && card.prices.foil.market < 0) {
      issues.push('Negative foil market price');
    }
  }

  // Name validation
  if (card.name.length > 200) {
    issues.push('Card name too long (>200 chars)');
  }
  if (card.name.length === 0) {
    issues.push('Empty card name');
  }

  // Rarity validation (if present)
  if (card.rarity) {
    const validRarities = ['C', 'U', 'R', 'M', 'L', 'S', 'Common', 'Uncommon', 'Rare', 'Mythic', 'Special'];
    if (!validRarities.some(r => card.rarity?.includes(r))) {
      issues.push(`Unknown rarity: ${card.rarity}`);
    }
  }

  return issues;
}

/**
 * Validate category data
 */
function validateCategory(categoryName: string): ValidationResult {
  const curatedPath = path.join(
    CURATED_DIR,
    `${categoryName.toLowerCase().replace(/\s+/g, '-')}.jsonl`
  );

  if (!fs.existsSync(curatedPath)) {
    logger.error(`Curated file not found: ${curatedPath}`);
    return {
      category: categoryName,
      totalCards: 0,
      validCards: 0,
      invalidCards: 0,
      issues: [],
    };
  }

  const content = fs.readFileSync(curatedPath, 'utf-8');
  const { data: cards, errors: parseErrors } = parseJsonLines<TCGCard>(content);

  logger.info(`Validating ${categoryName}...`, {
    totalCards: cards.length,
    parseErrors,
  });

  const issueMap = new Map<string, ValidationIssue[]>();
  let validCards = 0;
  let invalidCards = 0;

  for (const card of cards) {
    const cardIssues = validateCard(card);

    if (cardIssues.length === 0) {
      validCards++;
    } else {
      invalidCards++;

      for (const issue of cardIssues) {
        if (!issueMap.has(issue)) {
          issueMap.set(issue, []);
        }

        issueMap.get(issue)!.push({
          cardName: card.name,
          productId: card.productId,
          issue,
        });
      }
    }
  }

  // Aggregate issues
  const issues = Array.from(issueMap.entries()).map(([type, occurrences]) => ({
    type,
    count: occurrences.length,
    examples: occurrences.slice(0, 5).map(o => `${o.cardName} (ID: ${o.productId})`),
  }));

  return {
    category: categoryName,
    totalCards: cards.length,
    validCards,
    invalidCards,
    issues: issues.sort((a, b) => b.count - a.count), // Sort by count
  };
}

/**
 * Check for duplicate cards
 */
function checkDuplicates(categoryName: string): { duplicates: number; examples: string[] } {
  const curatedPath = path.join(
    CURATED_DIR,
    `${categoryName.toLowerCase().replace(/\s+/g, '-')}.jsonl`
  );

  if (!fs.existsSync(curatedPath)) {
    return { duplicates: 0, examples: [] };
  }

  const content = fs.readFileSync(curatedPath, 'utf-8');
  const { data: cards } = parseJsonLines<TCGCard>(content);

  const productIds = new Set<number>();
  const duplicates: string[] = [];

  for (const card of cards) {
    if (productIds.has(card.productId)) {
      duplicates.push(`${card.name} (ID: ${card.productId})`);
    }
    productIds.add(card.productId);
  }

  return {
    duplicates: duplicates.length,
    examples: duplicates.slice(0, 10),
  };
}

/**
 * Check file integrity
 */
function checkFileIntegrity(categoryName: string): {
  exists: boolean;
  readable: boolean;
  size: number;
  lineCount: number;
  emptyLines: number;
  malformedLines: number;
} {
  const curatedPath = path.join(
    CURATED_DIR,
    `${categoryName.toLowerCase().replace(/\s+/g, '-')}.jsonl`
  );

  if (!fs.existsSync(curatedPath)) {
    return {
      exists: false,
      readable: false,
      size: 0,
      lineCount: 0,
      emptyLines: 0,
      malformedLines: 0,
    };
  }

  try {
    const content = fs.readFileSync(curatedPath, 'utf-8');
    const lines = content.split('\n');

    let emptyLines = 0;
    let malformedLines = 0;

    for (const line of lines) {
      if (!line.trim()) {
        emptyLines++;
        continue;
      }

      try {
        JSON.parse(line);
      } catch {
        malformedLines++;
      }
    }

    return {
      exists: true,
      readable: true,
      size: fs.statSync(curatedPath).size,
      lineCount: lines.length,
      emptyLines,
      malformedLines,
    };
  } catch (error) {
    return {
      exists: true,
      readable: false,
      size: 0,
      lineCount: 0,
      emptyLines: 0,
      malformedLines: 0,
    };
  }
}

/**
 * Main validation
 */
async function main() {
  console.log('\n' + '='.repeat(60));
  console.log('DATA VALIDATION REPORT');
  console.log('='.repeat(60));

  const categories = getEnabledCategories();
  const allResults: ValidationResult[] = [];

  for (const category of categories) {
    console.log(`\n📊 ${category.name.toUpperCase()}`);
    console.log('-'.repeat(60));

    // File integrity
    const integrity = checkFileIntegrity(category.name);
    if (!integrity.exists) {
      console.log('❌ File not found');
      continue;
    }
    if (!integrity.readable) {
      console.log('❌ File not readable');
      continue;
    }

    console.log(`✓ File size: ${formatBytes(integrity.size)}`);
    console.log(`✓ Lines: ${integrity.lineCount.toLocaleString()}`);

    if (integrity.emptyLines > 0) {
      console.log(`⚠️  Empty lines: ${integrity.emptyLines}`);
    }
    if (integrity.malformedLines > 0) {
      console.log(`⚠️  Malformed lines: ${integrity.malformedLines}`);
    }

    // Duplicates check
    const duplicateCheck = checkDuplicates(category.name);
    if (duplicateCheck.duplicates > 0) {
      console.log(`⚠️  Duplicate cards: ${duplicateCheck.duplicates}`);
      console.log(`   Examples: ${duplicateCheck.examples.join(', ')}`);
    }

    // Validation
    const result = validateCategory(category.name);
    allResults.push(result);

    console.log(`\n✓ Total cards: ${result.totalCards.toLocaleString()}`);
    console.log(`✓ Valid cards: ${result.validCards.toLocaleString()} (${Math.round((result.validCards / result.totalCards) * 100)}%)`);

    if (result.invalidCards > 0) {
      console.log(`⚠️  Invalid cards: ${result.invalidCards.toLocaleString()}`);
      console.log('\nTop Issues:');

      for (const issue of result.issues.slice(0, 5)) {
        console.log(`  • ${issue.type}: ${issue.count} occurrences`);
        console.log(`    Examples: ${issue.examples.slice(0, 3).join(', ')}`);
      }
    }
  }

  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('SUMMARY');
  console.log('='.repeat(60));

  const totals = allResults.reduce(
    (acc, r) => ({
      totalCards: acc.totalCards + r.totalCards,
      validCards: acc.validCards + r.validCards,
      invalidCards: acc.invalidCards + r.invalidCards,
    }),
    { totalCards: 0, validCards: 0, invalidCards: 0 }
  );

  console.log(`Total cards: ${totals.totalCards.toLocaleString()}`);
  console.log(`Valid cards: ${totals.validCards.toLocaleString()} (${Math.round((totals.validCards / totals.totalCards) * 100)}%)`);
  console.log(`Invalid cards: ${totals.invalidCards.toLocaleString()}`);

  // Exit with error if too many invalid cards
  const invalidPercentage = (totals.invalidCards / totals.totalCards) * 100;
  if (invalidPercentage > 5) {
    console.log(`\n❌ Validation failed: ${invalidPercentage.toFixed(1)}% invalid cards (threshold: 5%)`);
    process.exit(1);
  } else {
    console.log(`\n✓ Validation passed`);
  }
}

main().catch(error => {
  logger.error('Validation failed', {}, error);
  process.exit(1);
});
