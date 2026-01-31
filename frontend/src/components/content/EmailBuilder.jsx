import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import './EmailBuilder.css';

/**
 * Email Builder Component
 * 
 * Features:
 * - MJML-based templates for cross-email-client compatibility
 * - AI-generated content matching brand voice
 * - Email types: Promotional, Newsletter, Welcome, Announcement, Nurture
 * - Output: HTML, MJML source, plaintext
 * - Subject line generator with A/B testing variants
 */

const EMAIL_TYPES = [
    { id: 'welcome', name: 'Welcome Email', description: 'Welcome new subscribers or customers' },
    { id: 'newsletter', name: 'Newsletter', description: 'Regular newsletter with multiple sections' },
    { id: 'promotional', name: 'Promotional', description: 'Sales and promotional offers' },
    { id: 'announcement', name: 'Announcement', description: 'Product launches and company news' },
    { id: 'nurture', name: 'Nurture Sequence', description: 'Educational and relationship building' },
];

const EmailBuilder = ({ organizationId, onSave, onClose }) => {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // Form state
    const [emailType, setEmailType] = useState('newsletter');
    const [topic, setTopic] = useState('');
    const [keyPoints, setKeyPoints] = useState(['']);
    const [targetAudience, setTargetAudience] = useState('');
    const [tone, setTone] = useState('professional');
    
    // Generated content
    const [generatedEmail, setGeneratedEmail] = useState(null);
    const [subjectVariants, setSubjectVariants] = useState([]);
    const [selectedSubject, setSelectedSubject] = useState(0);
    const [previewMode, setPreviewMode] = useState('html'); // 'html', 'mjml', 'text'

    const totalSteps = 3;

    useEffect(() => {
        // Load templates on mount
        loadTemplates();
    }, []);

    const loadTemplates = async () => {
        try {
            await api.getEmailTemplates();
        } catch (err) {
            console.error('Failed to load templates:', err);
        }
    };

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
            
            // Generate email
            const result = await api.generateEmail(organizationId, {
                email_type: emailType,
                topic,
                key_points: validPoints,
                target_audience: targetAudience || undefined,
                tone
            });
            
            setGeneratedEmail(result);
            
            // Generate subject variants
            const variantResult = await api.generateSubjectVariants(organizationId, {
                topic,
                count: 5
            });
            
            setSubjectVariants(variantResult);
            setStep(3);
        } catch (err) {
            setError(err.message || 'Failed to generate email');
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
                return emailType && topic.trim().length > 0;
            case 2:
                return keyPoints.some(p => p.trim().length > 0);
            default:
                return true;
        }
    };

    const renderStep1 = () => (
        <div className="email-step">
            <h3>Step 1: Choose Email Type</h3>
            <p className="step-description">Select the type of email you want to create.</p>
            
            <div className="email-types">
                {EMAIL_TYPES.map(type => (
                    <label 
                        key={type.id} 
                        className={`email-type-card ${emailType === type.id ? 'selected' : ''}`}
                    >
                        <input
                            type="radio"
                            name="emailType"
                            value={type.id}
                            checked={emailType === type.id}
                            onChange={(e) => setEmailType(e.target.value)}
                        />
                        <div className="type-info">
                            <span className="type-name">{type.name}</span>
                            <span className="type-desc">{type.description}</span>
                        </div>
                    </label>
                ))}
            </div>

            <div className="form-group">
                <label>Email Topic *</label>
                <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g., January Newsletter, Product Launch Announcement"
                />
            </div>

            <div className="form-group">
                <label>Tone</label>
                <select value={tone} onChange={(e) => setTone(e.target.value)}>
                    <option value="professional">Professional</option>
                    <option value="casual">Casual</option>
                    <option value="enthusiastic">Enthusiastic</option>
                    <option value="formal">Formal</option>
                </select>
            </div>

            <div className="form-group">
                <label>Target Audience</label>
                <input
                    type="text"
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    placeholder="e.g., Enterprise customers, New subscribers"
                />
            </div>
        </div>
    );

    const renderStep2 = () => (
        <div className="email-step">
            <h3>Step 2: Key Points</h3>
            <p className="step-description">Add the key points you want to include in the email.</p>
            
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
        </div>
    );

    const renderStep3 = () => {
        if (!generatedEmail) return null;

        const currentSubject = selectedSubject === 0 
            ? generatedEmail.subject 
            : subjectVariants[selectedSubject - 1]?.text;

        return (
            <div className="email-step">
                <h3>Step 3: Review & Export</h3>
                
                {subjectVariants.length > 0 && (
                    <div className="subject-variants">
                        <label>Choose Subject Line:</label>
                        <div className="variant-list">
                            <button
                                className={`variant-btn ${selectedSubject === 0 ? 'selected' : ''}`}
                                onClick={() => setSelectedSubject(0)}
                            >
                                <span className="variant-text">{generatedEmail.subject}</span>
                                <span className="variant-meta">AI Generated</span>
                            </button>
                            {subjectVariants.map((variant, index) => (
                                <button
                                    key={index}
                                    className={`variant-btn ${selectedSubject === index + 1 ? 'selected' : ''}`}
                                    onClick={() => setSelectedSubject(index + 1)}
                                >
                                    <span className="variant-text">{variant.text}</span>
                                    <span className="variant-meta">
                                        {variant.predicted_open_rate > 0 && `${variant.predicted_open_rate}% open rate`}
                                        {variant.emoji && ' • Emoji'}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                <div className="preview-tabs">
                    <button 
                        className={previewMode === 'html' ? 'active' : ''}
                        onClick={() => setPreviewMode('html')}
                    >
                        HTML Preview
                    </button>
                    <button 
                        className={previewMode === 'mjml' ? 'active' : ''}
                        onClick={() => setPreviewMode('mjml')}
                    >
                        MJML Source
                    </button>
                    <button 
                        className={previewMode === 'text' ? 'active' : ''}
                        onClick={() => setPreviewMode('text')}
                    >
                        Plain Text
                    </button>
                </div>

                <div className="email-preview">
                    {previewMode === 'html' && (
                        <iframe
                            srcDoc={generatedEmail.html}
                            title="Email Preview"
                            className="html-preview-frame"
                        />
                    )}

                    {previewMode === 'mjml' && (
                        <textarea 
                            readOnly 
                            value={generatedEmail.mjml}
                            className="code-preview"
                            rows={20}
                        />
                    )}

                    {previewMode === 'text' && (
                        <textarea 
                            readOnly 
                            value={generatedEmail.plaintext}
                            className="text-preview"
                            rows={20}
                        />
                    )}
                </div>

                <div className="email-stats">
                    <span>Subject: {currentSubject?.length || 0} chars</span>
                    <span>HTML: {generatedEmail.html?.length || 0} chars</span>
                    <span>Text: {generatedEmail.plaintext?.length || 0} chars</span>
                </div>
            </div>
        );
    };

    return (
        <div className="email-builder">
            <div className="builder-header">
                <h2>Email Builder</h2>
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
                                const content = previewMode === 'html' 
                                    ? generatedEmail.html 
                                    : previewMode === 'mjml' 
                                        ? generatedEmail.mjml 
                                        : generatedEmail.plaintext;
                                navigator.clipboard.writeText(content);
                                alert(`${previewMode.toUpperCase()} copied to clipboard!`);
                            }}
                        >
                            📋 Copy {previewMode.toUpperCase()}
                        </button>
                        {onSave && (
                            <button 
                                className="save-btn"
                                onClick={() => onSave({
                                    ...generatedEmail,
                                    subject: selectedSubject === 0 
                                        ? generatedEmail.subject 
                                        : subjectVariants[selectedSubject - 1]?.text
                                })}
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

export default EmailBuilder;