import React, { useState, useRef } from 'react';
import api from '../../services/api';

function SyntheticInfluencerCreator({ organizationId, onJobCreated, disabled }) {
    const [step, setStep] = useState(1); // 1: Upload, 2: Script, 3: Style, 4: Generate
    const [productImages, setProductImages] = useState([]);
    const [productDescription, setProductDescription] = useState('');
    const [script, setScript] = useState('');
    const [scriptMode, setScriptMode] = useState('assisted'); // assisted, manual
    const [assistedAnswers, setAssistedAnswers] = useState({});
    const [influencerStyle, setInfluencerStyle] = useState('casual');
    const [voiceStyle, setVoiceStyle] = useState('friendly');
    const [voiceGender, setVoiceGender] = useState('female');
    const [targetPlatform, setTargetPlatform] = useState('tiktok');
    const [isGenerating, setIsGenerating] = useState(false);
    const fileInputRef = useRef(null);

    const influencerStyles = [
        { id: 'casual', name: 'Casual Creator', desc: 'Relatable, everyday vibe' },
        { id: 'professional', name: 'Professional', desc: 'Polished, expert feel' },
        { id: 'energetic', name: 'Energetic', desc: 'High energy, exciting' },
        { id: 'luxury', name: 'Luxury', desc: 'Premium, aspirational' },
        { id: 'ugc', name: 'UGC Style', desc: 'Authentic, user-generated feel' }
    ];

    const voiceStyles = [
        { id: 'friendly', name: 'Friendly' },
        { id: 'professional', name: 'Professional' },
        { id: 'energetic', name: 'Energetic' },
        { id: 'calm', name: 'Calm' },
        { id: 'authoritative', name: 'Authoritative' }
    ];

    const platforms = [
        { id: 'tiktok', name: 'TikTok', icon: '🎵' },
        { id: 'instagram', name: 'Instagram Reels', icon: '📸' },
        { id: 'youtube', name: 'YouTube Shorts', icon: '📺' },
        { id: 'linkedin', name: 'LinkedIn', icon: '💼' }
    ];

    // AI-Assisted Script Questions
    const scriptQuestions = [
        {
            id: 'hook',
            question: 'What\'s the main hook or attention-grabber?',
            placeholder: 'e.g., "Did you know 90% of people do this wrong?"'
        },
        {
            id: 'problem',
            question: 'What problem does your product solve?',
            placeholder: 'e.g., "Tired of tangled headphones?"'
        },
        {
            id: 'solution',
            question: 'How does your product solve it?',
            placeholder: 'e.g., "These wireless earbuds never tangle and last 12 hours"'
        },
        {
            id: 'proof',
            question: 'Any proof points or testimonials?',
            placeholder: 'e.g., "Over 50,000 happy customers"'
        },
        {
            id: 'cta',
            question: 'What\'s the call to action?',
            placeholder: 'e.g., "Link in bio for 20% off!"'
        }
    ];

    const handleImageUpload = (e) => {
        const files = Array.from(e.target.files);
        const newImages = files.map(file => ({
            file,
            preview: URL.createObjectURL(file),
            name: file.name
        }));
        setProductImages([...productImages, ...newImages]);
    };

    const removeImage = (index) => {
        const updated = [...productImages];
        URL.revokeObjectURL(updated[index].preview);
        updated.splice(index, 1);
        setProductImages(updated);
    };

    const generateScriptFromAnswers = async () => {
        // In production, this would call an AI endpoint
        const { hook, problem, solution, proof, cta } = assistedAnswers;

        let generatedScript = '';
        if (hook) generatedScript += `${hook}\n\n`;
        if (problem) generatedScript += `${problem}\n\n`;
        if (solution) generatedScript += `Here's the thing... ${solution}\n\n`;
        if (proof) generatedScript += `And ${proof}.\n\n`;
        if (cta) generatedScript += `${cta}`;

        setScript(generatedScript.trim());
        setStep(3);
    };

    const handleGenerate = async () => {
        setIsGenerating(true);

        try {
            // Upload images first to get URLs
            const uploadedImageUrls = [];
            for (const img of productImages) {
                const uploadResult = await api.uploadImage(img.file);
                uploadedImageUrls.push(uploadResult.url);
            }

            // Then create the synthetic influencer job
            const data = await api.createSyntheticInfluencer({
                product_images: uploadedImageUrls,
                product_description: productDescription,
                script: script,
                influencer_style: influencerStyle,
                target_platform: targetPlatform,
                voice_style: voiceStyle,
                voice_gender: voiceGender
            });

            onJobCreated(data);
        } catch (error) {
            console.error('Error creating synthetic influencer:', error);
            // Show error to user
            alert(`Failed to create synthetic influencer: ${error.message}`);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="synthetic-creator">
            {/* Progress Steps */}
            <div className="creator-steps">
                {['Product', 'Script', 'Style', 'Generate'].map((name, i) => (
                    <div
                        key={i}
                        className={`step ${step > i ? 'completed' : ''} ${step === i + 1 ? 'active' : ''}`}
                        onClick={() => step > i && setStep(i + 1)}
                    >
                        <span className="step-number">{i + 1}</span>
                        <span className="step-name">{name}</span>
                    </div>
                ))}
            </div>

            {/* Step 1: Product Upload */}
            {step === 1 && (
                <div className="step-content">
                    <h3>Upload Your Product</h3>
                    <p>Add images of the product your AI influencer will showcase</p>

                    <div
                        className="upload-zone"
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            multiple
                            onChange={handleImageUpload}
                            style={{ display: 'none' }}
                        />
                        <span className="upload-icon">📷</span>
                        <span>Click to upload product images</span>
                        <span className="upload-hint">PNG, JPG up to 10MB</span>
                    </div>

                    {productImages.length > 0 && (
                        <div className="uploaded-images">
                            {productImages.map((img, i) => (
                                <div key={i} className="image-preview">
                                    <img src={img.preview} alt={img.name} />
                                    <button
                                        className="remove-btn"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            removeImage(i);
                                        }}
                                    >
                                        ×
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="form-group">
                        <label>Product Description</label>
                        <textarea
                            value={productDescription}
                            onChange={(e) => setProductDescription(e.target.value)}
                            placeholder="Briefly describe your product, its key features, and target audience..."
                            rows={3}
                        />
                    </div>

                    <button
                        className="btn-primary"
                        onClick={() => setStep(2)}
                        disabled={productImages.length === 0 || !productDescription}
                    >
                        Continue to Script →
                    </button>
                </div>
            )}

            {/* Step 2: Script */}
            {step === 2 && (
                <div className="step-content">
                    <h3>Create Your Script</h3>

                    <div className="script-mode-toggle">
                        <button
                            className={scriptMode === 'assisted' ? 'active' : ''}
                            onClick={() => setScriptMode('assisted')}
                        >
                            🤖 AI-Assisted
                        </button>
                        <button
                            className={scriptMode === 'manual' ? 'active' : ''}
                            onClick={() => setScriptMode('manual')}
                        >
                            ✍️ Write Manually
                        </button>
                    </div>

                    {scriptMode === 'assisted' ? (
                        <div className="assisted-script">
                            <p className="helper-text">
                                Answer these questions and we'll craft the perfect script
                            </p>
                            {scriptQuestions.map((q) => (
                                <div key={q.id} className="form-group">
                                    <label>{q.question}</label>
                                    <input
                                        type="text"
                                        placeholder={q.placeholder}
                                        value={assistedAnswers[q.id] || ''}
                                        onChange={(e) => setAssistedAnswers({
                                            ...assistedAnswers,
                                            [q.id]: e.target.value
                                        })}
                                    />
                                </div>
                            ))}
                            <button
                                className="btn-primary"
                                onClick={generateScriptFromAnswers}
                                disabled={!assistedAnswers.hook || !assistedAnswers.solution}
                            >
                                Generate Script →
                            </button>
                        </div>
                    ) : (
                        <div className="manual-script">
                            <div className="form-group">
                                <label>Script</label>
                                <textarea
                                    value={script}
                                    onChange={(e) => setScript(e.target.value)}
                                    placeholder="Write your influencer script here... Keep it natural and conversational!"
                                    rows={8}
                                />
                                <span className="char-count">{script.length} characters</span>
                            </div>
                            <button
                                className="btn-primary"
                                onClick={() => setStep(3)}
                                disabled={!script}
                            >
                                Continue to Style →
                            </button>
                        </div>
                    )}

                    <button className="btn-secondary" onClick={() => setStep(1)}>
                        ← Back
                    </button>
                </div>
            )}

            {/* Step 3: Style Selection */}
            {step === 3 && (
                <div className="step-content">
                    <h3>Choose Your Style</h3>

                    {/* Generated Script Preview */}
                    {script && (
                        <div className="script-preview">
                            <label>Your Script</label>
                            <div className="script-text">{script}</div>
                            <button
                                className="edit-btn"
                                onClick={() => {
                                    setScriptMode('manual');
                                    setStep(2);
                                }}
                            >
                                Edit Script
                            </button>
                        </div>
                    )}

                    <div className="style-section">
                        <label>Influencer Style</label>
                        <div className="style-grid">
                            {influencerStyles.map(style => (
                                <div
                                    key={style.id}
                                    className={`style-card ${influencerStyle === style.id ? 'selected' : ''}`}
                                    onClick={() => setInfluencerStyle(style.id)}
                                >
                                    <span className="style-name">{style.name}</span>
                                    <span className="style-desc">{style.desc}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="voice-section">
                        <label>Voice</label>
                        <div className="voice-options">
                            <select
                                value={voiceStyle}
                                onChange={(e) => setVoiceStyle(e.target.value)}
                            >
                                {voiceStyles.map(v => (
                                    <option key={v.id} value={v.id}>{v.name}</option>
                                ))}
                            </select>
                            <div className="gender-toggle">
                                <button
                                    className={voiceGender === 'female' ? 'active' : ''}
                                    onClick={() => setVoiceGender('female')}
                                >
                                    Female
                                </button>
                                <button
                                    className={voiceGender === 'male' ? 'active' : ''}
                                    onClick={() => setVoiceGender('male')}
                                >
                                    Male
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="platform-section">
                        <label>Target Platform</label>
                        <div className="platform-grid">
                            {platforms.map(p => (
                                <div
                                    key={p.id}
                                    className={`platform-card ${targetPlatform === p.id ? 'selected' : ''}`}
                                    onClick={() => setTargetPlatform(p.id)}
                                >
                                    <span className="platform-icon">{p.icon}</span>
                                    <span>{p.name}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <button
                        className="btn-primary"
                        onClick={() => setStep(4)}
                    >
                        Continue to Generate →
                    </button>

                    <button className="btn-secondary" onClick={() => setStep(2)}>
                        ← Back
                    </button>
                </div>
            )}

            {/* Step 4: Generate */}
            {step === 4 && (
                <div className="step-content">
                    <h3>Ready to Generate</h3>

                    <div className="summary">
                        <div className="summary-row">
                            <span>Product Images:</span>
                            <span>{productImages.length} images</span>
                        </div>
                        <div className="summary-row">
                            <span>Script Length:</span>
                            <span>{script.length} characters</span>
                        </div>
                        <div className="summary-row">
                            <span>Influencer Style:</span>
                            <span>{influencerStyles.find(s => s.id === influencerStyle)?.name}</span>
                        </div>
                        <div className="summary-row">
                            <span>Voice:</span>
                            <span>{voiceStyle}, {voiceGender}</span>
                        </div>
                        <div className="summary-row">
                            <span>Platform:</span>
                            <span>{platforms.find(p => p.id === targetPlatform)?.name}</span>
                        </div>
                    </div>

                    <div className="estimated-time">
                        <span className="time-icon">⏱️</span>
                        <span>Estimated generation time: 2-5 minutes</span>
                    </div>

                    <button
                        className="btn-generate"
                        onClick={handleGenerate}
                        disabled={disabled || isGenerating}
                    >
                        {isGenerating ? (
                            <>
                                <span className="spinner"></span>
                                Creating Your Influencer...
                            </>
                        ) : (
                            <>
                                🎬 Generate Synthetic Influencer
                            </>
                        )}
                    </button>

                    <button className="btn-secondary" onClick={() => setStep(3)}>
                        ← Back
                    </button>
                </div>
            )}
        </div>
    );
}

export default SyntheticInfluencerCreator;
