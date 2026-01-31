import React, { useState } from 'react';
import './DeliverableCards.css';

function LandingPageCard({ deliverable, isSelected, onSelect, onRefine }) {
    const [showPreview, setShowPreview] = useState(false);
    const { data, status } = deliverable;

    const previewUrl = data?.preview_url;
    const html = data?.html || '';
    const sections = data?.sections || [];
    const headline = data?.headline;

    return (
        <div
            className={`deliverable-card landing-page-card ${isSelected ? 'deliverable-card--selected' : ''} ${status === 'generating' ? 'deliverable-card--generating' : ''}`}
            onClick={onSelect}
        >
            {/* Header */}
            <div className="landing-page-card__header">
                <span className="landing-page-card__icon">🌐</span>
                <span className="landing-page-card__label">Landing Page</span>
            </div>

            {/* Preview Thumbnail */}
            <div className="landing-page-card__thumbnail">
                {previewUrl ? (
                    <img src={previewUrl} alt="Page preview" />
                ) : html ? (
                    <div className="landing-page-card__mini-preview">
                        <div className="mini-browser">
                            <div className="mini-browser__bar">
                                <span className="dot"></span>
                                <span className="dot"></span>
                                <span className="dot"></span>
                            </div>
                            <div className="mini-browser__content">
                                {headline && <div className="mini-headline">{headline}</div>}
                                {sections.slice(0, 3).map((section, i) => (
                                    <div key={i} className="mini-section"></div>
                                ))}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="landing-page-card__placeholder">
                        <span>🌐</span>
                        <p>Building page...</p>
                    </div>
                )}
            </div>

            {/* Sections List */}
            {sections.length > 0 && (
                <div className="landing-page-card__sections">
                    <span className="sections-label">Sections:</span>
                    <ul>
                        {sections.slice(0, 4).map((section, i) => (
                            <li key={i}>{section.type || section.name || `Section ${i + 1}`}</li>
                        ))}
                        {sections.length > 4 && (
                            <li className="more">+{sections.length - 4} more</li>
                        )}
                    </ul>
                </div>
            )}

            {/* Preview Button */}
            {html && (
                <button
                    className="landing-page-card__preview-btn"
                    onClick={(e) => { e.stopPropagation(); setShowPreview(true); }}
                >
                    👁️ Preview Full Page
                </button>
            )}

            {/* Status */}
            <div className={`landing-page-card__status landing-page-card__status--${status}`}>
                {status === 'generating' ? '⏳ Building...' :
                 status === 'ready' ? '✓ Ready' :
                 status === 'approved' ? '✓✓ Approved' : status}
            </div>

            {/* Full Preview Modal */}
            {showPreview && (
                <div className="preview-modal" onClick={() => setShowPreview(false)}>
                    <div className="preview-modal__content" onClick={e => e.stopPropagation()}>
                        <button className="preview-modal__close" onClick={() => setShowPreview(false)}>✕</button>
                        <iframe
                            srcDoc={html}
                            title="Landing Page Preview"
                            sandbox="allow-scripts"
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

export default LandingPageCard;
