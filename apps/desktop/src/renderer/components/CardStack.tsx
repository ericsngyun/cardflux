import React from 'react';

export interface CardStackItem {
  id: string;
  name: string;
  number: string;
  rarity: string;
  set: string;
  price: number;
  confidence: string;
  timestamp: number;
  productId: number;
}

interface CardStackProps {
  cards: CardStackItem[];
  onClear: () => void;
  onExport: () => void;
  onRemoveCard: (id: string) => void;
}

export const CardStack: React.FC<CardStackProps> = React.memo(({ cards, onClear, onExport, onRemoveCard }) => {
  const totalValue = cards.reduce((sum, card) => sum + card.price, 0);
  const cardCount = cards.length;

  return (
    <div className="card-stack">
      <div className="card-stack-header">
        <div className="stack-title">
          <h2>📚 Card Stack</h2>
          <span className="card-count">{cardCount} {cardCount === 1 ? 'card' : 'cards'}</span>
        </div>
        <div className="stack-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={onExport}
            disabled={cardCount === 0}
          >
            📊 Export CSV
          </button>
          <button
            className="btn btn-danger btn-sm"
            onClick={onClear}
            disabled={cardCount === 0}
          >
            🗑️ Clear Stack
          </button>
        </div>
      </div>

      <div className="card-stack-list">
        {cardCount === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🎴</div>
            <p>No cards scanned yet</p>
            <p className="empty-hint">Use SPACE to capture and identify cards</p>
          </div>
        ) : (
          <div className="stack-items">
            {cards.map((card) => (
              <div key={card.id} className="stack-item">
                <div className="stack-item-main">
                  <div className="card-info">
                    <div className="card-name">{card.name}</div>
                    <div className="card-meta">
                      <span className="card-number">{card.number}</span>
                      <span className="card-rarity">{card.rarity}</span>
                      <span className={`card-confidence confidence-${card.confidence.toLowerCase()}`}>
                        {card.confidence}
                      </span>
                    </div>
                    <div className="card-set">{card.set}</div>
                  </div>
                  <div className="card-actions">
                    <div className="card-price">${card.price.toFixed(2)}</div>
                    <button
                      className="btn-icon"
                      onClick={() => onRemoveCard(card.id)}
                      title="Remove card"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <div className="stack-item-footer">
                  <span className="timestamp">
                    {new Date(card.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card-stack-footer">
        <div className="total-value">
          <span className="total-label">Total Value:</span>
          <span className="total-amount">${totalValue.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
});
