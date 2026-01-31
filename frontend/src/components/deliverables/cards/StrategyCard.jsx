import React, { useState } from 'react';
import './DeliverableCards.css';

function StrategyCard({ deliverable, isSelected, onSelect, onRefine }) {
    const [expanded, setExpanded] = useState(false);
    const { data, status } = deliverable;

    const campaignName = data?.campaign_name || 'Campaign Strategy';
    const targetAudience = data?.target_audience || '';
    const keyMessages = data?.key_messages || [];
    const channels = data?.channels || [];
    const contentPillars = data?.content_pillars || [];
    const executiveSummary = data?.executive_summary || '';

    return (
        <div
            className={`deliverable-card strategy-card ${isSelected ? 'deliverable-card--selected' : ''} ${status === 'generating' ? 'deliverable-card--generating' : ''}`}
            onClick={onSelect}
        >
            {/* Header */}
            <div className="strategy-card__header">
                <span className="strategy-card__icon">📊</span>
                <span className="strategy-card__label">Strategy Document</span>
            </div>

            {/* Title */}
            <h4 className="strategy-card__title">{campaignName}</h4>

            {/* Executive Summary */}
            {executiveSummary && (
                <div className="strategy-card__summary">
                    <p>{executiveSummary.slice(0, 150)}{executiveSummary.length > 150 ? '...' : ''}</p>
                </div>
            )}

            {/* Key Info Grid */}
            <div className="strategy-card__grid">
                {/* Target Audience */}
                {targetAudience && (
                    <div className="strategy-card__item">
                        <span className="item-icon">👥</span>
                        <span className="item-label">Audience</span>
                        <span className="item-value">{targetAudience.slice(0, 50)}</span>
                    </div>
                )}

                {/* Channels */}
                {channels.length > 0 && (
                    <div className="strategy-card__item">
                        <span className="item-icon">📡</span>
                        <span className="item-label">Channels</span>
                        <span className="item-value">{channels.slice(0, 3).join(', ')}</span>
                    </div>
                )}
            </div>

            {/* Expandable Details */}
            {expanded && (
                <div className="strategy-card__details">
                    {/* Key Messages */}
                    {keyMessages.length > 0 && (
                        <div className="detail-section">
                            <h5>Key Messages</h5>
                            <ul>
                                {keyMessages.map((msg, i) => (
                                    <li key={i}>{typeof msg === 'string' ? msg : msg.message || msg.text}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Content Pillars */}
                    {contentPillars.length > 0 && (
                        <div className="detail-section">
                            <h5>Content Pillars</h5>
                            <div className="pillars">
                                {contentPillars.map((pillar, i) => (
                                    <span key={i} className="pillar-tag">
                                        {typeof pillar === 'string' ? pillar : pillar.name || pillar.title}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Expand Toggle */}
            <button
                className="strategy-card__toggle"
                onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            >
                {expanded ? '▲ Show Less' : '▼ Show More'}
            </button>

            {/* Status */}
            <div className={`strategy-card__status strategy-card__status--${status}`}>
                {status === 'generating' ? '⏳ Creating...' :
                 status === 'ready' ? '✓ Ready' :
                 status === 'approved' ? '✓✓ Approved' : status}
            </div>
        </div>
    );
}

export default StrategyCard;
