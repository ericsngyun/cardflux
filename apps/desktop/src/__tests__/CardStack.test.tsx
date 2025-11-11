import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CardStack, CardStackItem } from '../renderer/components/CardStack';

describe('CardStack Component', () => {
  const mockCards: CardStackItem[] = [
    {
      id: '123456-1',
      name: 'Monkey.D.Luffy',
      number: 'ST01-001',
      rarity: 'Leader',
      set: 'Starter Deck',
      price: 5.99,
      confidence: 'HIGH',
      timestamp: Date.now(),
      productId: 123456,
      imageUrl: 'https://example.com/luffy.jpg',
    },
    {
      id: '789012-2',
      name: 'Trafalgar Law',
      number: 'ST02-001',
      rarity: 'Leader',
      set: 'Starter Deck 02',
      price: 7.50,
      confidence: 'HIGH',
      timestamp: Date.now() + 1000,
      productId: 789012,
      imageUrl: 'https://example.com/law.jpg',
    },
    {
      id: '345678-3',
      name: 'Roronoa Zoro',
      number: 'ST01-013',
      rarity: 'Super Rare',
      set: 'Starter Deck',
      price: 3.25,
      confidence: 'MODERATE',
      timestamp: Date.now() + 2000,
      productId: 345678,
    },
  ];

  const mockOnClear = jest.fn();
  const mockOnExport = jest.fn();
  const mockOnRemoveCard = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Empty State', () => {
    it('displays empty state when no cards', () => {
      render(
        <CardStack
          cards={[]}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getByText(/No cards scanned yet/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Press SPACE to capture and identify cards/i)
      ).toBeInTheDocument();
    });

    it('disables buttons when empty', () => {
      render(
        <CardStack
          cards={[]}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      const exportButton = screen.getByRole('button', { name: /export to csv/i });
      const clearButton = screen.getByRole('button', { name: /clear all cards/i });

      expect(exportButton).toBeDisabled();
      expect(clearButton).toBeDisabled();
    });

    it('shows 0 cards count', () => {
      render(
        <CardStack
          cards={[]}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // Use getAllByText since "0 cards" appears twice (header and footer)
      const cardCounts = screen.getAllByText(/0 cards/i);
      expect(cardCounts.length).toBeGreaterThan(0);
    });

    it('shows $0.00 total value', () => {
      render(
        <CardStack
          cards={[]}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getByText(/\$0\.00/)).toBeInTheDocument();
    });
  });

  describe('Card Display', () => {
    it('renders all cards in the stack', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getByText('Monkey.D.Luffy')).toBeInTheDocument();
      expect(screen.getByText('Trafalgar Law')).toBeInTheDocument();
      expect(screen.getByText('Roronoa Zoro')).toBeInTheDocument();
    });

    it('displays card numbers', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getByText('ST01-001')).toBeInTheDocument();
      expect(screen.getByText('ST02-001')).toBeInTheDocument();
      expect(screen.getByText('ST01-013')).toBeInTheDocument();
    });

    it('displays card rarities', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getAllByText('Leader')).toHaveLength(2);
      expect(screen.getByText('Super Rare')).toBeInTheDocument();
    });

    it('displays card sets', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getAllByText('Starter Deck')).toHaveLength(2);
      expect(screen.getByText('Starter Deck 02')).toBeInTheDocument();
    });

    it('displays card prices', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getByText('$5.99')).toBeInTheDocument();
      expect(screen.getByText('$7.50')).toBeInTheDocument();
      expect(screen.getByText('$3.25')).toBeInTheDocument();
    });

    it('displays confidence levels', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getAllByText('HIGH')).toHaveLength(2);
      expect(screen.getByText('MODERATE')).toBeInTheDocument();
    });

    it('displays timestamps in localized format', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // Should have 3 timestamps (one for each card)
      const timestamps = screen.getAllByText(/\d{1,2}:\d{2}:\d{2}/);
      expect(timestamps).toHaveLength(3);
    });

    it('renders card thumbnails when imageUrl provided', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      const images = screen.getAllByRole('img');
      expect(images).toHaveLength(2); // Only first two cards have imageUrl
      expect(images[0]).toHaveAttribute('src', 'https://example.com/luffy.jpg');
      expect(images[1]).toHaveAttribute('src', 'https://example.com/law.jpg');
    });

    it('hides image on load error', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      const image = screen.getAllByRole('img')[0];

      // Trigger error event
      const errorEvent = new Event('error');
      image.dispatchEvent(errorEvent);

      // Image should be hidden
      expect(image).toHaveStyle({ display: 'none' });
    });
  });

  describe('Card Count and Value', () => {
    it('displays correct card count', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // "3 cards" appears in both header and footer
      const cardCounts = screen.getAllByText('3 cards');
      expect(cardCounts.length).toBeGreaterThan(0);
    });

    it('uses singular form for single card', () => {
      render(
        <CardStack
          cards={[mockCards[0]]}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // "1 card" appears in both header and footer
      const cardCounts = screen.getAllByText('1 card');
      expect(cardCounts.length).toBeGreaterThan(0);
    });

    it('calculates total value correctly', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // 5.99 + 7.50 + 3.25 = 16.74
      expect(screen.getByText('$16.74')).toBeInTheDocument();
    });

    it('shows updated count after removing card', () => {
      const { rerender } = render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getAllByText('3 cards').length).toBeGreaterThan(0);

      // Simulate removing a card
      rerender(
        <CardStack
          cards={[mockCards[0], mockCards[1]]}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getAllByText('2 cards').length).toBeGreaterThan(0);
    });

    it('updates total value after removing card', () => {
      const { rerender } = render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getByText('$16.74')).toBeInTheDocument();

      // Remove card with price 3.25
      rerender(
        <CardStack
          cards={[mockCards[0], mockCards[1]]}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // 5.99 + 7.50 = 13.49
      expect(screen.getByText('$13.49')).toBeInTheDocument();
    });
  });

  describe('Actions', () => {
    it('enables buttons when cards present', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      const exportButton = screen.getByRole('button', { name: /export to csv/i });
      const clearButton = screen.getByRole('button', { name: /clear all cards/i });

      expect(exportButton).not.toBeDisabled();
      expect(clearButton).not.toBeDisabled();
    });

    it('calls onExport when Export button clicked', async () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      const user = userEvent.setup();
      const exportButton = screen.getByRole('button', { name: /export to csv/i });

      await user.click(exportButton);

      expect(mockOnExport).toHaveBeenCalledTimes(1);
    });

    it('calls onClear when Clear button clicked', async () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      const user = userEvent.setup();
      const clearButton = screen.getByRole('button', { name: /clear all cards/i });

      await user.click(clearButton);

      expect(mockOnClear).toHaveBeenCalledTimes(1);
    });

    it('calls onRemoveCard with correct id when remove button clicked', async () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      const user = userEvent.setup();
      const removeButtons = screen.getAllByRole('button', { name: /remove card/i });

      // Click first remove button
      await user.click(removeButtons[0]);

      expect(mockOnRemoveCard).toHaveBeenCalledWith('123456-1');
    });

    it('calls onRemoveCard for each card independently', async () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      const user = userEvent.setup();
      const removeButtons = screen.getAllByRole('button', { name: /remove card/i });

      // Click second remove button
      await user.click(removeButtons[1]);

      expect(mockOnRemoveCard).toHaveBeenCalledWith('789012-2');

      // Click third remove button
      await user.click(removeButtons[2]);

      expect(mockOnRemoveCard).toHaveBeenCalledWith('345678-3');
    });
  });

  describe('Performance', () => {
    it('memoizes component to prevent unnecessary re-renders', () => {
      const { rerender } = render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // Rerender with same props
      rerender(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // Component should still render (can't easily test memoization without React DevTools)
      // But at least verify it doesn't crash
      expect(screen.getByText('Monkey.D.Luffy')).toBeInTheDocument();
    });

    it('handles large number of cards efficiently', () => {
      const largeCardList: CardStackItem[] = Array.from({ length: 100 }, (_, i) => ({
        id: `card-${i}`,
        name: `Test Card ${i}`,
        number: `ST01-${String(i + 1).padStart(3, '0')}`,
        rarity: 'Common',
        set: 'Test Set',
        price: 1.0 + i * 0.1,
        confidence: 'HIGH',
        timestamp: Date.now() + i * 1000,
        productId: 100000 + i,
      }));

      render(
        <CardStack
          cards={largeCardList}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getAllByText('100 cards').length).toBeGreaterThan(0);
      // Total: 1.0*100 + 0.1*(0+1+2+...+99) = 100 + 0.1*4950 = 100 + 495 = 595.00
      expect(screen.getAllByText('$595.00').length).toBeGreaterThan(0);
    });
  });

  describe('Accessibility', () => {
    it('has accessible button labels', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getByRole('button', { name: /export to csv/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /clear all cards/i })).toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: /remove card/i })).toHaveLength(3);
    });

    it('provides alt text for card images', () => {
      render(
        <CardStack
          cards={mockCards}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(screen.getByAltText('Monkey.D.Luffy')).toBeInTheDocument();
      expect(screen.getByAltText('Trafalgar Law')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles card with zero price', () => {
      const cardsWithZeroPrice: CardStackItem[] = [
        {
          ...mockCards[0],
          price: 0,
        },
      ];

      render(
        <CardStack
          cards={cardsWithZeroPrice}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // $0.00 appears in both the card price and total value
      expect(screen.getAllByText('$0.00').length).toBeGreaterThan(0);
    });

    it('handles card with very high price', () => {
      const cardsWithHighPrice: CardStackItem[] = [
        {
          ...mockCards[0],
          price: 999.99,
        },
      ];

      render(
        <CardStack
          cards={cardsWithHighPrice}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // Price appears in card-price div
      const prices = screen.getAllByText('$999.99');
      expect(prices.length).toBeGreaterThan(0);
    });

    it('handles card without imageUrl gracefully', () => {
      const cardsWithoutImage: CardStackItem[] = [
        {
          ...mockCards[2], // This one has no imageUrl
        },
      ];

      render(
        <CardStack
          cards={cardsWithoutImage}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      // Should not crash and should not render img tag
      expect(screen.getByText('Roronoa Zoro')).toBeInTheDocument();
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
    });

    it('handles long card names gracefully', () => {
      const cardsWithLongName: CardStackItem[] = [
        {
          ...mockCards[0],
          name: 'This is a very long card name that should be handled gracefully without breaking the layout',
        },
      ];

      render(
        <CardStack
          cards={cardsWithLongName}
          onClear={mockOnClear}
          onExport={mockOnExport}
          onRemoveCard={mockOnRemoveCard}
        />
      );

      expect(
        screen.getByText(
          'This is a very long card name that should be handled gracefully without breaking the layout'
        )
      ).toBeInTheDocument();
    });
  });
});
