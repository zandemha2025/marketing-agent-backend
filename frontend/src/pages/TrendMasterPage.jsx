import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import './TrendMasterPage.css';

/**
 * TrendMaster Page - AI-powered trend analysis dashboard
 * 
 * Features:
 * - Multi-source trend scanning (NewsAPI, Reddit, Google Trends)
 * - AI-powered trend analysis with predictions
 * - Trend cards with sentiment, growth rate, source count
 * - "Create Content from Trend" workflow
 * - Filtering by category and relevance
 */

const TrendMasterPage = ({ organizationId, onBack }) => {
    const [trends, setTrends] = useState([]);
    const [categories, setCategories] = useState(['All']);
    const [selectedCategory, setSelectedCategory] = useState('All');
    const [minRelevance, setMinRelevance] = useState(0);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [selectedTrend, setSelectedTrend] = useState(null);
    const [contentModalOpen, setContentModalOpen] = useState(false);
    const [contentType, setContentType] = useState('blog');
    const [generatingContent, setGeneratingContent] = useState(false);
    const [generatedContent, setGeneratedContent] = useState(null);

    // Fetch trends on mount and when filters change
    useEffect(() => {
        fetchTrends();
        fetchCategories();
    }, [organizationId, selectedCategory, minRelevance]);

    const fetchTrends = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await api.listAnalyzedTrends(
                organizationId,
                selectedCategory,
                minRelevance
            );
            setTrends(data);
        } catch (err) {
            setError(err.message || 'Failed to load trends');
            console.error('Error fetching trends:', err);
        } finally {
            setLoading(false);
        }
    }, [organizationId, selectedCategory, minRelevance]);

    const fetchCategories = useCallback(async () => {
        try {
            const data = await api.getTrendCategories();
            setCategories(data);
        } catch (err) {
            console.error('Error fetching categories:', err);
        }
    }, []);

    const handleRefresh = async () => {
        setRefreshing(true);
        try {
            await api.refreshTrends(organizationId);
            await fetchTrends();
        } catch (err) {
            setError(err.message || 'Failed to refresh trends');
        } finally {
            setRefreshing(false);
        }
    };

    const handleCreateContent = (trend) => {
        setSelectedTrend(trend);
        setContentModalOpen(true);
        setGeneratedContent(null);
    };

    const handleGenerateContent = async () => {
        if (!selectedTrend) return;
        
        setGeneratingContent(true);
        try {
            const result = await api.createContentFromTrend(organizationId, {
                trend_title: selectedTrend.title,
                trend_description: selectedTrend.description,
                content_type: contentType,
                keywords: selectedTrend.keywords || [],
            });
            setGeneratedContent(result);
        } catch (err) {
            setError(err.message || 'Failed to generate content');
        } finally {
            setGeneratingContent(false);
        }
    };

    const closeContentModal = () => {
        setContentModalOpen(false);
        setSelectedTrend(null);
        setGeneratedContent(null);
    };

    const getSentimentColor = (sentiment) => {
        switch (sentiment?.toLowerCase()) {
            case 'positive': return 'var(--color-success)';
            case 'negative': return 'var(--color-error)';
            case 'mixed': return 'var(--color-warning)';
            default: return 'var(--color-text-secondary)';
        }
    };

    const getPhaseColor = (phase) => {
        switch (phase?.toLowerCase()) {
            case 'emerging': return '#3b82f6'; // Blue
            case 'growth': return '#10b981'; // Green
            case 'peak': return '#f59e0b'; // Orange
            case 'decline': return '#ef4444'; // Red
            default: return 'var(--color-text-secondary)';
        }
    };

    const getPhaseLabel = (phase) => {
        switch (phase?.toLowerCase()) {
            case 'emerging': return '🌱 Emerging';
            case 'growth': return '📈 Growth';
            case 'peak': return '⛰️ Peak';
            case 'decline': return '📉 Decline';
            default: return '❓ Unknown';
        }
    };

    return (
        <div className="trendmaster-page">
            <header className="trendmaster-header">
                <div className="header-left">
                    {onBack && (
                        <button className="back-button" onClick={onBack}>
                            ← Back
                        </button>
                    )}
                    <h1>TrendMaster</h1>
                    <p className="subtitle">AI-powered trend analysis and insights</p>
                </div>
                <div className="header-actions">
                    <button 
                        className="refresh-button"
                        onClick={handleRefresh}
                        disabled={refreshing}
                    >
                        {refreshing ? '⟳ Refreshing...' : '↻ Refresh Trends'}
                    </button>
                </div>
            </header>

            <div className="trendmaster-filters">
                <div className="filter-group">
                    <label>Category</label>
                    <select 
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                    >
                        {categories.map(cat => (
                            <option key={cat} value={cat}>{cat}</option>
                        ))}
                    </select>
                </div>
                <div className="filter-group">
                    <label>Min Relevance: {minRelevance}%</label>
                    <input
                        type="range"
                        min="0"
                        max="100"
                        value={minRelevance}
                        onChange={(e) => setMinRelevance(parseInt(e.target.value))}
                    />
                </div>
            </div>

            {error && (
                <div className="error-banner">
                    <span>{error}</span>
                    <button onClick={() => setError(null)}>✕</button>
                </div>
            )}

            {loading ? (
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Analyzing trends across multiple sources...</p>
                </div>
            ) : trends.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">📊</div>
                    <h3>No trends found</h3>
                    <p>Try adjusting your filters or refresh to scan for new trends.</p>
                    <button onClick={handleRefresh} disabled={refreshing}>
                        {refreshing ? 'Scanning...' : 'Scan for Trends'}
                    </button>
                </div>
            ) : (
                <div className="trends-grid">
                    {trends.map((trend, index) => (
                        <div key={index} className="trend-card">
                            <div className="trend-header">
                                <span 
                                    className="trend-category"
                                    style={{ 
                                        backgroundColor: `var(--color-category-${trend.category?.toLowerCase().replace(/\s+/g, '-') || 'default'}, var(--color-surface-hover))`
                                    }}
                                >
                                    {trend.category}
                                </span>
                                {trend.prediction && (
                                    <span 
                                        className="trend-phase"
                                        style={{ color: getPhaseColor(trend.prediction.phase) }}
                                    >
                                        {getPhaseLabel(trend.prediction.phase)}
                                    </span>
                                )}
                            </div>

                            <h3 className="trend-title">{trend.title}</h3>
                            <p className="trend-description">{trend.description}</p>

                            {trend.keywords && trend.keywords.length > 0 && (
                                <div className="trend-keywords">
                                    {trend.keywords.slice(0, 5).map((keyword, i) => (
                                        <span key={i} className="keyword-tag">#{keyword}</span>
                                    ))}
                                </div>
                            )}

                            <div className="trend-metrics">
                                <div className="metric">
                                    <span className="metric-label">Sources</span>
                                    <span className="metric-value">{trend.source_count}</span>
                                </div>
                                <div className="metric">
                                    <span className="metric-label">Relevance</span>
                                    <span className="metric-value">{trend.relevance_score}%</span>
                                </div>
                                {trend.prediction && (
                                    <div className="metric">
                                        <span className="metric-label">Growth</span>
                                        <span className="metric-value" style={{ 
                                            color: trend.prediction.growth_rate > 0 ? 'var(--color-success)' : 'var(--color-error)'
                                        }}>
                                            {trend.prediction.growth_rate > 0 ? '+' : ''}
                                            {trend.prediction.growth_rate.toFixed(1)}%
                                        </span>
                                    </div>
                                )}
                                <div className="metric">
                                    <span className="metric-label">Sentiment</span>
                                    <span 
                                        className="metric-value sentiment-badge"
                                        style={{ color: getSentimentColor(trend.sentiment) }}
                                    >
                                        {trend.sentiment}
                                    </span>
                                </div>
                            </div>

                            {trend.content_opportunities && trend.content_opportunities.length > 0 && (
                                <div className="content-opportunities">
                                    <h4>💡 Content Ideas</h4>
                                    <ul>
                                        {trend.content_opportunities.slice(0, 3).map((opp, i) => (
                                            <li key={i}>{opp}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <div className="trend-actions">
                                <button 
                                    className="create-content-btn"
                                    onClick={() => handleCreateContent(trend)}
                                >
                                    ✨ Create Content
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Content Generation Modal */}
            {contentModalOpen && selectedTrend && (
                <div className="modal-overlay" onClick={closeContentModal}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Create Content from Trend</h2>
                            <button className="close-btn" onClick={closeContentModal}>✕</button>
                        </div>

                        <div className="modal-body">
                            <div className="trend-summary">
                                <h3>{selectedTrend.title}</h3>
                                <p>{selectedTrend.description}</p>
                            </div>

                            {!generatedContent ? (
                                <>
                                    <div className="form-group">
                                        <label>Content Type</label>
                                        <select 
                                            value={contentType}
                                            onChange={(e) => setContentType(e.target.value)}
                                        >
                                            <option value="blog">Blog Post</option>
                                            <option value="social">Social Media Post</option>
                                            <option value="linkedin">LinkedIn Post</option>
                                            <option value="twitter">Twitter/X Thread</option>
                                            <option value="email">Email Newsletter</option>
                                        </select>
                                    </div>

                                    <button 
                                        className="generate-btn"
                                        onClick={handleGenerateContent}
                                        disabled={generatingContent}
                                    >
                                        {generatingContent ? (
                                            <>
                                                <span className="spinner-small"></span>
                                                Generating...
                                            </>
                                        ) : (
                                            '✨ Generate Content'
                                        )}
                                    </button>
                                </>
                            ) : (
                                <div className="generated-content">
                                    <h4>{generatedContent.title}</h4>
                                    <div className="content-text">
                                        {generatedContent.content}
                                    </div>
                                    {generatedContent.suggested_hashtags?.length > 0 && (
                                        <div className="suggested-hashtags">
                                            <strong>Suggested Hashtags:</strong>
                                            <div className="hashtag-list">
                                                {generatedContent.suggested_hashtags.map((tag, i) => (
                                                    <span key={i} className="hashtag">#{tag}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    {generatedContent.cta && (
                                        <div className="cta-section">
                                            <strong>Call to Action:</strong>
                                            <p>{generatedContent.cta}</p>
                                        </div>
                                    )}
                                    <div className="content-actions">
                                        <button 
                                            className="secondary-btn"
                                            onClick={() => setGeneratedContent(null)}
                                        >
                                            ← Back
                                        </button>
                                        <button 
                                            className="primary-btn"
                                            onClick={() => {
                                                navigator.clipboard.writeText(generatedContent.content);
                                                alert('Content copied to clipboard!');
                                            }}
                                        >
                                            📋 Copy Content
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default TrendMasterPage;