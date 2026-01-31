import React, { useState } from 'react';
import api from '../../services/api';
import './LandingPageBuilder.css';

/**
 * Landing Page Builder Component
 * 
 * Features:
 * - Generate landing pages in HTML/React/Next.js formats
 * - Brand DNA integration
 * - AI-planned sections based on campaign goal
 * - SEO-optimized structure
 * - Deploy to Vercel/Netlify
 */

const OUTPUT_FORMATS = [
    { id: 'html', name: 'HTML + Tailwind', description: 'Quick landing pages' },
    { id: 'react', name: 'React Component', description: 'Integration into existing apps' },
    { id: 'nextjs', name: 'Next.js Project', description: 'Full deployable site' },
    { id: 'all', name: 'All Formats', description: 'Get all output types' },
];

const AVAILABLE_SECTIONS = [
    { id: 'hero', name: 'Hero Section', default: true },
    { id: 'features', name: 'Features/Benefits', default: true },
    { id: 'how_it_works', name: 'How It Works', default: false },
    { id: 'social_proof', name: 'Testimonials', default: true },
    { id: 'pricing', name: 'Pricing', default: false },
    { id: 'faq', name: 'FAQ', default: false },
    { id: 'cta', name: 'Final CTA', default: true },
];

const LandingPageBuilder = ({ organizationId, onSave, onClose }) => {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // Form state
    const [goal, setGoal] = useState('');
    const [targetAudience, setTargetAudience] = useState('');
    const [keyBenefits, setKeyBenefits] = useState(['']);
    const [selectedSections, setSelectedSections] = useState(
        AVAILABLE_SECTIONS.filter(s => s.default).map(s => s.id)
    );
    const [outputFormat, setOutputFormat] = useState('all');
    
    // Generated content
    const [generatedPage, setGeneratedPage] = useState(null);
    const [activeTab, setActiveTab] = useState('html');
    const [projectScaffold, setProjectScaffold] = useState(null);

    const handleAddBenefit = () => {
        setKeyBenefits([...keyBenefits, '']);
    };

    const handleRemoveBenefit = (index) => {
        if (keyBenefits.length > 1) {
            setKeyBenefits(keyBenefits.filter((_, i) => i !== index));
        }
    };

    const handleBenefitChange = (index, value) => {
        const newBenefits = [...keyBenefits];
        newBenefits[index] = value;
        setKeyBenefits(newBenefits);
    };

    const toggleSection = (sectionId) => {
        setSelectedSections(prev =>
            prev.includes(sectionId)
                ? prev.filter(id => id !== sectionId)
                : [...prev, sectionId]
        );
    };

    const handleGenerate = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const validBenefits = keyBenefits.filter(b => b.trim());
            
            const result = await api.generateLandingPage(organizationId, {
                goal,
                target_audience: targetAudience,
                key_benefits: validBenefits,
                sections: selectedSections,
                output_format: outputFormat
            });
            
            setGeneratedPage(result);
            
            // If Next.js format, also get scaffold
            if (outputFormat === 'nextjs' || outputFormat === 'all') {
                try {
                    const scaffold = await api.scaffoldLandingPageProject(organizationId, {
                        goal,
                        target_audience: targetAudience,
                        key_benefits: validBenefits,
                        sections: selectedSections
                    });
                    setProjectScaffold(scaffold);
                } catch (err) {
                    console.error('Failed to scaffold project:', err);
                }
            }
            
            setStep(3);
        } catch (err) {
            setError(err.message || 'Failed to generate landing page');
        } finally {
            setLoading(false);
        }
    };

    const handleNext = () => {
        if (step < 3) {
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
                return goal.trim().length > 0 && targetAudience.trim().length > 0;
            case 2:
                return keyBenefits.some(b => b.trim().length > 0) && selectedSections.length > 0;
            default:
                return true;
        }
    };

    const downloadFile = (content, filename, type = 'text/plain') => {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const downloadProject = () => {
        if (!projectScaffold) return;
        
        // Create a zip-like structure by downloading each file
        Object.entries(projectScaffold.files).forEach(([path, content]) => {
            const filename = path.replace(/\//g, '-');
            downloadFile(content, filename, 'text/plain');
        });
    };

    const renderStep1 = () => (
        <div className="lp-step">
            <h3>Step 1: Campaign Details</h3>
            <p className="step-description">Define your campaign goal and target audience.</p>
            
            <div className="form-group">
                <label>Campaign Goal *</label>
                <input
                    type="text"
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                    placeholder="e.g., Lead generation for SaaS product"
                />
            </div>

            <div className="form-group">
                <label>Target Audience *</label>
                <input
                    type="text"
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    placeholder="e.g., Marketing managers at enterprise companies"
                />
            </div>

            <div className="form-group">
                <label>Output Format</label>
                <div className="format-options">
                    {OUTPUT_FORMATS.map(fmt => (
                        <label key={fmt.id} className="format-option">
                            <input
                                type="radio"
                                name="outputFormat"
                                value={fmt.id}
                                checked={outputFormat === fmt.id}
                                onChange={(e) => setOutputFormat(e.target.value)}
                            />
                            <div className="format-info">
                                <span className="format-name">{fmt.name}</span>
                                <span className="format-desc">{fmt.description}</span>
                            </div>
                        </label>
                    ))}
                </div>
            </div>
        </div>
    );

    const renderStep2 = () => (
        <div className="lp-step">
            <h3>Step 2: Content & Sections</h3>
            <p className="step-description">Define key benefits and select page sections.</p>
            
            <div className="form-group">
                <label>Key Benefits</label>
                <div className="benefits-list">
                    {keyBenefits.map((benefit, index) => (
                        <div key={index} className="benefit-item">
                            <input
                                type="text"
                                value={benefit}
                                onChange={(e) => handleBenefitChange(index, e.target.value)}
                                placeholder={`Benefit ${index + 1}`}
                            />
                            {keyBenefits.length > 1 && (
                                <button 
                                    className="remove-btn"
                                    onClick={() => handleRemoveBenefit(index)}
                                >
                                    ✕
                                </button>
                            )}
                        </div>
                    ))}
                </div>
                <button className="add-btn" onClick={handleAddBenefit}>
                    + Add Benefit
                </button>
            </div>

            <div className="form-group">
                <label>Page Sections</label>
                <div className="sections-grid">
                    {AVAILABLE_SECTIONS.map(section => (
                        <label key={section.id} className="section-checkbox">
                            <input
                                type="checkbox"
                                checked={selectedSections.includes(section.id)}
                                onChange={() => toggleSection(section.id)}
                            />
                            <span>{section.name}</span>
                        </label>
                    ))}
                </div>
            </div>
        </div>
    );

    const renderStep3 = () => {
        if (!generatedPage) return null;

        return (
            <div className="lp-step">
                <h3>Step 3: Generated Landing Page</h3>
                
                <div className="seo-info">
                    <h4>SEO Metadata</h4>
                    <div className="seo-field">
                        <label>Title:</label>
                        <span>{generatedPage.seo_title}</span>
                    </div>
                    <div className="seo-field">
                        <label>Description:</label>
                        <span>{generatedPage.seo_description}</span>
                    </div>
                    <div className="seo-field">
                        <label>Keywords:</label>
                        <span>{generatedPage.keywords?.join(', ')}</span>
                    </div>
                </div>

                <div className="preview-tabs">
                    {generatedPage.html_tailwind && (
                        <button 
                            className={activeTab === 'html' ? 'active' : ''}
                            onClick={() => setActiveTab('html')}
                        >
                            HTML Preview
                        </button>
                    )}
                    {generatedPage.react_component && (
                        <button 
                            className={activeTab === 'react' ? 'active' : ''}
                            onClick={() => setActiveTab('react')}
                        >
                            React Component
                        </button>
                    )}
                    {projectScaffold && (
                        <button 
                            className={activeTab === 'nextjs' ? 'active' : ''}
                            onClick={() => setActiveTab('nextjs')}
                        >
                            Next.js Project
                        </button>
                    )}
                </div>

                <div className="code-preview">
                    {activeTab === 'html' && generatedPage.html_tailwind && (
                        <>
                            <iframe
                                srcDoc={generatedPage.html_tailwind}
                                title="Landing Page Preview"
                                className="html-preview-frame"
                            />
                            <button 
                                className="download-btn"
                                onClick={() => downloadFile(generatedPage.html_tailwind, 'landing-page.html', 'text/html')}
                            >
                                📥 Download HTML
                            </button>
                        </>
                    )}
                    
                    {activeTab === 'react' && generatedPage.react_component && (
                        <>
                            <textarea 
                                readOnly 
                                value={generatedPage.react_component}
                                className="code-textarea"
                                rows={20}
                            />
                            <button 
                                className="download-btn"
                                onClick={() => downloadFile(generatedPage.react_component, 'LandingPage.jsx', 'text/javascript')}
                            >
                                📥 Download Component
                            </button>
                        </>
                    )}
                    
                    {activeTab === 'nextjs' && projectScaffold && (
                        <div className="project-scaffold">
                            <h4>Project: {projectScaffold.project_name}</h4>
                            <div className="file-list">
                                {Object.keys(projectScaffold.files).map(path => (
                                    <div key={path} className="file-item">
                                        <span className="file-path">{path}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="scaffold-instructions">
                                <h5>Setup Instructions:</h5>
                                <pre>{projectScaffold.instructions.setup}</pre>
                            </div>
                            <button className="download-btn" onClick={downloadProject}>
                                📥 Download All Files
                            </button>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="landing-page-builder">
            <div className="builder-header">
                <h2>Landing Page Builder</h2>
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
                
                {step < 3 ? (
                    <button 
                        className="next-btn"
                        onClick={handleNext}
                        disabled={!canProceed() || loading}
                    >
                        {loading && step === 2 ? 'Generating...' : 'Next →'}
                    </button>
                ) : (
                    <button 
                        className="restart-btn"
                        onClick={() => {
                            setStep(1);
                            setGeneratedPage(null);
                            setProjectScaffold(null);
                        }}
                    >
                        🔄 Create New
                    </button>
                )}
            </div>
        </div>
    );
};

export default LandingPageBuilder;