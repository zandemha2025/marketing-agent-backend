import React, { useState } from 'react';
import SocialPostCard from './cards/SocialPostCard';
import EmailCard from './cards/EmailCard';
import VideoCard from './cards/VideoCard';
import BlogCard from './cards/BlogCard';
import AdCard from './cards/AdCard';
import LandingPageCard from './cards/LandingPageCard';
import StrategyCard from './cards/StrategyCard';
import './DeliverablesPanel.css';

const TYPE_COMPONENTS = {
    social_post: SocialPostCard,
    email: EmailCard,
    video: VideoCard,
    blog_post: BlogCard,
    ad: AdCard,
    landing_page: LandingPageCard,
    strategy_doc: StrategyCard,
};

const TYPE_LABELS = {
    social_post: 'Social Posts',
    email: 'Emails',
    video: 'Videos',
    blog_post: 'Blog Posts',
    ad: 'Ads',
    landing_page: 'Landing Pages',
    strategy_doc: 'Strategy',
};

function DeliverablesPanel({
    deliverables = [],
    selectedId,
    onSelect,
    onRefine,
    phase = 'producing',
    progress = 0,
    statusMessage = ''
}) {
    const [viewMode, setViewMode] = useState('feed'); // 'feed' or 'grouped'
    const [expandedTypes, setExpandedTypes] = useState(new Set(['social_post', 'email']));

    // Group deliverables by type
    const grouped = deliverables.reduce((acc, d) => {
        if (!acc[d.type]) acc[d.type] = [];
        acc[d.type].push(d);
        return acc;
    }, {});

    const toggleExpand = (type) => {
        const next = new Set(expandedTypes);
        if (next.has(type)) {
            next.delete(type);
        } else {
            next.add(type);
        }
        setExpandedTypes(next);
    };

    const renderDeliverable = (deliverable) => {
        const Component = TYPE_COMPONENTS[deliverable.type];
        if (!Component) {
            return (
                <div
                    key={deliverable.id}
                    className={`deliverable-card deliverable-card--generic ${selectedId === deliverable.id ? 'deliverable-card--selected' : ''}`}
                    onClick={() => onSelect?.(deliverable.id)}
                >
                    <div className="deliverable-card__type">{deliverable.type}</div>
                    <div className="deliverable-card__platform">{deliverable.platform}</div>
                </div>
            );
        }

        return (
            <Component
                key={deliverable.id}
                deliverable={deliverable}
                isSelected={selectedId === deliverable.id}
                onSelect={() => onSelect?.(deliverable.id)}
                onRefine={(feedback) => onRefine?.(deliverable.id, feedback)}
            />
        );
    };

    const readyCount = deliverables.filter(d => d.status === 'ready').length;
    const totalCount = deliverables.length;

    return (
        <div className="deliverables-panel">
            {/* Header */}
            <div className="deliverables-panel__header">
                <div className="deliverables-panel__title">
                    <h3>Deliverables</h3>
                    <span className="deliverables-panel__count">
                        {readyCount}/{totalCount} ready
                    </span>
                </div>
                <div className="deliverables-panel__controls">
                    <button
                        className={`view-toggle ${viewMode === 'feed' ? 'view-toggle--active' : ''}`}
                        onClick={() => setViewMode('feed')}
                        title="Feed view"
                    >
                        ☰
                    </button>
                    <button
                        className={`view-toggle ${viewMode === 'grouped' ? 'view-toggle--active' : ''}`}
                        onClick={() => setViewMode('grouped')}
                        title="Grouped view"
                    >
                        ▤
                    </button>
                </div>
            </div>

            {/* Progress (shown during production) */}
            {phase === 'producing' && (
                <div className="deliverables-panel__progress">
                    <div className="progress-bar">
                        <div
                            className="progress-bar__fill"
                            style={{ width: `${progress * 100}%` }}
                        />
                    </div>
                    <span className="progress-message">{statusMessage}</span>
                </div>
            )}

            {/* Content */}
            <div className="deliverables-panel__content">
                {deliverables.length === 0 ? (
                    <div className="deliverables-panel__empty">
                        <div className="empty-icon">📦</div>
                        <p>Deliverables will appear here as they're created</p>
                    </div>
                ) : viewMode === 'feed' ? (
                    // Feed view - chronological
                    <div className="deliverables-feed">
                        {deliverables.map(renderDeliverable)}
                    </div>
                ) : (
                    // Grouped view - by type
                    <div className="deliverables-grouped">
                        {Object.entries(grouped).map(([type, items]) => (
                            <div key={type} className="deliverable-group">
                                <button
                                    className="deliverable-group__header"
                                    onClick={() => toggleExpand(type)}
                                >
                                    <span className="deliverable-group__title">
                                        {TYPE_LABELS[type] || type}
                                    </span>
                                    <span className="deliverable-group__count">
                                        {items.length}
                                    </span>
                                    <span className={`deliverable-group__chevron ${expandedTypes.has(type) ? 'expanded' : ''}`}>
                                        ›
                                    </span>
                                </button>
                                {expandedTypes.has(type) && (
                                    <div className="deliverable-group__items">
                                        {items.map(renderDeliverable)}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Selected deliverable hint */}
            {selectedId && (
                <div className="deliverables-panel__hint">
                    💬 Type in chat to refine the selected item
                </div>
            )}
        </div>
    );
}

export default DeliverablesPanel;
