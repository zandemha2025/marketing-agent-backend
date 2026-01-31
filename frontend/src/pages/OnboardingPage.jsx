import React, { useState, useRef, useCallback } from 'react';
import api from '../services/api';
import OnboardingWelcome from '../components/onboarding/OnboardingWelcome';
import OnboardingProgress from '../components/onboarding/OnboardingProgress';
import OnboardingResult from '../components/onboarding/OnboardingResult';
import './OnboardingPage.css';

/**
 * OnboardingPage - Rebuilt from scratch for reliability
 *
 * Simple state machine:
 * WELCOME -> PROCESSING -> RESULT (or ERROR)
 *
 * Uses polling only (no WebSocket complexity).
 * All state transitions happen in one place for clarity.
 */

const STAGE = {
    WELCOME: 'welcome',
    PROCESSING: 'processing',
    RESULT: 'result',
    ERROR: 'error',
};

function OnboardingPage({ onComplete }) {
    // Core state
    const [stage, setStage] = useState(STAGE.WELCOME);
    const [orgId, setOrgId] = useState(null);
    const [progress, setProgress] = useState({
        stage: 'initializing',
        progress: 0,
        message: 'Preparing...',
    });
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    // Refs to manage polling lifecycle
    const pollingRef = useRef(null);
    const mountedRef = useRef(true);

    // Cleanup polling
    const stopPolling = useCallback(() => {
        if (pollingRef.current) {
            console.log('[Onboarding] Stopping polling');
            clearTimeout(pollingRef.current);
            pollingRef.current = null;
        }
    }, []);

    // Fetch result and transition to RESULT stage
    const fetchResultAndComplete = useCallback(async (organizationId) => {
        console.log('[Onboarding] Fetching final result for:', organizationId);
        try {
            const data = await api.getOnboardingResult(organizationId);
            console.log('[Onboarding] Result fetched successfully:', data);

            if (!mountedRef.current) return;

            setResult(data);
            setStage(STAGE.RESULT);
            console.log('[Onboarding] Transitioned to RESULT stage');
        } catch (err) {
            console.error('[Onboarding] Failed to fetch result:', err);
            if (!mountedRef.current) return;

            setError(`Failed to load results: ${err.message}`);
            setStage(STAGE.ERROR);
        }
    }, []);

    // Poll for status
    const pollStatus = useCallback(async (organizationId) => {
        if (!mountedRef.current) return;

        console.log('[Onboarding] Polling status for:', organizationId);

        try {
            const status = await api.getOnboardingStatus(organizationId);
            console.log('[Onboarding] Status response:', status);

            if (!mountedRef.current) return;

            // Update progress display
            setProgress({
                stage: status.progress?.stage || 'initializing',
                progress: status.progress?.progress || 0,
                message: status.progress?.message || 'Working...',
            });

            // Check completion status
            if (status.status === 'complete') {
                console.log('[Onboarding] Backend reports COMPLETE');
                stopPolling();
                await fetchResultAndComplete(organizationId);
                return;
            }

            if (status.status === 'failed') {
                console.log('[Onboarding] Backend reports FAILED');
                stopPolling();
                setError(status.progress?.error || 'Onboarding failed');
                setStage(STAGE.ERROR);
                return;
            }

            // Continue polling
            pollingRef.current = setTimeout(() => pollStatus(organizationId), 2000);

        } catch (err) {
            console.error('[Onboarding] Polling error:', err);
            if (!mountedRef.current) return;

            stopPolling();
            setError(`Connection error: ${err.message}`);
            setStage(STAGE.ERROR);
        }
    }, [stopPolling, fetchResultAndComplete]);

    // Start onboarding process
    const handleStart = useCallback(async (domain) => {
        console.log('[Onboarding] Starting for domain:', domain);

        // Reset state
        setError(null);
        setResult(null);
        setProgress({
            stage: 'initializing',
            progress: 0,
            message: `Starting research for ${domain}...`,
        });
        setStage(STAGE.PROCESSING);

        try {
            const response = await api.startOnboarding(domain);
            console.log('[Onboarding] Started, org ID:', response.organization_id);

            if (!mountedRef.current) return;

            setOrgId(response.organization_id);

            // Start polling
            pollingRef.current = setTimeout(
                () => pollStatus(response.organization_id),
                1000
            );

        } catch (err) {
            console.error('[Onboarding] Start error:', err);
            if (!mountedRef.current) return;

            // Check if it's an "already onboarded" error
            if (err.message.includes('already onboarded')) {
                // Try to extract org ID and go straight to result
                // For now, just show a helpful error
                setError('This domain has already been analyzed. The results are available.');
            } else {
                setError(`Failed to start: ${err.message}`);
            }
            setStage(STAGE.ERROR);
        }
    }, [pollStatus]);

    // Handle completion
    const handleComplete = useCallback(() => {
        console.log('[Onboarding] User clicked complete, org ID:', orgId);
        if (orgId && onComplete) {
            onComplete(orgId);
        }
    }, [orgId, onComplete]);

    // Handle retry
    const handleRetry = useCallback(async () => {
        console.log('[Onboarding] Retry requested');
        stopPolling();

        if (orgId) {
            // Try to retry the existing org
            setStage(STAGE.PROCESSING);
            setError(null);
            setProgress({
                stage: 'initializing',
                progress: 0,
                message: 'Retrying...',
            });

            try {
                await api.retryOnboarding(orgId);
                pollingRef.current = setTimeout(() => pollStatus(orgId), 1000);
            } catch (err) {
                console.error('[Onboarding] Retry failed:', err);
                setError(`Retry failed: ${err.message}`);
                setStage(STAGE.ERROR);
            }
        } else {
            // Go back to welcome
            setStage(STAGE.WELCOME);
            setError(null);
        }
    }, [orgId, pollStatus, stopPolling]);

    // Cleanup on unmount
    React.useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            stopPolling();
        };
    }, [stopPolling]);

    // Render based on stage
    return (
        <div className="onboarding-page">
            <div className="onboarding-container">
                {stage === STAGE.WELCOME && (
                    <OnboardingWelcome onStart={handleStart} />
                )}

                {stage === STAGE.PROCESSING && (
                    <OnboardingProgress progress={progress} />
                )}

                {stage === STAGE.RESULT && result && (
                    <OnboardingResult
                        result={result}
                        onComplete={handleComplete}
                        organizationId={orgId}
                    />
                )}

                {stage === STAGE.ERROR && (
                    <div className="onboarding-error animate-fadeIn">
                        <div className="error-icon">⚠️</div>
                        <h2>Something went wrong</h2>
                        <p>{error}</p>
                        <div className="error-actions">
                            <button
                                className="btn btn-secondary"
                                onClick={() => {
                                    setStage(STAGE.WELCOME);
                                    setError(null);
                                    setOrgId(null);
                                }}
                            >
                                Start Over
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={handleRetry}
                            >
                                Try Again
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Background decorations */}
            <div className="bg-decoration bg-decoration-1"></div>
            <div className="bg-decoration bg-decoration-2"></div>
            <div className="bg-decoration bg-decoration-3"></div>
        </div>
    );
}

export default OnboardingPage;
