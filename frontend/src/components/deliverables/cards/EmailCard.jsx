import React, { useState } from 'react';
import './DeliverableCards.css';

function EmailCard({ deliverable, isSelected, onSelect, onRefine }) {
    const [activeSubject, setActiveSubject] = useState('primary');
    const [showFullBody, setShowFullBody] = useState(false);
    const { data, status } = deliverable;

    const subject = data?.subject || {};
    const subjects = {
        primary: subject.primary || 'Subject line',
        variant_a: subject.variant_a,
        variant_b: subject.variant_b,
    };

    const preview = data?.preview || '';
    const bodyText = data?.body_text || '';
    const truncatedBody = bodyText.length > 200 ? bodyText.slice(0, 200) + '...' : bodyText;
    const cta = data?.cta || {};

    return (
        <div
            className={`deliverable-card email-card ${isSelected ? 'deliverable-card--selected' : ''} ${status === 'generating' ? 'deliverable-card--generating' : ''}`}
            onClick={onSelect}
        >
            {/* Header */}
            <div className="email-card__header">
                <span className="email-card__icon">📧</span>
                <span className="email-card__label">Email</span>
            </div>

            {/* Subject Lines */}
            <div className="email-card__subjects">
                <div className="subject-tabs">
                    {Object.entries(subjects).map(([key, value]) => (
                        value && (
                            <button
                                key={key}
                                className={`subject-tab ${activeSubject === key ? 'subject-tab--active' : ''}`}
                                onClick={(e) => { e.stopPropagation(); setActiveSubject(key); }}
                            >
                                {key === 'primary' ? 'Main' : key === 'variant_a' ? 'A' : 'B'}
                            </button>
                        )
                    ))}
                </div>
                <div className="email-card__subject-line">
                    <strong>Subject:</strong> {subjects[activeSubject]}
                </div>
                {preview && (
                    <div className="email-card__preview">
                        <span className="preview-label">Preview:</span> {preview}
                    </div>
                )}
            </div>

            {/* Body Preview */}
            <div className="email-card__body">
                <div
                    className="email-card__body-content"
                    onClick={(e) => { e.stopPropagation(); setShowFullBody(!showFullBody); }}
                >
                    {showFullBody ? bodyText : truncatedBody}
                </div>
            </div>

            {/* CTA */}
            {cta.text && (
                <div className="email-card__cta">
                    <button className="cta-button">{cta.text}</button>
                    {cta.supporting && (
                        <p className="cta-supporting">{cta.supporting}</p>
                    )}
                </div>
            )}

            {/* Sign Off */}
            {data?.sign_off && (
                <div className="email-card__signoff">
                    {data.sign_off.line}<br />
                    <strong>{data.sign_off.name}</strong>
                </div>
            )}

            {/* Status */}
            <div className={`email-card__status email-card__status--${status}`}>
                {status === 'generating' ? '⏳ Creating...' :
                 status === 'ready' ? '✓ Ready' :
                 status === 'approved' ? '✓✓ Approved' : status}
            </div>
        </div>
    );
}

export default EmailCard;
