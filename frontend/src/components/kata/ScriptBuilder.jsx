import React, { useState } from 'react';
import api from '../../services/api';

function ScriptBuilder({ organizationId, onScriptGenerated }) {
    const [step, setStep] = useState(0);
    const [answers, setAnswers] = useState({});
    const [generatedScript, setGeneratedScript] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [scriptFormat, setScriptFormat] = useState('tiktok');
    const [error, setError] = useState(null);

    const formats = [
        { id: 'tiktok', name: 'TikTok/Reels', maxLength: 60, structure: 'hook-problem-solution-cta' },
        { id: 'youtube', name: 'YouTube Short', maxLength: 60, structure: 'hook-story-cta' },
        { id: 'product_demo', name: 'Product Demo', maxLength: 90, structure: 'intro-features-benefits-cta' },
        { id: 'testimonial', name: 'Testimonial Style', maxLength: 45, structure: 'problem-discovery-result' },
        { id: 'educational', name: 'Educational', maxLength: 60, structure: 'hook-teach-engage' }
    ];

    const questionSets = {
        tiktok: [
            {
                id: 'hook_style',
                question: 'What type of hook do you want?',
                options: [
                    { value: 'question', label: 'Question ("Did you know...?")' },
                    { value: 'statement', label: 'Bold Statement ("This changed my life")' },
                    { value: 'controversy', label: 'Controversial ("Stop doing this...")' },
                    { value: 'story', label: 'Story ("I couldn\'t believe...")' }
                ]
            },
            {
                id: 'product',
                question: 'What product/service are you promoting?',
                type: 'text',
                placeholder: 'e.g., Wireless earbuds, Skincare serum, Online course'
            },
            {
                id: 'main_benefit',
                question: 'What\'s the #1 benefit for your customer?',
                type: 'text',
                placeholder: 'e.g., Save 2 hours a day, Clear skin in 2 weeks'
            },
            {
                id: 'pain_point',
                question: 'What problem does it solve?',
                type: 'text',
                placeholder: 'e.g., Tangled wires, Acne breakouts, Wasted time'
            },
            {
                id: 'proof',
                question: 'Any proof or social proof?',
                type: 'text',
                placeholder: 'e.g., 10K+ happy customers, Doctor recommended, As seen on...'
            },
            {
                id: 'cta',
                question: 'What action should viewers take?',
                options: [
                    { value: 'link_bio', label: 'Link in bio' },
                    { value: 'comment', label: 'Comment below' },
                    { value: 'follow', label: 'Follow for more' },
                    { value: 'shop', label: 'Shop now' },
                    { value: 'custom', label: 'Custom CTA' }
                ]
            },
            {
                id: 'tone',
                question: 'What tone should the script have?',
                options: [
                    { value: 'casual', label: 'Casual & Friendly' },
                    { value: 'professional', label: 'Professional' },
                    { value: 'energetic', label: 'High Energy & Excited' },
                    { value: 'educational', label: 'Informative & Helpful' },
                    { value: 'luxury', label: 'Premium & Aspirational' }
                ]
            }
        ],
        product_demo: [
            {
                id: 'product',
                question: 'What product are you demonstrating?',
                type: 'text',
                placeholder: 'Product name and type'
            },
            {
                id: 'features',
                question: 'List the top 3 features to highlight:',
                type: 'textarea',
                placeholder: '1. Feature one\n2. Feature two\n3. Feature three'
            },
            {
                id: 'use_case',
                question: 'What\'s the main use case to show?',
                type: 'text',
                placeholder: 'e.g., Morning routine, Work setup, Cooking'
            },
            {
                id: 'differentiator',
                question: 'What makes it different from competitors?',
                type: 'text',
                placeholder: 'e.g., 2x battery life, Natural ingredients only'
            },
            {
                id: 'tone',
                question: 'What tone should the demo have?',
                options: [
                    { value: 'casual', label: 'Casual & Relatable' },
                    { value: 'professional', label: 'Professional Review' },
                    { value: 'enthusiastic', label: 'Enthusiastic Unboxing' }
                ]
            }
        ],
        testimonial: [
            {
                id: 'before_state',
                question: 'What was life like BEFORE the product?',
                type: 'textarea',
                placeholder: 'Describe the struggle or problem...'
            },
            {
                id: 'discovery',
                question: 'How did they discover the product?',
                type: 'text',
                placeholder: 'e.g., Friend recommended, Saw an ad, Searched online'
            },
            {
                id: 'after_state',
                question: 'What\'s life like AFTER using it?',
                type: 'textarea',
                placeholder: 'Describe the transformation...'
            },
            {
                id: 'specific_result',
                question: 'Any specific measurable result?',
                type: 'text',
                placeholder: 'e.g., Lost 20 lbs, Saved $500/month, Got promoted'
            }
        ]
    };

    const currentQuestions = questionSets[scriptFormat] || questionSets.tiktok;
    const currentQuestion = currentQuestions[step];
    const totalSteps = currentQuestions.length;

    const handleAnswer = (value) => {
        setAnswers({ ...answers, [currentQuestion.id]: value });
    };

    const nextStep = () => {
        if (step < totalSteps - 1) {
            setStep(step + 1);
        } else {
            generateScript();
        }
    };

    const prevStep = () => {
        if (step > 0) {
            setStep(step - 1);
        }
    };

    const generateScript = async () => {
        setIsGenerating(true);
        setError(null);

        try {
            // Call the real API - no fallback
            const data = await api.generateScript({
                format: scriptFormat,
                answers: answers,
                organization_id: organizationId
            });

            if (data.script) {
                setGeneratedScript(data.script);
            } else {
                throw new Error('No script returned from API');
            }
        } catch (error) {
            console.error('Script generation failed:', error);
            setError(`Failed to generate script: ${error.message}. Please try again.`);
        } finally {
            setIsGenerating(false);
        }
    };

    const constructScript = (a) => {
        // Simple script construction based on answers
        let script = '';

        // Hook
        if (a.hook_style === 'question') {
            script += `Did you know most people struggle with ${a.pain_point}?\n\n`;
        } else if (a.hook_style === 'statement') {
            script += `This ${a.product} completely changed everything for me.\n\n`;
        } else if (a.hook_style === 'controversy') {
            script += `Stop wasting money on products that don't work for ${a.pain_point}.\n\n`;
        } else {
            script += `I couldn't believe how much ${a.product} changed my routine.\n\n`;
        }

        // Problem & Solution
        script += `I used to deal with ${a.pain_point} every single day.\n\n`;
        script += `Then I found this ${a.product} and now I ${a.main_benefit}.\n\n`;

        // Proof
        if (a.proof) {
            script += `And I'm not the only one - ${a.proof}.\n\n`;
        }

        // CTA
        if (a.cta === 'link_bio') {
            script += `Link in bio if you want to try it too!`;
        } else if (a.cta === 'comment') {
            script += `Comment below if you want me to share more details!`;
        } else if (a.cta === 'follow') {
            script += `Follow for more tips like this!`;
        } else {
            script += `Shop now to get yours!`;
        }

        return script;
    };

    const handleUseScript = () => {
        onScriptGenerated(generatedScript);
    };

    const resetBuilder = () => {
        setStep(0);
        setAnswers({});
        setGeneratedScript('');
        setError(null);
    };

    return (
        <div className="script-builder">
            <h3>📝 AI Script Builder</h3>

            {error && (
                <div className="script-error">
                    <span className="error-icon">⚠️</span>
                    <p>{error}</p>
                    <button onClick={() => setError(null)} className="dismiss-btn">Dismiss</button>
                </div>
            )}

            {!generatedScript ? (
                <>
                    {/* Format Selection (only on first step) */}
                    {step === 0 && (
                        <div className="format-selection">
                            <label>Script Format</label>
                            <div className="format-options">
                                {formats.map(f => (
                                    <button
                                        key={f.id}
                                        className={`format-btn ${scriptFormat === f.id ? 'selected' : ''}`}
                                        onClick={() => {
                                            setScriptFormat(f.id);
                                            setAnswers({});
                                        }}
                                    >
                                        <span className="format-name">{f.name}</span>
                                        <span className="format-length">~{f.maxLength}s</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Progress */}
                    <div className="builder-progress">
                        <div className="progress-bar">
                            <div
                                className="progress-fill"
                                style={{ width: `${((step + 1) / totalSteps) * 100}%` }}
                            />
                        </div>
                        <span className="progress-text">Question {step + 1} of {totalSteps}</span>
                    </div>

                    {/* Current Question */}
                    <div className="question-card">
                        <h4>{currentQuestion?.question}</h4>

                        {currentQuestion?.type === 'text' && (
                            <input
                                type="text"
                                placeholder={currentQuestion.placeholder}
                                value={answers[currentQuestion.id] || ''}
                                onChange={(e) => handleAnswer(e.target.value)}
                                autoFocus
                            />
                        )}

                        {currentQuestion?.type === 'textarea' && (
                            <textarea
                                placeholder={currentQuestion.placeholder}
                                value={answers[currentQuestion.id] || ''}
                                onChange={(e) => handleAnswer(e.target.value)}
                                rows={4}
                                autoFocus
                            />
                        )}

                        {currentQuestion?.options && (
                            <div className="options-grid">
                                {currentQuestion.options.map(opt => (
                                    <button
                                        key={opt.value}
                                        className={`option-btn ${answers[currentQuestion.id] === opt.value ? 'selected' : ''}`}
                                        onClick={() => handleAnswer(opt.value)}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Navigation */}
                    <div className="builder-nav">
                        <button
                            className="btn-secondary"
                            onClick={prevStep}
                            disabled={step === 0}
                        >
                            ← Back
                        </button>
                        <button
                            className="btn-primary"
                            onClick={nextStep}
                            disabled={!answers[currentQuestion?.id]}
                        >
                            {step === totalSteps - 1 ? (
                                isGenerating ? 'Generating...' : 'Generate Script ✨'
                            ) : (
                                'Next →'
                            )}
                        </button>
                    </div>
                </>
            ) : (
                /* Generated Script View */
                <div className="generated-script">
                    <div className="script-header">
                        <span className="success-badge">✨ Script Generated!</span>
                        <span className="format-badge">{formats.find(f => f.id === scriptFormat)?.name}</span>
                    </div>

                    <div className="script-content">
                        <textarea
                            value={generatedScript}
                            onChange={(e) => setGeneratedScript(e.target.value)}
                            rows={10}
                        />
                    </div>

                    <div className="script-stats">
                        <span>{generatedScript.length} characters</span>
                        <span>~{Math.ceil(generatedScript.split(' ').length / 2.5)}s speaking time</span>
                    </div>

                    <div className="script-actions">
                        <button className="btn-secondary" onClick={resetBuilder}>
                            Start Over
                        </button>
                        <button className="btn-secondary" onClick={generateScript}>
                            🔄 Regenerate
                        </button>
                        <button className="btn-primary" onClick={handleUseScript}>
                            ✓ Use This Script
                        </button>
                    </div>

                    <div className="script-tips">
                        <h4>💡 Tips for better performance:</h4>
                        <ul>
                            <li>Read the script aloud to check flow</li>
                            <li>First 3 seconds are crucial - nail the hook</li>
                            <li>Keep sentences short and punchy</li>
                            <li>Add natural pauses for emphasis</li>
                        </ul>
                    </div>
                </div>
            )}
        </div>
    );
}

export default ScriptBuilder;
