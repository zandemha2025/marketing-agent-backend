import React, { useState, useCallback, useEffect } from 'react';
import './TrendMaster.css';

/**
 * TrendMaster - AI-powered trend analysis and opportunity discovery.
 *
 * Features:
 * - Real-time trend monitoring
 * - Competitor activity tracking
 * - Industry news aggregation
 * - Opportunity scoring and recommendations
 * - One-click campaign brief generation from trends
 */

const TREND_CATEGORIES = [
    { key: 'all', label: 'All Trends', icon: '🔥' },
    { key: 'industry', label: 'Industry', icon: '🏭' },
    { key: 'social', label: 'Social Media', icon: '📱' },
    { key: 'competitor', label: 'Competitors', icon: '🎯' },
    { key: 'consumer', label: 'Consumer', icon: '👥' },
    { key: 'tech', label: 'Technology', icon: '💻' },
];

const TREND_TIMEFRAMES = [
    { key: '24h', label: 'Last 24h' },
    { key: '7d', label: 'Last 7 days' },
    { key: '30d', label: 'Last 30 days' },
    { key: '90d', label: 'Last quarter' },
];

export default function TrendMaster({
    onCreateBrief,
    onAnalyzeCompetitor,
    onRefresh,
    isLoading = false,
    trends = [], // Must be provided - no mock fallback
    error = null,
}) {
    const [selectedCategory, setSelectedCategory] = useState('all');
    const [selectedTimeframe, setSelectedTimeframe] = useState('7d');
    const [expandedTrend, setExpandedTrend] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');

    // Validate trends prop
    if (!Array.isArray(trends)) {
        console.error('TrendMaster: trends prop must be an array');
    }

    const filteredTrends = trends.filter(trend => {
        const matchesCategory = selectedCategory === 'all' || trend.category === selectedCategory;
        const matchesSearch = !searchQuery ||
            trend.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            trend.description.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesCategory && matchesSearch;
    });

    const handleCreateBriefFromTrend = useCallback((trend) => {
        if (onCreateBrief) {
            onCreateBrief({
                source: 'trend',
                trendId: trend.id,
                title: trend.title,
                context: trend.description,
                opportunities: trend.opportunities,
            });
        }
    }, [onCreateBrief]);

    const getScoreColor = (score) => {
        if (score >= 90) return '#10b981';
        if (score >= 75) return '#f59e0b';
        if (score >= 50) return '#6366f1';
        return '#666';
    };

    const getSentimentIcon = (sentiment) => {
        switch (sentiment) {
            case 'positive': return '📈';
            case 'negative': return '📉';
            default: return '➡️';
        }
    };

    const getRelevanceBadge = (relevance) => {
        switch (relevance) {
            case 'critical': return { label: 'Critical', color: '#ef4444' };
            case 'high': return { label: 'High', color: '#f59e0b' };
            case 'medium': return { label: 'Medium', color: '#6366f1' };
            default: return { label: 'Low', color: '#666' };
        }
    };

    return (
        <div className="trend-master">
            {/* Header */}
            <div className="trend-master__header">
                <div className="trend-master__title">
                    <h2>🔥 TrendMaster</h2>
                    <span className="trend-master__subtitle">AI-Powered Trend Intelligence</span>
                </div>
                <div className="trend-master__actions">
                    <button
                        className="trend-master__refresh"
                        onClick={onRefresh}
                        disabled={isLoading}
                    >
                        {isLoading ? '🔄 Updating...' : '🔄 Refresh'}
                    </button>
                </div>
            </div>

            {/* Search and Filters */}
            <div className="trend-master__filters">
                <div className="trend-master__search">
                    <span className="search-icon">🔍</span>
                    <input
                        type="text"
                        placeholder="Search trends..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>

                <div className="trend-master__timeframe">
                    {TREND_TIMEFRAMES.map(tf => (
                        <button
                            key={tf.key}
                            className={`timeframe-btn ${selectedTimeframe === tf.key ? 'timeframe-btn--active' : ''}`}
                            onClick={() => setSelectedTimeframe(tf.key)}
                        >
                            {tf.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Category Tabs */}
            <div className="trend-master__categories">
                {TREND_CATEGORIES.map(cat => (
                    <button
                        key={cat.key}
                        className={`category-tab ${selectedCategory === cat.key ? 'category-tab--active' : ''}`}
                        onClick={() => setSelectedCategory(cat.key)}
                    >
                        <span>{cat.icon}</span>
                        <span>{cat.label}</span>
                    </button>
                ))}
            </div>

            {/* Trends List */}
            <div className="trend-master__content">
                {isLoading ? (
                    <div className="trend-master__loading">
                        <div className="loading-spinner" />
                        <p>Analyzing trends across your industry...</p>
                    </div>
                ) : error ? (
                    <div className="trend-master__error">
                        <span className="error-icon">⚠️</span>
                        <p>{error}</p>
                        {onRefresh && (
                            <button onClick={onRefresh} className="retry-btn">
                                Try Again
                            </button>
                        )}
                    </div>
                ) : !trends || trends.length === 0 ? (
                    <div className="trend-master__empty">
                        <span className="empty-icon">📊</span>
                        <h3>No trends available</h3>
                        <p>We haven't detected any trends for your industry yet.</p>
                        <p className="empty-hint">Click "Refresh" to scan for new trends.</p>
                        {onRefresh && (
                            <button onClick={onRefresh} className="refresh-btn">
                                🔄 Scan for Trends
                            </button>
                        )}
                    </div>
                ) : filteredTrends.length === 0 ? (
                    <div className="trend-master__empty">
                        <span className="empty-icon">🔍</span>
                        <p>No trends found matching your criteria</p>
                        <button 
                            onClick={() => {setSearchQuery(''); setSelectedCategory('all');}}
                            className="clear-filters-btn"
                        >
                            Clear Filters
                        </button>
                    </div>
                ) : (
                    <div className="trends-list">
                        {filteredTrends.map(trend => {
                            const isExpanded = expandedTrend === trend.id;
                            const relevanceBadge = getRelevanceBadge(trend.relevance);

                            return (
                                <div
                                    key={trend.id}
                                    className={`trend-card ${isExpanded ? 'trend-card--expanded' : ''}`}
                                >
                                    {/* Trend Header */}
                                    <div
                                        className="trend-card__header"
                                        onClick={() => setExpandedTrend(isExpanded ? null : trend.id)}
                                    >
                                        <div className="trend-card__score" style={{ borderColor: getScoreColor(trend.score) }}>
                                            <span className="score-value">{trend.score}</span>
                                        </div>

                                        <div className="trend-card__info">
                                            <h3 className="trend-card__title">{trend.title}</h3>
                                            <p className="trend-card__description">{trend.description}</p>

                                            <div className="trend-card__meta">
                                                <span
                                                    className="trend-card__relevance"
                                                    style={{ backgroundColor: relevanceBadge.color }}
                                                >
                                                    {relevanceBadge.label}
                                                </span>
                                                <span className="trend-card__change">
                                                    {getSentimentIcon(trend.sentiment)} {trend.change}
                                                </span>
                                                <span className="trend-card__sources">
                                                    📰 {trend.sources.length} sources
                                                </span>
                                            </div>
                                        </div>

                                        <div className="trend-card__expand">
                                            <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>▼</span>
                                        </div>
                                    </div>

                                    {/* Expanded Content */}
                                    {isExpanded && (
                                        <div className="trend-card__body">
                                            <div className="trend-card__section">
                                                <h4>💡 Opportunities</h4>
                                                <ul className="opportunity-list">
                                                    {trend.opportunities.map((opp, idx) => (
                                                        <li key={idx}>{opp}</li>
                                                    ))}
                                                </ul>
                                            </div>

                                            <div className="trend-card__section">
                                                <h4>📰 Sources</h4>
                                                <div className="sources-list">
                                                    {trend.sources.map((source, idx) => (
                                                        <span key={idx} className="source-tag">{source}</span>
                                                    ))}
                                                </div>
                                            </div>

                                            <div className="trend-card__actions">
                                                <button
                                                    className="trend-action-btn trend-action-btn--primary"
                                                    onClick={() => handleCreateBriefFromTrend(trend)}
                                                >
                                                    ✨ Create Campaign Brief
                                                </button>
                                                <button
                                                    className="trend-action-btn"
                                                    onClick={() => onAnalyzeCompetitor?.(trend)}
                                                >
                                                    🎯 Deep Analysis
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Quick Stats */}
            <div className="trend-master__stats">
                <div className="stat-item">
                    <span className="stat-value">{trends.length}</span>
                    <span className="stat-label">Active Trends</span>
                </div>
                <div className="stat-item">
                    <span className="stat-value">{trends.filter(t => t.relevance === 'high' || t.relevance === 'critical').length}</span>
                    <span className="stat-label">High Priority</span>
                </div>
                <div className="stat-item">
                    <span className="stat-value">{trends.filter(t => t.actionable).length}</span>
                    <span className="stat-label">Actionable</span>
                </div>
            </div>
        </div>
    );
}
