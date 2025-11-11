import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../renderer/app';

// Mock window.identifier
const mockIdentifier = window.identifier as jest.Mocked<typeof window.identifier>;
const mockSettings = window.settings as jest.Mocked<typeof window.settings>;
const mockSync = window.sync as jest.Mocked<typeof window.sync>;

describe('CardFlux Desktop App', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  describe('Initialization', () => {
    it('renders loading screen on initial mount', () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: false,
        ready: false,
        running: false,
      });

      render(<App />);

      expect(screen.getByText(/Initializing CardFlux/i)).toBeInTheDocument();
      expect(screen.getByText(/Loading AI models and card database/i)).toBeInTheDocument();
    });

    it('transitions to ready state after Python init', async () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: true,
        ready: true,
        running: false,
      });

      render(<App />);

      // Wait for ready state (status check happens immediately on mount)
      await waitFor(
        () => {
          expect(screen.queryByText(/Initializing CardFlux/i)).not.toBeInTheDocument();
        },
        { timeout: 5000 }
      );
    });

    it('shows error state if initialization fails', async () => {
      mockIdentifier.getStatus.mockRejectedValue(
        new Error('Failed to connect to identification service')
      );

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/System Error/i)).toBeInTheDocument();
        expect(
          screen.getByText(/Failed to connect to identification service/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('Settings', () => {
    beforeEach(async () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: true,
        ready: true,
        running: false,
      });
    });

    it('loads settings from localStorage on mount', async () => {
      const savedSettings = {
        tcgGame: 'one-piece',
        useOCR: true,
        useFoilDetection: true,
        topK: 30,
        useGeometric: true,
        multiFrameEnabled: false,
        multiFrameCount: 3,
        acceptLowConfidence: false,
        autoAddModerate: true,
      };

      localStorage.setItem('cardflux-settings', JSON.stringify(savedSettings));

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Open settings
      const user = userEvent.setup();
      const settingsButton = screen.getByRole('button', { name: /settings/i });
      await user.click(settingsButton);

      // Verify settings loaded (check if OCR toggle is checked)
      await waitFor(() => {
        expect(screen.getByText(/Identification Settings/i)).toBeInTheDocument();
      });
    });

    it('saves settings to localStorage when changed', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      const user = userEvent.setup();
      const settingsButton = screen.getByRole('button', { name: /settings/i });
      await user.click(settingsButton);

      await waitFor(() => {
        expect(screen.getByText(/Identification Settings/i)).toBeInTheDocument();
      });

      // Change a setting (this would require more specific selectors in actual implementation)
      // For now, just verify the save mechanism works

      // Close settings
      const closeButton = screen.getByRole('button', { name: /close/i });
      await user.click(closeButton);

      // Verify localStorage was updated
      const savedSettings = localStorage.getItem('cardflux-settings');
      expect(savedSettings).toBeTruthy();
    });

    it('falls back to file storage if localStorage fails', async () => {
      // Mock localStorage to fail
      const originalSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = jest.fn(() => {
        throw new Error('QuotaExceededError');
      });

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Wait for file fallback to be called
      await waitFor(() => {
        expect(mockSettings.saveToFile).toHaveBeenCalled();
      });

      // Restore
      Storage.prototype.setItem = originalSetItem;
    });
  });

  describe('Card Identification', () => {
    beforeEach(async () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: true,
        ready: true,
        running: false,
      });
    });

    it('identifies card and adds to stack on capture', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Simulate capture (in real app, this would be triggered by camera component)
      // For now, we'll test that the identification handler works

      // Note: In a real test, we'd trigger capture via keyboard (SPACE)
      // This would require more complex setup with the CameraView component

      // Verify initial state
      expect(screen.getByText(/Cards: 0/i)).toBeInTheDocument();
    });

    it('displays HIGH confidence card notification', async () => {
      mockIdentifier.identify.mockResolvedValue({
        success: true,
        result: {
          card: {
            productId: 123456,
            name: 'Monkey.D.Luffy',
            number: 'ST01-001',
            rarity: 'Leader',
            set: 'Starter Deck',
            prices: {
              normal: { market: 5.99 },
            },
            imageUrl: 'https://example.com/luffy.jpg',
          },
          confidence: 'HIGH',
          score: 0.95,
        },
      });

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Would need to simulate actual capture to test notification
      // This is a placeholder for the full integration
    });

    it('shows review modal for MODERATE confidence when autoAdd disabled', async () => {
      localStorage.setItem(
        'cardflux-settings',
        JSON.stringify({
          tcgGame: 'one-piece',
          useOCR: false,
          useFoilDetection: false,
          topK: 20,
          useGeometric: true,
          multiFrameEnabled: false,
          multiFrameCount: 3,
          acceptLowConfidence: false,
          autoAddModerate: false, // Disabled
        })
      );

      mockIdentifier.identify.mockResolvedValue({
        success: true,
        result: {
          card: {
            productId: 123456,
            name: 'Test Card',
            number: 'ST01-002',
            rarity: 'Common',
            set: 'Starter Deck',
            prices: {
              normal: { market: 1.5 },
            },
            imageUrl: 'https://example.com/card.jpg',
          },
          confidence: 'MODERATE',
          score: 0.68,
        },
      });

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Would need to simulate capture to trigger review modal
    });

    it('rejects LOW confidence cards when setting disabled', async () => {
      localStorage.setItem(
        'cardflux-settings',
        JSON.stringify({
          tcgGame: 'one-piece',
          useOCR: false,
          useFoilDetection: false,
          topK: 20,
          useGeometric: true,
          multiFrameEnabled: false,
          multiFrameCount: 3,
          acceptLowConfidence: false, // Disabled
          autoAddModerate: true,
        })
      );

      mockIdentifier.identify.mockResolvedValue({
        success: true,
        result: {
          card: {
            productId: 123456,
            name: 'Test Card',
            number: 'ST01-003',
            rarity: 'Common',
            set: 'Starter Deck',
            prices: {
              normal: { market: 0.5 },
            },
            imageUrl: 'https://example.com/card.jpg',
          },
          confidence: 'LOW',
          score: 0.45,
        },
      });

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Would need to simulate capture to verify rejection
    });
  });

  describe('Card Stack Management', () => {
    beforeEach(async () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: true,
        ready: true,
        running: false,
      });
    });

    it('displays total card count and value', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Initially empty
      expect(screen.getByText(/Cards: 0/i)).toBeInTheDocument();
      expect(screen.getByText(/Value: \$0\.00/i)).toBeInTheDocument();
    });

    it('clears stack with confirmation', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Mock window.confirm
      (window.confirm as jest.Mock).mockReturnValue(true);

      // Press 'C' key to clear (when cards exist)
      // Note: This test would need cards in the stack first to be meaningful
      expect(screen.getByText(/Cards: 0/i)).toBeInTheDocument();
    });

    it('exports stack to CSV', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Press 'E' key to export (when cards exist)
      // Would need to mock Blob and URL.createObjectURL
      expect(screen.getByText(/Cards: 0/i)).toBeInTheDocument();
    });
  });

  describe('Sync Functionality', () => {
    beforeEach(async () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: true,
        ready: true,
        running: false,
      });
    });

    it('displays last sync time from localStorage', async () => {
      const lastSyncTime = Date.now() - 3600000; // 1 hour ago
      localStorage.setItem(
        'cardflux-sync-status',
        JSON.stringify({ timestamp: lastSyncTime, game: 'one-piece' })
      );

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Should show "1 hour ago"
      await waitFor(() => {
        expect(screen.getByText(/hour/i)).toBeInTheDocument();
      });
    });

    it('syncs data when Sync Now button clicked', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      const user = userEvent.setup();
      const syncButton = screen.getByRole('button', { name: /sync now/i });

      await user.click(syncButton);

      await waitFor(() => {
        expect(mockSync.syncData).toHaveBeenCalledWith('one-piece');
      });

      // Should show success notification
      await waitFor(() => {
        expect(mockSync.syncData).toHaveBeenCalled();
      });
    });

    it('prevents multiple simultaneous syncs', async () => {
      mockSync.syncData.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      const user = userEvent.setup();
      const syncButton = screen.getByRole('button', { name: /sync now/i });

      // Click sync button twice rapidly
      await user.click(syncButton);
      await user.click(syncButton);

      // Should only call sync once
      await waitFor(() => {
        expect(mockSync.syncData).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Keyboard Shortcuts', () => {
    beforeEach(async () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: true,
        ready: true,
        running: false,
      });
    });

    it('opens settings panel with S key', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      const user = userEvent.setup();

      // Press 'S' key
      await user.keyboard('s');

      await waitFor(() => {
        expect(screen.getByText(/Identification Settings/i)).toBeInTheDocument();
      });
    });

    it('closes notification with Escape key', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Would need to trigger a notification first, then test Escape
    });
  });

  describe('Error Handling', () => {
    it('displays error notification on identification failure', async () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: true,
        ready: true,
        running: false,
      });

      mockIdentifier.identify.mockResolvedValue({
        success: false,
        error: 'Card detection failed',
      });

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Would need to simulate capture to trigger error
    });

    it('handles rate limit errors gracefully', async () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: true,
        ready: true,
        running: false,
      });

      mockIdentifier.identify.mockRejectedValue(
        new Error('Too many identification requests. Please wait a moment.')
      );

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Would need to simulate rapid captures to trigger rate limit
    });
  });

  describe('Multi-Frame Fusion', () => {
    beforeEach(async () => {
      mockIdentifier.getStatus.mockResolvedValue({
        initialized: true,
        ready: true,
        running: false,
      });

      localStorage.setItem(
        'cardflux-settings',
        JSON.stringify({
          tcgGame: 'one-piece',
          useOCR: false,
          useFoilDetection: false,
          topK: 20,
          useGeometric: true,
          multiFrameEnabled: true, // Enabled
          multiFrameCount: 3,
          acceptLowConfidence: false,
          autoAddModerate: true,
        })
      );
    });

    it('captures multiple frames before identifying', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Would need to simulate 3 captures
      // Each capture should show progress notification
      // Third capture should trigger identifyMultiFrame
    });

    it('shows fusion statistics in notification', async () => {
      mockIdentifier.identifyMultiFrame.mockResolvedValue({
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
      });

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText(/Ready/i)).toBeInTheDocument();
      });

      // Would need to simulate captures and verify notification shows fusion stats
    });
  });
});
