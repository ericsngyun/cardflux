import '@testing-library/jest-dom';

// Mock Electron APIs
global.window = Object.create(window);

const mockElectronAPI = {
  identifier: {
    initialize: jest.fn().mockResolvedValue({ success: true }),
    getStatus: jest.fn().mockResolvedValue({
      initialized: true,
      ready: true,
      running: false,
    }),
    identify: jest.fn().mockResolvedValue({
      success: true,
      result: {
        card: {
          productId: 123456,
          name: 'Test Card',
          number: 'ST01-001',
          rarity: 'Common',
          set: 'Starter Deck',
          prices: {
            normal: { market: 1.5 },
          },
          imageUrl: 'https://example.com/card.jpg',
        },
        confidence: 'HIGH',
        score: 0.95,
      },
    }),
    identifyMultiFrame: jest.fn().mockResolvedValue({
      success: true,
      result: {
        card: {
          productId: 123456,
          name: 'Test Card',
          number: 'ST01-001',
          rarity: 'Common',
          set: 'Starter Deck',
          prices: {
            normal: { market: 1.5 },
          },
          imageUrl: 'https://example.com/card.jpg',
        },
        confidence: 'HIGH',
        score: 0.95,
        multiFrame: {
          fusionVotes: 2.8,
          confidenceBoost: true,
        },
      },
    }),
  },
  settings: {
    saveToFile: jest.fn().mockResolvedValue({ success: true }),
    loadFromFile: jest.fn().mockResolvedValue({
      success: true,
      settings: {
        tcgGame: 'one-piece',
        useOCR: false,
        useFoilDetection: false,
        topK: 20,
        useGeometric: true,
      },
    }),
  },
  sync: {
    syncData: jest.fn().mockResolvedValue({
      success: true,
      updatedCards: 10,
      newCards: 2,
    }),
  },
};

Object.defineProperty(window, 'identifier', {
  writable: true,
  value: mockElectronAPI.identifier,
});

Object.defineProperty(window, 'settings', {
  writable: true,
  value: mockElectronAPI.settings,
});

Object.defineProperty(window, 'sync', {
  writable: true,
  value: mockElectronAPI.sync,
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock window.confirm
Object.defineProperty(window, 'confirm', {
  writable: true,
  value: jest.fn(() => true),
});

// Mock navigator.mediaDevices for camera tests
Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: jest.fn().mockResolvedValue({
      getVideoTracks: () => [{
        getCapabilities: () => ({}),
        applyConstraints: jest.fn().mockResolvedValue(undefined),
        stop: jest.fn(),
      }],
      getTracks: () => [{
        stop: jest.fn(),
      }],
    }),
  },
});

// Suppress console errors in tests (can be removed for debugging)
global.console = {
  ...console,
  error: jest.fn(),
  warn: jest.fn(),
};
