import React, { useState } from 'react';
import './DeliverableCards.css';

function AdCard({ deliverable, isSelected, onSelect, onRefine }) {
    const [activeVariation, setActiveVariation] = useState(0);
    const { data, platform, status } = deliverable;

    const imageUrl = data?.image_url;
    const variations = data?.variations || [];
    const currentVariation = variations[activeVariation] || {};
    const dimensions = data?.dimensions || '1200x628';

    return (
        <div
            className={`deliverable-card ad-card ${isSelected ? 'deliverable-card--selected' : ''} ${status === 'generating' ? 'deliverable-card--generating' : ''}`}
            onClick={onSelect}
        >
            {/* Header */}
            <div className="ad-card__header">
                <span className="ad-card__icon">📢</span>
                <span className="ad-card__label">
                    {platform === 'google' ? 'Google Ad' :
                     platform === 'facebook' ? 'Facebook Ad' :
                     platform === 'display' ? 'Display Ad' : 'Ad'}
                </span>
                <span className="ad-card__size">{dimensions}</span>
            </div>

            {/* Ad Preview */}
            <div className="ad-card__preview">
                {/* Image */}
                <div className="ad-card__image">
                    {imageUrl ? (
                        <img src={imageUrl} alt="Ad creative" />
                    ) : (
                        <div className="ad-card__image-placeholder">
                            <span>🖼️</span>
                        </div>
                    )}
                </div>

                {/* Copy Overlay */}
                <div className="ad-card__copy">
                    <h5 className="ad-card__headline">{currentVariation.headline || 'Headline'}</h5>
                    <p className="ad-card__body">{currentVariation.body || 'Ad body copy'}</p>
                    <button className="ad-card__cta-btn">{currentVariation.cta || 'Learn More'}</button>
                </div>
            </div>

            {/* Variation Selector */}
            {variations.length > 1 && (
                <div className="ad-card__variations">
                    <span className="variations-label">Variations:</span>
                    <div className="variation-tabs">
                        {variations.map((_, index) => (
                            <button
                                key={index}
                                className={`variation-tab ${activeVariation === index ? 'variation-tab--active' : ''}`}
                                onClick={(e) => { e.stopPropagation(); setActiveVariation(index); }}
                            >
                                {index + 1}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Status */}
            <div className={`ad-card__status ad-card__status--${status}`}>
                {status === 'generating' ? '⏳ Creating...' :
                 status === 'ready' ? '✓ Ready' :
                 status === 'approved' ? '✓✓ Approved' : status}
            </div>
        </div>
    );
}

export default AdCard;
