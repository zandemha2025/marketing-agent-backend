import React, { useState, useCallback } from 'react';
import api from '../services/api';
import './ArticleWriterPage.css';

/**
 * Article Writer Page - Interview-to-Content workflow
 * 
 * Features:
 * - Voice/text interview input
 * - AI transcription processing
 * - Multi-format content generation from single interview:
 *   - Blog articles
 *   - LinkedIn posts
 *   - Twitter threads
 *   - Press releases
 *   - Email newsletters
 * - Content calendar integration
 */

const ArticleWriterPage = ({ organizationId, onBack }) => {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // Interview input
    const [interviewTitle, setInterviewTitle] = useState('');
    const [interviewText, setInterviewText] = useState('');
    const [targetAudience, setTargetAudience] = useState('');
    
    // Processed interview
    const [processedInterview, setProcessedInterview] = useState(null);
    
    // Generated content
    const [generatedContent, setGeneratedContent] = useState(null);
    const [selectedFormats, setSelectedFormats] = useState([
        'blog', 'linkedin', 'twitter', 'email'
    ]);
    const [activeTab, setActiveTab] = useState('blog');

    const availableFormats = [
        { id: 'blog', label: 'Blog Article', icon: '📝' },
        { id: 'linkedin', label: 'LinkedIn Post', icon: '💼' },
        { id: 'twitter', label: 'Twitter Thread', icon: '🐦' },
        { id: 'press_release', label: 'Press Release', icon: '📰' },
        { id: 'email', label: 'Email Newsletter', icon: '📧' },
    ];

    const handleProcessInterview = async () => {
        if (!interviewTitle.trim() || !interviewText.trim()) {
            setError('Please provide both a title and interview text');
            return;
        }
        
        setLoading(true);
        setError(null);
        
        try {
            const result = await api.processInterview(organizationId, {
                text: interviewText,
                title: interviewTitle,
            });
            
            setProcessedInterview(result);
            setStep(2);
        } catch (err) {
            setError(err.message || 'Failed to process interview');
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateContent = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const result = await api.generateContentFromInterview(organizationId, {
                interview_text: interviewText,
                interview_title: interviewTitle,
                formats: selectedFormats,
                target_audience: targetAudience || undefined,
            });
            
            setGeneratedContent(result.contents);
            setStep(3);
        } catch (err) {
            setError(err.message || 'Failed to generate content');
        } finally {
            setLoading(false);
        }
    };

    const toggleFormat = (formatId) => {
        setSelectedFormats(prev => 
            prev.includes(formatId)
                ? prev.filter(f => f !== formatId)
                : [...prev, formatId]
        );
    };

    const getInsightIcon = (category) => {
        switch (category) {
            case 'story': return '📖';
            case 'statistic': return '📊';
            case 'quote': return '💬';
            case 'idea': return '💡';
            case 'pain_point': return '😰';
            case 'solution': return '✅';
            default: return '📝';
        }
    };

    const renderStep1 = () => (
        <div className="article-step">
            <h3>Step 1: Input Your Interview</h3>
            <p className="step-description">
                Paste your interview transcript or notes. Our AI will analyze it and extract key insights.
            </p>
            
            <div className="form-group">
                <label>Interview Title *</label>
                <input
                    type="text"
                    value={interviewTitle}
                    onChange={(e) => setInterviewTitle(e.target.value)}
                    placeholder="e.g., Q&A with CEO about Product Launch"
                />
            </div>

            <div className="form-group">
                <label>Target Audience</label>
                <input
                    type="text"
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    placeholder="e.g., Enterprise marketing teams"
                />
            </div>

            <div className="form-group">
                <label>Interview Text *</label>
                <textarea
                    value={interviewText}
                    onChange={(e) => setInterviewText(e.target.value)}
                    placeholder={`Paste your interview transcript here...

Example format:
Interviewer: Can you tell us about your new product?

Interviewee: Absolutely! We've been working on this for two years...`}
                    rows={15}
                />
                <span className="word-count">
                    {interviewText.split(/\s+/).filter(w => w).length} words
                </span>
            </div>

            <div className="format-note">
                <strong>💡 Tip:</strong> Include speaker names followed by colons (e.g., "John:") 
                for better speaker identification.
            </div>
        </div>
    );

    const renderStep2 = () => {
        if (!processedInterview) return null;

        return (
            <div className="article-step">
                <h3>Step 2: Review Extracted Insights</h3>
                <p className="step-description">
                    We've analyzed your interview. Review the key insights before generating content.
                </p>

                <div className="interview-summary">
                    <h4>Summary</h4>
                    <p>{processedInterview.summary}</p>
                    <div className="summary-stats">
                        <span>{processedInterview.word_count} words</span>
                        <span>{processedInterview.segments.length} segments</span>
                        {processedInterview.duration_minutes && (
                            <span>~{Math.round(processedInterview.duration_minutes)} min</span>
                        )}
                    </div>
                </div>

                {processedInterview.topics.length > 0 && (
                    <div className="topics-section">
                        <h4>Topics Detected</h4>
                        <div className="topic-tags">
                            {processedInterview.topics.map((topic, i) => (
                                <span key={i} className="topic-tag">{topic}</span>
                            ))}
                        </div>
                    </div>
                )}

                {processedInterview.insights.length > 0 && (
                    <div className="insights-section">
                        <h4>Key Insights ({processedInterview.insights.length})</h4>
                        <div className="insights-list">
                            {processedInterview.insights.map((insight, i) => (
                                <div key={i} className="insight-card">
                                    <span className="insight-icon">
                                        {getInsightIcon(insight.category)}
                                    </span>
                                    <div className="insight-content">
                                        <span className="insight-category">{insight.category}</span>
                                        <p>{insight.content}</p>
                                    </div>
                                    <span className="insight-importance">
                                        {'★'.repeat(insight.importance)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {processedInterview.key_quotes.length > 0 && (
                    <div className="quotes-section">
                        <h4>Notable Quotes</h4>
                        <div className="quotes-list">
                            {processedInterview.key_quotes.map((quote, i) => (
                                <blockquote key={i} className="quote-card">
                                    "{quote}"
                                </blockquote>
                            ))}
                        </div>
                    </div>
                )}

                <div className="formats-selection">
                    <h4>Select Content Formats to Generate</h4>
                    <div className="format-checkboxes">
                        {availableFormats.map(fmt => (
                            <label key={fmt.id} className="format-checkbox">
                                <input
                                    type="checkbox"
                                    checked={selectedFormats.includes(fmt.id)}
                                    onChange={() => toggleFormat(fmt.id)}
                                />
                                <span className="format-icon">{fmt.icon}</span>
                                <span className="format-label">{fmt.label}</span>
                            </label>
                        ))}
                    </div>
                </div>
            </div>
        );
    };

    const renderStep3 = () => {
        if (!generatedContent) return null;

        const activeContent = generatedContent[activeTab];
        if (!activeContent) return null;

        return (
            <div className="article-step">
                <h3>Step 3: Generated Content</h3>
                <p className="step-description">
                    Your content has been generated. Review, edit, and export each piece.
                </p>

                <div className="content-tabs">
                    {availableFormats
                        .filter(fmt => selectedFormats.includes(fmt.id) && generatedContent[fmt.id])
                        .map(fmt => (
                            <button
                                key={fmt.id}
                                className={`content-tab ${activeTab === fmt.id ? 'active' : ''}`}
                                onClick={() => setActiveTab(fmt.id)}
                            >
                                <span className="tab-icon">{fmt.icon}</span>
                                <span className="tab-label">{fmt.label}</span>
                            </button>
                        ))}
                </div>

                <div className="generated-content-panel">
                    <div className="content-header">
                        <h4>{activeContent.title}</h4>
                        <div className="content-meta">
                            <span>{activeContent.word_count} words</span>
                            <span>{activeContent.estimated_read_time} min read</span>
                        </div>
                    </div>

                    <div className="content-body">
                        {activeTab === 'twitter' ? (
                            <div className="twitter-thread">
                                {activeContent.content.split(/\n\n?\d+\//).filter(Boolean).map((tweet, i) => (
                                    <div key={i} className="tweet">
                                        <span className="tweet-number">{i + 1}/</span>
                                        <p>{tweet.replace(/^\//, '').trim()}</p>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="content-text">
                                {activeContent.content.split('\n').map((para, i) => (
                                    <p key={i}>{para}</p>
                                ))}
                            </div>
                        )}
                    </div>

                    {activeContent.suggested_hashtags?.length > 0 && (
                        <div className="hashtags-section">
                            <strong>Suggested Hashtags:</strong>
                            <div className="hashtag-list">
                                {activeContent.suggested_hashtags.map((tag, i) => (
                                    <span key={i} className="hashtag">#{tag}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {activeContent.key_takeaways?.length > 0 && (
                        <div className="takeaways-section">
                            <strong>Key Takeaways:</strong>
                            <ul>
                                {activeContent.key_takeaways.map((point, i) => (
                                    <li key={i}>{point}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <div className="content-actions">
                        <button 
                            className="copy-btn"
                            onClick={() => {
                                navigator.clipboard.writeText(activeContent.content);
                                alert('Content copied to clipboard!');
                            }}
                        >
                            📋 Copy
                        </button>
                        <button 
                            className="schedule-btn"
                            disabled
                            title="Calendar integration coming soon - use Social Calendar page for scheduling"
                            onClick={() => {
                                // FIXME: Calendar integration not implemented
                                // To implement:
                                // 1. Open modal with date/time picker
                                // 2. Call POST /api/scheduled-posts with content and scheduled_at
                                // 3. Show confirmation with link to Social Calendar
                                alert('Calendar integration not yet available. Please use the Social Calendar page to schedule content.');
                            }}
                        >
                            📅 Schedule (Coming Soon)
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="article-writer-page">
            <header className="article-header">
                <div className="header-left">
                    {onBack && (
                        <button className="back-button" onClick={onBack}>
                            ← Back
                        </button>
                    )}
                    <h1>Article Writer</h1>
                    <p className="subtitle">Turn interviews into multiple content formats</p>
                </div>
            </header>

            <div className="progress-bar">
                {[1, 2, 3].map((s) => (
                    <div 
                        key={s} 
                        className={`progress-step ${s === step ? 'active' : ''} ${s < step ? 'completed' : ''}`}
                    >
                        {s < step ? '✓' : s}
                    </div>
                ))}
            </div>

            {error && (
                <div className="error-banner">
                    <span>{error}</span>
                    <button onClick={() => setError(null)}>✕</button>
                </div>
            )}

            <div className="article-content">
                {step === 1 && renderStep1()}
                {step === 2 && renderStep2()}
                {step === 3 && renderStep3()}
            </div>

            <div className="article-footer">
                {step > 1 && (
                    <button className="back-btn" onClick={() => setStep(step - 1)}>
                        ← Back
                    </button>
                )}
                
                {step < 3 ? (
                    <button 
                        className="next-btn"
                        onClick={step === 1 ? handleProcessInterview : handleGenerateContent}
                        disabled={loading || (step === 2 && selectedFormats.length === 0)}
                    >
                        {loading ? (
                            <>
                                <span className="spinner-small"></span>
                                Processing...
                            </>
                        ) : (
                            step === 1 ? 'Analyze Interview →' : 'Generate Content →'
                        )}
                    </button>
                ) : (
                    <button 
                        className="restart-btn"
                        onClick={() => {
                            setStep(1);
                            setInterviewTitle('');
                            setInterviewText('');
                            setProcessedInterview(null);
                            setGeneratedContent(null);
                        }}
                    >
                        🔄 Start New Interview
                    </button>
                )}
            </div>
        </div>
    );
};

export default ArticleWriterPage;