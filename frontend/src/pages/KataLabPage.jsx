import React, { useState, useRef, useEffect } from 'react';
import SyntheticInfluencerCreator from '../components/kata/SyntheticInfluencerCreator';
import VideoCompositor from '../components/kata/VideoCompositor';
import ScriptBuilder from '../components/kata/ScriptBuilder';
import KataPreview from '../components/kata/KataPreview';
import api from '../services/api';
import '../styles/kata-lab.css';

function KataLabPage({ organizationId, onBack }) {
    const [activeMode, setActiveMode] = useState('influencer'); // influencer, compositor, script
    const [currentJob, setCurrentJob] = useState(null);
    const [generatedContent, setGeneratedContent] = useState(null);
    const [pollingError, setPollingError] = useState(null);
    const pollingIntervalRef = useRef(null);

    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
        };
    }, []);

    const modes = [
        {
            id: 'influencer',
            name: 'Synthetic Influencer',
            icon: '👤',
            description: 'Create AI influencers with your products'
        },
        {
            id: 'compositor',
            name: 'Video Compositor',
            icon: '🎬',
            description: 'Merge videos, add products, create mashups'
        },
        {
            id: 'script',
            name: 'Script Builder',
            icon: '📝',
            description: 'AI-assisted script writing'
        }
    ];

    const handleJobCreated = (job) => {
        setCurrentJob(job);
        setPollingError(null);
        // Start polling for job status
        pollJobStatus(job.job_id);
    };

    const pollJobStatus = async (jobId) => {
        // Clear any existing interval
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
        }

        pollingIntervalRef.current = setInterval(async () => {
            try {
                const data = await api.getKataJobStatus(jobId);

                setCurrentJob(data);

                if (data.status === 'completed' || data.status === 'complete') {
                    clearInterval(pollingIntervalRef.current);
                    pollingIntervalRef.current = null;
                    // Fetch full result
                    try {
                        const result = await api.getKataJobResult(jobId);
                        setGeneratedContent(result);
                    } catch (resultError) {
                        console.error('Error fetching job result:', resultError);
                        setPollingError('Failed to fetch final result');
                    }
                } else if (data.status === 'failed') {
                    clearInterval(pollingIntervalRef.current);
                    pollingIntervalRef.current = null;
                    setPollingError(data.error || 'Job failed');
                }
            } catch (error) {
                console.error('Error polling job status:', error);
                setPollingError('Failed to check job status');
                // Don't stop polling on network errors, but limit retries
            }
        }, 2000);
    };

    const handleReset = () => {
        // Clear polling interval
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
        }
        setCurrentJob(null);
        setGeneratedContent(null);
        setPollingError(null);
    };

    return (
        <div className="kata-lab-page">
            <header className="kata-header">
                <button className="back-button" onClick={onBack}>
                    ← Back to Dashboard
                </button>
                <div className="kata-title">
                    <h1>🎭 Kata Lab</h1>
                    <p>AI-Powered Content Creation Studio</p>
                </div>
            </header>

            <div className="kata-content">
                {/* Mode Selection */}
                <div className="mode-selector">
                    {modes.map(mode => (
                        <button
                            key={mode.id}
                            className={`mode-button ${activeMode === mode.id ? 'active' : ''}`}
                            onClick={() => {
                                setActiveMode(mode.id);
                                handleReset();
                            }}
                        >
                            <span className="mode-icon">{mode.icon}</span>
                            <span className="mode-name">{mode.name}</span>
                            <span className="mode-desc">{mode.description}</span>
                        </button>
                    ))}
                </div>

                <div className="kata-workspace">
                    {/* Left Panel - Creator */}
                    <div className="creator-panel">
                        {activeMode === 'influencer' && (
                            <SyntheticInfluencerCreator
                                organizationId={organizationId}
                                onJobCreated={handleJobCreated}
                                disabled={currentJob && currentJob.status === 'processing'}
                            />
                        )}
                        {activeMode === 'compositor' && (
                            <VideoCompositor
                                organizationId={organizationId}
                                onJobCreated={handleJobCreated}
                                disabled={currentJob && currentJob.status === 'processing'}
                            />
                        )}
                        {activeMode === 'script' && (
                            <ScriptBuilder
                                organizationId={organizationId}
                                onScriptGenerated={(script) => setGeneratedContent({ script })}
                            />
                        )}
                    </div>

                    {/* Right Panel - Preview */}
                    <div className="preview-panel">
                        <KataPreview
                            job={currentJob}
                            content={generatedContent}
                            onReset={handleReset}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}

export default KataLabPage;
