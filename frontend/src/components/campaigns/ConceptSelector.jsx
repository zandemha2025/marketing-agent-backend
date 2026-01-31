import React from 'react';
import './ConceptSelector.css';

export default function ConceptSelector({ concepts, selectedIndex, onSelect }) {
  if (!concepts || concepts.length === 0) {
    return (
      <div className="concept-selector concept-selector--empty">
        <p>No concepts available.</p>
      </div>
    );
  }

  return (
    <div className="concept-selector">
      <h2 className="concept-selector__title">Creative Concepts</h2>
      <p className="concept-selector__subtitle">Select a concept to move forward with.</p>

      <div className="concept-selector__grid">
        {concepts.map((concept, index) => {
          const isSelected = index === selectedIndex;
          return (
            <div
              key={index}
              className={`concept-card ${isSelected ? 'concept-card--selected' : ''}`}
            >
              <div className="concept-card__badge">Concept {index + 1}</div>

              <h3 className="concept-card__name">{concept.name}</h3>

              {concept.tagline && (
                <p className="concept-card__tagline">{concept.tagline}</p>
              )}

              {concept.concept_summary && (
                <p className="concept-card__summary">{concept.concept_summary}</p>
              )}

              {concept.visual_direction && (
                <div className="concept-card__visual">
                  <span className="concept-card__visual-label">Visual Direction</span>
                  <p className="concept-card__visual-text">{concept.visual_direction}</p>
                </div>
              )}

              <button
                className={`concept-card__btn ${isSelected ? 'concept-card__btn--selected' : ''}`}
                onClick={() => onSelect(index)}
              >
                {isSelected ? 'Selected' : 'Select Concept'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
