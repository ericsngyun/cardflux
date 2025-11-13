/** @type {import('jest').Config} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/src'],
  testMatch: [
    '**/__tests__/**/*.test.ts',
    '**/__tests__/**/*.test.tsx',
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
  ],
  moduleNameMapper: {
    // Handle CSS imports (with CSS modules)
    '\\.css$': 'identity-obj-proxy',

    // Handle image imports
    '\\.(jpg|jpeg|png|gif|svg)$': '<rootDir>/__mocks__/fileMock.js',

    // Handle workspace packages
    '^@cardflux/config$': '<rootDir>/../../packages/config/src',
    '^@cardflux/shared$': '<rootDir>/../../packages/shared/src',
  },
  setupFilesAfterEnv: ['<rootDir>/src/__tests__/setup.ts'],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/__tests__/**',
    '!src/preload/**', // Electron preload scripts are hard to test
  ],
  coverageThreshold: {
    global: {
      branches: 60,
      functions: 60,
      lines: 70,
      statements: 70,
    },
  },
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  transform: {
    '^.+\\.tsx?$': ['ts-jest', {
      tsconfig: {
        jsx: 'react',
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
      },
    }],
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  testTimeout: 15000, // Increased for async operations
};
