import React, { useState } from 'react';
import './ConceptPitch.css';

function ConceptPitch({
    concepts = [],
    strategy = {},
    researchSummary = '',
    tension = {},
    onSelectConcept,
    onRequestChanges
}) {
    const [selectedIndex, setSelectedIndex] = useState(null);
    const [feedbackMode, setFeedbackMode] = useState(false);
    const [feedback, setFeedback] = useState('');

    const handleSelect = (index) => {
        setSelectedIndex(index);
    };

    const handleConfirm = () => {
        if (selectedIndex !== null) {
            onSelectConcept?.(selectedIndex);
        }
    };

    const handleRequestChanges = () => {
        if (feedback.trim()) {
            onRequestChanges?.(feedback);
            setFeedback('');
            setFeedbackMode(false);
        }
    };

    return (
        <div className="concept-pitch">
            {/* Header */}
            <div className="concept-pitch__header">
                <div className="pitch-intro">
                    <span className="pitch-intro__icon">💡</span>
                    <div>
                        <h2>Here's what I'm thinking...</h2>
                        <p>Based on your brand and what you're trying to achieve, I've developed {concepts.length} creative directions.</p>
                    </div>
                </div>
            </div>

            {/* Research Summary (collapsible) */}
            {researchSummary && (
                <div className="pitch-research">
                    <details>
                        <summary>📊 Research Insights</summary>
                        <p>{researchSummary}</p>
                    </details>
                </div>
            )}

            {/* Brand Tension (if available) */}
            {tension?.tension && (
                <div className="pitch-tension">
                    <div className="tension-card">
                        <span className="tension-label">The Tension</span>
                        <p className="tension-text">{tension.tension}</p>
                        {tension.resolution && (
                            <p className="tension-resolution">
                                <strong>Resolution:</strong> {tension.resolution}
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* Concepts Grid */}
            <div className="concept-pitch__concepts">
                {concepts.map((concept, index) => (
                    <div
                        key={concept.id || index}
                        className={`concept-card ${selectedIndex === index ? 'concept-card--selected' : ''}`}
                        onClick={() => handleSelect(index)}
                    >
                        {/* Concept Header */}
                        <div className="concept-card__header">
                            <span className="concept-number">Concept {index + 1}</span>
                            {selectedIndex === index && (
                                <span className="concept-selected-badge">✓ Selected</span>
                            )}
                        </div>

                        {/* Concept Name */}
                        <h3 className="concept-card__name">{concept.name}</h3>

                        {/* Description */}
                        <p className="concept-card__description">{concept.description}</p>

                        {/* Manifesto */}
                        {concept.manifesto && (
                            <div className="concept-card__manifesto">
                                <span className="manifesto-label">The Idea</span>
                                <p>{concept.manifesto}</p>
                            </div>
                        )}

                        {/* Visual World */}
                        {concept.visual_world && (
                            <div className="concept-card__visual">
                                <span className="section-label">🎨 Visual World</span>
                                <p>{concept.visual_world}</p>
                            </div>
                        )}

                        {/* Tone of Voice */}
                        {concept.tone_of_voice && (
                            <div className="concept-card__tone">
                                <span className="section-label">🗣️ Tone</span>
                                <p>{concept.tone_of_voice}</p>
                            </div>
                        )}

                        {/* Channel Expressions */}
                        {concept.channel_expressions?.length > 0 && (
                            <div className="concept-card__channels">
                                <span className="section-label">📱 How It Comes to Life</span>
                                <ul>
                                    {concept.channel_expressions.slice(0, 3).map((expr, i) => (
                                        <li key={i}>
                                            <strong>{expr.channel}:</strong> {expr.expression || expr.description}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Mood Board Placeholder */}
                        {concept.mood_images?.length > 0 ? (
                            <div className="concept-card__mood">
                                <div className="mood-grid">
                                    {concept.mood_images.slice(0, 4).map((img, i) => (
                                        <img key={i} src={img} alt={`Mood ${i + 1}`} />
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="concept-card__mood concept-card__mood--placeholder">
                                <div className="mood-placeholder">
                                    <span>🎭</span>
                                    <p>Visual direction would go here</p>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Action Bar */}
            <div className="concept-pitch__actions">
                {feedbackMode ? (
                    <div className="feedback-form">
                        <textarea
                            value={feedback}
                            onChange={(e) => setFeedback(e.target.value)}
                            placeholder="What would you like to change? Be specific..."
                            rows={3}
                        />
                        <div className="feedback-actions">
                            <button
                                className="btn btn--secondary"
                                onClick={() => setFeedbackMode(false)}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn btn--primary"
                                onClick={handleRequestChanges}
                                disabled={!feedback.trim()}
                            >
                                Submit Feedback
                            </button>
                        </div>
                    </div>
                ) : (
                    <>
                        <button
                            className="btn btn--secondary"
                            onClick={() => setFeedbackMode(true)}
                        >
                            ✏️ Request Changes
                        </button>
                        <button
                            className="btn btn--primary"
                            onClick={handleConfirm}
                            disabled={selectedIndex === null}
                        >
                            {selectedIndex !== null
                                ? `Go with "${concepts[selectedIndex]?.name}"`
                                : 'Select a concept to continue'
                            }
                        </button>
                    </>
                )}
            </div>

            {/* Tip */}
            <div className="concept-pitch__tip">
                💡 Tip: Click a concept to select it. You can always refine things later.
            </div>
        </div>
    );
}

export default ConceptPitch;
