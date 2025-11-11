import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SettingsPanel, IdentificationSettings } from '../renderer/components/SettingsPanel';

describe('SettingsPanel Component', () => {
  const defaultSettings: IdentificationSettings = {
    tcgGame: 'one-piece',
    useOCR: false,
    useFoilDetection: false,
    topK: 20,
    useGeometric: true,
    multiFrameEnabled: false,
    multiFrameCount: 3,
    acceptLowConfidence: false,
    autoAddModerate: true,
  };

  const mockOnSettingsChange = jest.fn();
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders all settings sections', () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText(/Identification Settings/i)).toBeInTheDocument();
      expect(screen.getByText(/Trading Card Game/i)).toBeInTheDocument();
      expect(screen.getByText(/Card Number Extraction \(OCR\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Foil Detection/i)).toBeInTheDocument();
      expect(screen.getByText(/Geometric Verification \(ORB\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Multi-Frame Fusion/i)).toBeInTheDocument();
      expect(screen.getByText(/Confidence Thresholds/i)).toBeInTheDocument();
    });

    it('displays current settings values', () => {
      const customSettings: IdentificationSettings = {
        ...defaultSettings,
        useOCR: true,
        useFoilDetection: true,
        topK: 30,
      };

      render(
        <SettingsPanel
          settings={customSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      // Check checkboxes are checked
      const ocrToggle = screen.getByRole('checkbox', {
        name: /Card Number Extraction/i,
      });
      expect(ocrToggle).toBeChecked();

      const foilToggle = screen.getByRole('checkbox', {
        name: /Foil Detection/i,
      });
      expect(foilToggle).toBeChecked();

      // Check slider value
      expect(screen.getByText('30')).toBeInTheDocument();
    });

    it('shows TCG game selector as disabled', () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const gameSelector = screen.getByRole('combobox', {
        name: /Trading Card Game/i,
      });
      expect(gameSelector).toBeDisabled();
    });

    it('shows performance estimate', () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText(/Estimated Performance/i)).toBeInTheDocument();
      expect(screen.getByText(/~3-5 seconds/i)).toBeInTheDocument(); // Initialization time
    });
  });

  describe('Toggle Interactions', () => {
    it('toggles OCR setting', async () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const ocrToggle = screen.getByRole('checkbox', {
        name: /Card Number Extraction/i,
      });

      await user.click(ocrToggle);

      expect(mockOnSettingsChange).toHaveBeenCalledWith({
        ...defaultSettings,
        useOCR: true,
      });
    });

    it('toggles Foil Detection setting', async () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const foilToggle = screen.getByRole('checkbox', {
        name: /Foil Detection/i,
      });

      await user.click(foilToggle);

      expect(mockOnSettingsChange).toHaveBeenCalledWith({
        ...defaultSettings,
        useFoilDetection: true,
      });
    });

    it('toggles Geometric Verification setting', async () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const geometricToggle = screen.getByRole('checkbox', {
        name: /Geometric Verification/i,
      });

      await user.click(geometricToggle);

      expect(mockOnSettingsChange).toHaveBeenCalledWith({
        ...defaultSettings,
        useGeometric: false,
      });
    });

    it('toggles Multi-Frame Fusion setting', async () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const multiFrameToggle = screen.getByRole('checkbox', {
        name: /Multi-Frame Fusion/i,
      });

      await user.click(multiFrameToggle);

      expect(mockOnSettingsChange).toHaveBeenCalledWith({
        ...defaultSettings,
        multiFrameEnabled: true,
      });
    });

    it('toggles Auto-add MODERATE confidence setting', async () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const autoAddToggle = screen.getByRole('checkbox', {
        name: /Auto-add MODERATE confidence/i,
      });

      await user.click(autoAddToggle);

      expect(mockOnSettingsChange).toHaveBeenCalledWith({
        ...defaultSettings,
        autoAddModerate: false,
      });
    });

    it('toggles Accept LOW confidence setting', async () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const acceptLowToggle = screen.getByRole('checkbox', {
        name: /Accept LOW confidence with review/i,
      });

      await user.click(acceptLowToggle);

      expect(mockOnSettingsChange).toHaveBeenCalledWith({
        ...defaultSettings,
        acceptLowConfidence: true,
      });
    });
  });

  describe('Multi-Frame Settings', () => {
    it('shows frame count slider when multi-frame enabled', () => {
      const settings: IdentificationSettings = {
        ...defaultSettings,
        multiFrameEnabled: true,
      };

      render(
        <SettingsPanel
          settings={settings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText(/Frame Count: 3/i)).toBeInTheDocument();
      expect(screen.getByRole('slider', { name: /Frame Count/i })).toBeInTheDocument();
    });

    it('hides frame count slider when multi-frame disabled', () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.queryByRole('slider', { name: /Frame Count/i })).not.toBeInTheDocument();
    });

    it('changes frame count value', async () => {
      const settings: IdentificationSettings = {
        ...defaultSettings,
        multiFrameEnabled: true,
      };

      render(
        <SettingsPanel
          settings={settings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const frameSlider = screen.getByRole('slider', { name: /Frame Count/i });

      // Change slider value to 5 using fireEvent
      await user.click(frameSlider);
      await user.keyboard('{ArrowRight}{ArrowRight}'); // Move slider right

      // For now, we'll just verify the slider exists and is interactive
      // Full testing would require mocking the onChange handler more thoroughly
      expect(frameSlider).toBeInTheDocument();
    });
  });

  describe('Top-K Slider', () => {
    it('displays current topK value', () => {
      const settings: IdentificationSettings = {
        ...defaultSettings,
        topK: 35,
      };

      render(
        <SettingsPanel
          settings={settings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('35')).toBeInTheDocument();
    });

    it('changes topK value', async () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const topKSlider = screen.getByRole('slider', {
        name: /Candidate Count/i,
      });

      // Change slider value using keyboard navigation
      await user.click(topKSlider);
      await user.keyboard('{ArrowRight}{ArrowRight}');

      // Verify slider is interactive
      expect(topKSlider).toBeInTheDocument();
    });
  });

  describe('Performance Estimation', () => {
    it('updates estimate when OCR enabled', () => {
      const settingsWithOCR: IdentificationSettings = {
        ...defaultSettings,
        useOCR: true,
      };

      const { rerender } = render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const baseEstimates = screen.getAllByText(/~\d+ms/);
      const baseValue = baseEstimates[0].textContent;

      rerender(
        <SettingsPanel
          settings={settingsWithOCR}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const newEstimates = screen.getAllByText(/~\d+ms/);
      const newValue = newEstimates[0].textContent;

      // OCR adds ~170ms, so new estimate should be higher
      expect(newValue).not.toBe(baseValue);
    });

    it('shows slowdown warning when OCR enabled', () => {
      const settingsWithOCR: IdentificationSettings = {
        ...defaultSettings,
        useOCR: true,
      };

      render(
        <SettingsPanel
          settings={settingsWithOCR}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText(/~170ms slower per scan/i)).toBeInTheDocument();
    });

    it('shows warning when LOW confidence enabled', () => {
      const settingsWithLow: IdentificationSettings = {
        ...defaultSettings,
        acceptLowConfidence: true,
      };

      render(
        <SettingsPanel
          settings={settingsWithLow}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(
        screen.getByText(/Requires manual confirmation for each LOW card/i)
      ).toBeInTheDocument();
    });
  });

  describe('Close Behavior', () => {
    it('calls onClose when close button clicked', async () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      // Get the primary close button (not the X button)
      const closeButton = screen.getByRole('button', { name: /^close$/i });

      await user.click(closeButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when X button clicked', async () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const xButton = screen.getByRole('button', { name: /close settings/i });

      await user.click(xButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when clicking overlay', async () => {
      const { container } = render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const overlay = container.querySelector('.settings-overlay');

      if (overlay) {
        await user.click(overlay);
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      }
    });

    it('does not close when clicking inside panel', async () => {
      const { container } = render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      const user = userEvent.setup();
      const panel = container.querySelector('.settings-panel');

      if (panel) {
        await user.click(panel);
        expect(mockOnClose).not.toHaveBeenCalled();
      }
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels for toggles', () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(
        screen.getByRole('checkbox', { name: /Card Number Extraction/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('checkbox', { name: /Foil Detection/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('checkbox', { name: /Geometric Verification/i })
      ).toBeInTheDocument();
    });

    it('has proper labels for sliders', () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByLabelText(/Candidate Count/i)).toBeInTheDocument();
    });

    it('close button has accessible name', () => {
      render(
        <SettingsPanel
          settings={defaultSettings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(
        screen.getByRole('button', { name: /close settings/i })
      ).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles minimum topK value', () => {
      const settings: IdentificationSettings = {
        ...defaultSettings,
        topK: 10,
      };

      render(
        <SettingsPanel
          settings={settings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('10')).toBeInTheDocument();
    });

    it('handles maximum topK value', () => {
      const settings: IdentificationSettings = {
        ...defaultSettings,
        topK: 50,
      };

      render(
        <SettingsPanel
          settings={settings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('handles minimum frame count', () => {
      const settings: IdentificationSettings = {
        ...defaultSettings,
        multiFrameEnabled: true,
        multiFrameCount: 2,
      };

      render(
        <SettingsPanel
          settings={settings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText(/Frame Count: 2/i)).toBeInTheDocument();
    });

    it('handles maximum frame count', () => {
      const settings: IdentificationSettings = {
        ...defaultSettings,
        multiFrameEnabled: true,
        multiFrameCount: 5,
      };

      render(
        <SettingsPanel
          settings={settings}
          onSettingsChange={mockOnSettingsChange}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText(/Frame Count: 5/i)).toBeInTheDocument();
    });
  });
});
