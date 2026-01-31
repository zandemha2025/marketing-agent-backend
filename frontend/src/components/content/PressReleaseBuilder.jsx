import React, { useState, useCallback } from 'react';
import api from '../../services/api';
import './PressReleaseBuilder.css';

/**
 * Press Release Builder Component
 * 
 * Features:
 * - Step-by-step PR creation wizard
 * - AI-generated content from bullet points
 * - Multiple headline variants for A/B testing
 * - Quote generation with executive attribution
 * - Preview in standard PR format (HTML/Text)
 * - Brand voice integration
 */

const PressReleaseBuilder = ({ organizationId, onSave, onClose }) => {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // Form state
    const [topic, setTopic] = useState('');
    const [keyPoints, setKeyPoints] = useState(['']);
    const [executiveName, setExecutiveName] = useState('');
    const [executiveTitle, setExecutiveTitle] = useState('');
    const [targetAudience, setTargetAudience] = useState('');
    const [tone, setTone] = useState('professional');
    
    // Generated content
    const [generatedPR, setGeneratedPR] = useState(null);
    const [headlineVariants, setHeadlineVariants] = useState([]);
    const [selectedHeadline, setSelectedHeadline] = useState(0);
    const [previewMode, setPreviewMode] = useState('formatted'); // 'formatted', 'html', 'text'

    const totalSteps = 3;

    const handleAddKeyPoint = () => {
        setKeyPoints([...keyPoints, '']);
    };

    const handleRemoveKeyPoint = (index) => {
        if (keyPoints.length > 1) {
            setKeyPoints(keyPoints.filter((_, i) => i !== index));
        }
    };

    const handleKeyPointChange = (index, value) => {
        const newPoints = [...keyPoints];
        newPoints[index] = value;
        setKeyPoints(newPoints);
    };

    const handleGenerate = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const validPoints = keyPoints.filter(p => p.trim());
            
            const result = await api.generatePressRelease(organizationId, {
                topic,
                key_points: validPoints,
                executive_name: executiveName || undefined,
                executive_title: executiveTitle || undefined,
                target_audience: targetAudience || undefined,
                tone
            });
            
            setGeneratedPR(result);
            
            // Generate headline variants
            const headlineResult = await api.generateHeadlineVariants(organizationId, {
                topic,
                key_point: validPoints[0] || topic,
                count: 5
            });
            
            setHeadlineVariants(headlineResult.headlines || []);
            setStep(3);
        } catch (err) {
            setError(err.message || 'Failed to generate press release');
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateQuote = async () => {
        if (!executiveName || !generatedPR) return;
        
        setLoading(true);
        try {
            const result = await api.generateQuote(organizationId, {
                topic,
                angle: 'general',
                executive_name: executiveName,
                executive_title: executiveTitle || 'Executive'
            });
            
            // Update the generated PR with new quote
            setGeneratedPR({
                ...generatedPR,
                quotes: [...generatedPR.quotes, result]
            });
        } catch (err) {
            setError(err.message || 'Failed to generate quote');
        } finally {
            setLoading(false);
        }
    };

    const handleNext = () => {
        if (step < totalSteps) {
            if (step === 2) {
                handleGenerate();
            } else {
                setStep(step + 1);
            }
        }
    };

    const handleBack = () => {
        if (step > 1) {
            setStep(step - 1);
        }
    };

    const canProceed = () => {
        switch (step) {
            case 1:
                return topic.trim().length > 0;
            case 2:
                return keyPoints.some(p => p.trim().length > 0);
            default:
                return true;
        }
    };

    const renderStep1 = () => (
        <div className="pr-step">
            <h3>Step 1: What's the News?</h3>
            <p className="step-description">Start with the main topic or announcement.</p>
            
            <div className="form-group">
                <label>Topic / Announcement *</label>
                <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g., Launch of new AI-powered marketing platform"
                />
            </div>

            <div className="form-group">
                <label>Tone</label>
                <select value={tone} onChange={(e) => setTone(e.target.value)}>
                    <option value="professional">Professional</option>
                    <option value="excited">Excited</option>
                    <option value="serious">Serious</option>
                    <option value="conversational">Conversational</option>
                </select>
            </div>

            <div className="form-group">
                <label>Target Audience</label>
                <input
                    type="text"
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    placeholder="e.g., Enterprise marketing teams, tech journalists"
                />
            </div>
        </div>
    );

    const renderStep2 = () => (
        <div className="pr-step">
            <h3>Step 2: Key Points</h3>
            <p className="step-description">Add bullet points with the key information to include.</p>
            
            <div className="key-points-list">
                {keyPoints.map((point, index) => (
                    <div key={index} className="key-point-item">
                        <input
                            type="text"
                            value={point}
                            onChange={(e) => handleKeyPointChange(index, e.target.value)}
                            placeholder={`Key point ${index + 1}`}
                        />
                        {keyPoints.length > 1 && (
                            <button 
                                className="remove-btn"
                                onClick={() => handleRemoveKeyPoint(index)}
                            >
                                ✕
                            </button>
                        )}
                    </div>
                ))}
            </div>
            
            <button className="add-point-btn" onClick={handleAddKeyPoint}>
                + Add Key Point
            </button>

            <div className="form-row">
                <div className="form-group">
                    <label>Executive Name (for quotes)</label>
                    <input
                        type="text"
                        value={executiveName}
                        onChange={(e) => setExecutiveName(e.target.value)}
                        placeholder="e.g., Jane Smith"
                    />
                </div>
                <div className="form-group">
                    <label>Executive Title</label>
                    <input
                        type="text"
                        value={executiveTitle}
                        onChange={(e) => setExecutiveTitle(e.target.value)}
                        placeholder="e.g., CEO"
                    />
                </div>
            </div>
        </div>
    );

    const renderStep3 = () => {
        if (!generatedPR) return null;

        const displayHeadline = selectedHeadline === 0 
            ? generatedPR.headline 
            : headlineVariants[selectedHeadline - 1];

        return (
            <div className="pr-step">
                <h3>Step 3: Review & Edit</h3>
                
                {headlineVariants.length > 0 && (
                    <div className="headline-variants">
                        <label>Choose Headline:</label>
                        <div className="variant-list">
                            <button
                                className={`variant-btn ${selectedHeadline === 0 ? 'selected' : ''}`}
                                onClick={() => setSelectedHeadline(0)}
                            >
                                {generatedPR.headline}
                            </button>
                            {headlineVariants.map((variant, index) => (
                                <button
                                    key={index}
                                    className={`variant-btn ${selectedHeadline === index + 1 ? 'selected' : ''}`}
                                    onClick={() => setSelectedHeadline(index + 1)}
                                >
                                    {variant}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                <div className="preview-tabs">
                    <button 
                        className={previewMode === 'formatted' ? 'active' : ''}
                        onClick={() => setPreviewMode('formatted')}
                    >
                        Formatted
                    </button>
                    <button 
                        className={previewMode === 'html' ? 'active' : ''}
                        onClick={() => setPreviewMode('html')}
                    >
                        HTML
                    </button>
                    <button 
                        className={previewMode === 'text' ? 'active' : ''}
                        onClick={() => setPreviewMode('text')}
                    >
                        Plain Text
                    </button>
                </div>

                <div className="pr-preview">
                    {previewMode === 'formatted' && (
                        <div className="formatted-preview">
                            <h1 className="pr-headline">{displayHeadline}</h1>
                            {generatedPR.subheadline && (
                                <h2 className="pr-subheadline">{generatedPR.subheadline}</h2>
                            )}
                            <p className="pr-dateline">{generatedPR.dateline}</p>
                            <p className="pr-lead">{generatedPR.lead}</p>
                            {generatedPR.body.map((para, i) => (
                                <p key={i} className="pr-body">{para}</p>
                            ))}
                            {generatedPR.quotes.map((quote, i) => (
                                <blockquote key={i} className="pr-quote">
                                    <p>"{quote.text}"</p>
                                    <footer>— {quote.attribution}</footer>
                                </blockquote>
                            ))}
                            <div className="pr-boilerplate">
                                <h4>About</h4>
                                <p>{generatedPR.boilerplate}</p>
                            </div>
                            {generatedPR.contact_info && (
                                <div className="pr-contact">
                                    <h4>Media Contact</h4>
                                    <p>{generatedPR.contact_info.name}</p>
                                    <p>{generatedPR.contact_info.email}</p>
                                    <p>{generatedPR.contact_info.phone}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {previewMode === 'html' && (
                        <div className="html-preview">
                            <textarea 
                                readOnly 
                                value={generatedPR.html}
                                rows={20}
                            />
                        </div>
                    )}

                    {previewMode === 'text' && (
                        <div className="text-preview">
                            <textarea 
                                readOnly 
                                value={generatedPR.plaintext}
                                rows={20}
                            />
                        </div>
                    )}
                </div>

                <div className="pr-stats">
                    <span>Word Count: {generatedPR.word_count}</span>
                    <button 
                        className="generate-quote-btn"
                        onClick={handleGenerateQuote}
                        disabled={loading || !executiveName}
                    >
                        {loading ? 'Generating...' : '+ Generate Another Quote'}
                    </button>
                </div>
            </div>
        );
    };

    return (
        <div className="press-release-builder">
            <div className="builder-header">
                <h2>Press Release Builder</h2>
                {onClose && (
                    <button className="close-btn" onClick={onClose}>✕</button>
                )}
            </div>

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
                <div className="error-message">
                    {error}
                    <button onClick={() => setError(null)}>✕</button>
                </div>
            )}

            <div className="builder-content">
                {step === 1 && renderStep1()}
                {step === 2 && renderStep2()}
                {step === 3 && renderStep3()}
            </div>

            <div className="builder-footer">
                {step > 1 && (
                    <button className="back-btn" onClick={handleBack}>
                        ← Back
                    </button>
                )}
                
                {step < totalSteps ? (
                    <button 
                        className="next-btn"
                        onClick={handleNext}
                        disabled={!canProceed() || loading}
                    >
                        {loading && step === 2 ? 'Generating...' : 'Next →'}
                    </button>
                ) : (
                    <div className="action-buttons">
                        <button 
                            className="copy-btn"
                            onClick={() => {
                                navigator.clipboard.writeText(generatedPR.plaintext);
                                alert('Press release copied to clipboard!');
                            }}
                        >
                            📋 Copy Text
                        </button>
                        {onSave && (
                            <button 
                                className="save-btn"
                                onClick={() => onSave(generatedPR)}
                            >
                                💾 Save
                            </button>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PressReleaseBuilder;