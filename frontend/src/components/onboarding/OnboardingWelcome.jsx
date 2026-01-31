import React, { useState } from 'react';
import './OnboardingWelcome.css';

function OnboardingWelcome({ onStart }) {
    const [domain, setDomain] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!domain.trim()) return;

        // Clean up domain input
        let cleanDomain = domain.trim().toLowerCase();

        // Remove protocol if present
        cleanDomain = cleanDomain.replace(/^(https?:\/\/)?(www\.)?/, '');

        // Remove trailing slash
        cleanDomain = cleanDomain.replace(/\/$/, '');

        setIsSubmitting(true);
        try {
            await onStart(cleanDomain);
        } finally {
            // Reset submitting state (component may unmount before this runs, which is fine)
            setIsSubmitting(false);
        }
    };

    return (
        <div className="onboarding-card animate-fadeIn">
            <div className="onboarding-header">
                <div className="onboarding-logo">
                    <span>✨</span>
                </div>
                <h1>Tell us about your brand</h1>
                <p>
                    Enter your website below. We'll analyze your brand, identify your competitors,
                    and build a profile of your target audience.
                </p>
            </div>

            <div className="onboarding-content">
                <form onSubmit={handleSubmit} className="welcome-form">
                    <div className="onboarding-form-group">
                        <label htmlFor="domain">Website URL</label>
                        <input
                            id="domain"
                            type="text"
                            placeholder="yourcompany.com"
                            value={domain}
                            onChange={(e) => setDomain(e.target.value)}
                            disabled={isSubmitting}
                            autoFocus
                        />
                    </div>

                    <div className="onboarding-actions">
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={!domain.trim() || isSubmitting}
                        >
                            {isSubmitting ? 'Starting...' : 'Get started'}
                        </button>
                    </div>
                </form>

                <p className="welcome-note">
                    This typically takes 2-3 minutes. You'll be able to review and edit the results.
                </p>
            </div>
        </div>
    );
}

export default OnboardingWelcome;
