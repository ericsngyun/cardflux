#!/usr/bin/env node
/**
 * Test the sealed product filtering logic
 */

import { isSealedProduct } from '@cardflux/config/tcgplayer-config';

const testCases = [
  // Should be filtered (sealed products)
  { name: 'Carrying On His Will Booster Pack', expected: true },
  { name: 'Carrying On His Will Booster Box', expected: true },
  { name: 'Carrying On His Will Booster Box Case', expected: true },
  { name: 'Carrying On His Will Sleeved Booster Pack', expected: true },
  { name: 'Learn Together Deck Set', expected: true },
  { name: 'Learn Together Deck Set Display', expected: true },
  { name: 'Starter Deck 1: Straw Hat Crew', expected: true },
  { name: 'Super Pre-Release Starter Deck 1: Straw Hat Crew', expected: true },
  { name: 'Gift Box', expected: true },
  { name: 'Premium Collection Box', expected: true },

  // Should NOT be filtered (individual cards)
  { name: 'Roronoa Zoro - OP12-020 (Zoro Deck)', expected: false },
  { name: 'Kouzuki Hiyori (Zoro Deck)', expected: false },
  { name: 'Monkey.D.Luffy', expected: false },
  { name: 'Brook (Championship 2024 Finalist Card Set Vol. 2)', expected: false },
  { name: 'Karoo', expected: false },
  { name: 'Sanji (Parallel)', expected: false },
];

console.log('\n=== Testing Sealed Product Filter ===\n');

let passed = 0;
let failed = 0;

for (const test of testCases) {
  const result = isSealedProduct({ name: test.name, cleanName: test.name } as any);
  const status = result === test.expected ? '✓' : '✗';

  if (result === test.expected) {
    passed++;
    console.log(`${status} "${test.name}" -> ${result ? 'SEALED' : 'CARD'}`);
  } else {
    failed++;
    console.log(`${status} "${test.name}" -> ${result ? 'SEALED' : 'CARD'} (expected: ${test.expected ? 'SEALED' : 'CARD'})`);
  }
}

console.log(`\n=== Results ===`);
console.log(`Passed: ${passed}/${testCases.length}`);
console.log(`Failed: ${failed}/${testCases.length}`);

if (failed > 0) {
  process.exit(1);
}
