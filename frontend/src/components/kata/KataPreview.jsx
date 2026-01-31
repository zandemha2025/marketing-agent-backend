import React, { useState } from 'react';

function KataPreview({ job, content, onReset }) {
    const [activeTab, setActiveTab] = useState('preview');

    // No job yet - show intro
    if (!job && !content) {
        return (
            <div className="kata-preview empty">
                <div className="preview-placeholder">
                    <span className="preview-icon">🎬</span>
                    <h3>Your Creation Will Appear Here</h3>
                    <p>
                        Configure your settings on the left and click generate to create
                        stunning AI-powered content.
                    </p>
                    <div className="feature-highlights">
                        <div className="feature">
                            <span>👤</span>
                            <span>Synthetic Influencers</span>
                        </div>
                        <div className="feature">
                            <span>🎬</span>
                            <span>Video Compositing</span>
                        </div>
                        <div className="feature">
                            <span>📝</span>
                            <span>AI Scripts</span>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Script-only content
    if (content?.script && !job) {
        return (
            <div className="kata-preview script-preview">
                <div className="preview-header">
                    <h3>📝 Generated Script</h3>
                </div>
                <div className="script-display">
                    <pre>{content.script}</pre>
                </div>
                <div className="script-actions">
                    <button className="btn-secondary" onClick={onReset}>
                        Create Another
                    </button>
                    <button
                        className="btn-primary"
                        onClick={() => navigator.clipboard.writeText(content.script)}
                    >
                        📋 Copy Script
                    </button>
                </div>
            </div>
        );
    }

    // Job is processing
    if (job && job.status === 'processing') {
        return (
            <div className="kata-preview processing">
                <div className="processing-animation">
                    <div className="processing-ring">
                        <div className="ring-segment"></div>
                        <div className="ring-segment"></div>
                        <div className="ring-segment"></div>
                    </div>
                    <span className="processing-icon">🎬</span>
                </div>
                <h3>Creating Your Content...</h3>
                <p className="processing-stage">{job.current_stage || 'Initializing...'}</p>
                <div className="progress-bar">
                    <div
                        className="progress-fill"
                        style={{ width: `${(job.progress || 0) * 100}%` }}
                    />
                </div>
                <span className="progress-percent">{Math.round((job.progress || 0) * 100)}%</span>

                <div className="processing-steps">
                    <div className={`step ${job.progress >= 0.1 ? 'active' : ''} ${job.progress >= 0.2 ? 'completed' : ''}`}>
                        <span className="step-icon">🔍</span>
                        <span>Analyzing inputs</span>
                    </div>
                    <div className={`step ${job.progress >= 0.3 ? 'active' : ''} ${job.progress >= 0.5 ? 'completed' : ''}`}>
                        <span className="step-icon">🎙️</span>
                        <span>Generating voice</span>
                    </div>
                    <div className={`step ${job.progress >= 0.5 ? 'active' : ''} ${job.progress >= 0.7 ? 'completed' : ''}`}>
                        <span className="step-icon">👤</span>
                        <span>Creating influencer</span>
                    </div>
                    <div className={`step ${job.progress >= 0.7 ? 'active' : ''} ${job.progress >= 0.9 ? 'completed' : ''}`}>
                        <span className="step-icon">🎨</span>
                        <span>Compositing</span>
                    </div>
                    <div className={`step ${job.progress >= 0.9 ? 'active' : ''} ${job.progress >= 1 ? 'completed' : ''}`}>
                        <span className="step-icon">✨</span>
                        <span>Final polish</span>
                    </div>
                </div>

                <button className="btn-cancel" onClick={onReset}>
                    Cancel
                </button>
            </div>
        );
    }

    // Job failed
    if (job && job.status === 'failed') {
        return (
            <div className="kata-preview failed">
                <div className="error-display">
                    <span className="error-icon">❌</span>
                    <h3>Generation Failed</h3>
                    <p>{job.error || 'An unexpected error occurred'}</p>
                </div>
                <div className="error-actions">
                    <button className="btn-primary" onClick={onReset}>
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    // Job completed - show results
    if (job && job.status === 'completed' && content) {
        return (
            <div className="kata-preview completed">
                <div className="preview-tabs">
                    <button
                        className={`tab ${activeTab === 'preview' ? 'active' : ''}`}
                        onClick={() => setActiveTab('preview')}
                    >
                        Preview
                    </button>
                    <button
                        className={`tab ${activeTab === 'details' ? 'active' : ''}`}
                        onClick={() => setActiveTab('details')}
                    >
                        Details
                    </button>
                    <button
                        className={`tab ${activeTab === 'quality' ? 'active' : ''}`}
                        onClick={() => setActiveTab('quality')}
                    >
                        Quality
                    </button>
                </div>

                {activeTab === 'preview' && (
                    <div className="preview-content">
                        {content.video_path ? (
                            <div className="video-player">
                                <video
                                    src={content.video_path}
                                    controls
                                    autoPlay
                                    loop
                                    muted
                                />
                            </div>
                        ) : content.audio_path ? (
                            <div className="audio-player">
                                <span className="audio-icon">🎙️</span>
                                <audio src={content.audio_path} controls />
                            </div>
                        ) : (
                            <div className="no-preview">
                                <span>Preview not available</span>
                            </div>
                        )}

                        <div className="preview-actions">
                            <button className="btn-secondary" onClick={onReset}>
                                Create Another
                            </button>
                            <button className="btn-secondary">
                                ✏️ Edit
                            </button>
                            <button className="btn-primary">
                                ⬇️ Download
                            </button>
                        </div>

                        <div className="quick-publish">
                            <h4>Quick Publish</h4>
                            <div className="publish-buttons">
                                <button className="publish-btn tiktok">
                                    <span>🎵</span> TikTok
                                </button>
                                <button className="publish-btn instagram">
                                    <span>📸</span> Instagram
                                </button>
                                <button className="publish-btn youtube">
                                    <span>📺</span> YouTube
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'details' && (
                    <div className="details-content">
                        <div className="detail-section">
                            <h4>Output Information</h4>
                            <div className="detail-grid">
                                <div className="detail-item">
                                    <span className="label">Duration</span>
                                    <span className="value">{content.duration || 'N/A'}s</span>
                                </div>
                                <div className="detail-item">
                                    <span className="label">Resolution</span>
                                    <span className="value">{content.resolution || '1080x1920'}</span>
                                </div>
                                <div className="detail-item">
                                    <span className="label">Format</span>
                                    <span className="value">{content.format || 'MP4'}</span>
                                </div>
                                <div className="detail-item">
                                    <span className="label">File Size</span>
                                    <span className="value">{content.file_size || 'N/A'}</span>
                                </div>
                            </div>
                        </div>

                        {content.influencer && (
                            <div className="detail-section">
                                <h4>Influencer Details</h4>
                                <div className="detail-grid">
                                    <div className="detail-item">
                                        <span className="label">Style</span>
                                        <span className="value">{content.influencer.style}</span>
                                    </div>
                                    <div className="detail-item">
                                        <span className="label">Voice</span>
                                        <span className="value">{content.influencer.voice}</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="detail-section">
                            <h4>Generation Stats</h4>
                            <div className="detail-grid">
                                <div className="detail-item">
                                    <span className="label">Processing Time</span>
                                    <span className="value">{job.processing_time || 'N/A'}</span>
                                </div>
                                <div className="detail-item">
                                    <span className="label">Job ID</span>
                                    <span className="value mono">{job.job_id}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'quality' && (
                    <div className="quality-content">
                        <div className="quality-scores">
                            <div className="quality-score">
                                <div className="score-ring">
                                    <svg viewBox="0 0 36 36">
                                        <path
                                            d="M18 2.0845
                                                a 15.9155 15.9155 0 0 1 0 31.831
                                                a 15.9155 15.9155 0 0 1 0 -31.831"
                                            fill="none"
                                            stroke="#e0e0e0"
                                            strokeWidth="3"
                                        />
                                        <path
                                            d="M18 2.0845
                                                a 15.9155 15.9155 0 0 1 0 31.831
                                                a 15.9155 15.9155 0 0 1 0 -31.831"
                                            fill="none"
                                            stroke="#10b981"
                                            strokeWidth="3"
                                            strokeDasharray={`${(content.quality?.realism || 0.85) * 100}, 100`}
                                        />
                                    </svg>
                                    <span className="score-value">
                                        {Math.round((content.quality?.realism || 0.85) * 100)}
                                    </span>
                                </div>
                                <span className="score-label">Realism</span>
                            </div>

                            <div className="quality-score">
                                <div className="score-ring">
                                    <svg viewBox="0 0 36 36">
                                        <path
                                            d="M18 2.0845
                                                a 15.9155 15.9155 0 0 1 0 31.831
                                                a 15.9155 15.9155 0 0 1 0 -31.831"
                                            fill="none"
                                            stroke="#e0e0e0"
                                            strokeWidth="3"
                                        />
                                        <path
                                            d="M18 2.0845
                                                a 15.9155 15.9155 0 0 1 0 31.831
                                                a 15.9155 15.9155 0 0 1 0 -31.831"
                                            fill="none"
                                            stroke="#3b82f6"
                                            strokeWidth="3"
                                            strokeDasharray={`${(content.quality?.brand_safety || 0.95) * 100}, 100`}
                                        />
                                    </svg>
                                    <span className="score-value">
                                        {Math.round((content.quality?.brand_safety || 0.95) * 100)}
                                    </span>
                                </div>
                                <span className="score-label">Brand Safety</span>
                            </div>

                            <div className="quality-score">
                                <div className="score-ring">
                                    <svg viewBox="0 0 36 36">
                                        <path
                                            d="M18 2.0845
                                                a 15.9155 15.9155 0 0 1 0 31.831
                                                a 15.9155 15.9155 0 0 1 0 -31.831"
                                            fill="none"
                                            stroke="#e0e0e0"
                                            strokeWidth="3"
                                        />
                                        <path
                                            d="M18 2.0845
                                                a 15.9155 15.9155 0 0 1 0 31.831
                                                a 15.9155 15.9155 0 0 1 0 -31.831"
                                            fill="none"
                                            stroke="#8b5cf6"
                                            strokeWidth="3"
                                            strokeDasharray={`${(content.quality?.engagement_potential || 0.78) * 100}, 100`}
                                        />
                                    </svg>
                                    <span className="score-value">
                                        {Math.round((content.quality?.engagement_potential || 0.78) * 100)}
                                    </span>
                                </div>
                                <span className="score-label">Engagement</span>
                            </div>
                        </div>

                        <div className="quality-breakdown">
                            <h4>Quality Breakdown</h4>
                            <div className="breakdown-items">
                                <div className="breakdown-item">
                                    <span className="item-label">Visual Quality</span>
                                    <div className="item-bar">
                                        <div className="bar-fill" style={{ width: '88%' }}></div>
                                    </div>
                                    <span className="item-value">88%</span>
                                </div>
                                <div className="breakdown-item">
                                    <span className="item-label">Audio Clarity</span>
                                    <div className="item-bar">
                                        <div className="bar-fill" style={{ width: '92%' }}></div>
                                    </div>
                                    <span className="item-value">92%</span>
                                </div>
                                <div className="breakdown-item">
                                    <span className="item-label">Lip Sync</span>
                                    <div className="item-bar">
                                        <div className="bar-fill" style={{ width: '85%' }}></div>
                                    </div>
                                    <span className="item-value">85%</span>
                                </div>
                                <div className="breakdown-item">
                                    <span className="item-label">Product Visibility</span>
                                    <div className="item-bar">
                                        <div className="bar-fill" style={{ width: '90%' }}></div>
                                    </div>
                                    <span className="item-value">90%</span>
                                </div>
                            </div>
                        </div>

                        <div className="quality-recommendation">
                            <span className="rec-icon">✅</span>
                            <span>This content meets quality standards and is ready for publishing.</span>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    return null;
}

export default KataPreview;
