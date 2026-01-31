import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useOrchestrator } from '../hooks/useOrchestrator';
import { SimpleDeliverablesPanel, ConceptPitch } from '../components/deliverables';
import ChatPanel from '../components/chat/ChatPanel';
// import { useGetCampaign } from '../hooks/useConvex';
import api from '../services/api';
import './CampaignStudioPage.css';

/**
 * Campaign Studio - The main campaign creation experience.
 *
 * Layout:
 * - Left: Chat panel (for interacting with the AI)
 * - Right: Context panel OR Deliverables panel (slides based on phase)
 *
 * Phases:
 * 1. Initializing / Researching / Strategizing → Show progress in context panel
 * 2. Awaiting Approval (Pitch) → Show ConceptPitch component
 * 3. Briefing / Producing → Show DeliverablesPanel with real-time updates
 * 4. Complete → Show full deliverables, ready for interaction
 */
export default function CampaignStudioPage() {
    const { sessionId } = useParams();
    const navigate = useNavigate();

    const [campaign, setCampaign] = useState(null);
    const [convexCampaignId, setConvexCampaignId] = useState(null);
    const [selectedDeliverableId, setSelectedDeliverableId] = useState(null);
    const [rightPanel, setRightPanel] = useState('context'); // 'context' | 'deliverables' | 'pitch'

    // Get campaign from Convex for real-time updates
    // const convexCampaign = useGetCampaign(convexCampaignId);

    const {
        phase,
        progress,
        statusMessage,
        concepts,
        deliverables,
        pitchData,
        error,
        isConnected,
        start,
        selectConcept,
        refineDeliverable,
        sendMessage
    } = useOrchestrator(sessionId);

    // Auto-start when connected
    useEffect(() => {
        if (isConnected && phase === 'connected') {
            start();
        }
    }, [isConnected, phase, start]);

    // Switch right panel based on phase
    useEffect(() => {
        if (phase === 'awaiting_approval') {
            setRightPanel('pitch');
        } else if (['producing', 'refining', 'complete'].includes(phase)) {
            setRightPanel('deliverables');
        } else {
            setRightPanel('context');
        }
    }, [phase]);

    // Handle concept selection
    const handleSelectConcept = (index) => {
        selectConcept(index);
        setRightPanel('deliverables');
    };

    // Handle deliverable selection (for refinement)
    const handleSelectDeliverable = (id) => {
        setSelectedDeliverableId(selectedDeliverableId === id ? null : id);
    };

    // Handle chat message (may be in context of selected deliverable)
    const handleChatMessage = (message) => {
        if (selectedDeliverableId) {
            refineDeliverable(selectedDeliverableId, message);
        } else {
            sendMessage(message);
        }
    };

    // Get context panel content
    const renderContextPanel = () => (
        <div className="context-panel">
            <div className="context-panel__header">
                <h3>Progress</h3>
            </div>
            <div className="context-panel__content">
                <div className="phase-indicator">
                    <span className={`phase-badge phase-badge--${phase}`}>
                        {phase.replace('_', ' ')}
                    </span>
                </div>

                {progress > 0 && (
                    <div className="progress-section">
                        <div className="progress-bar">
                            <div
                                className="progress-bar__fill"
                                style={{ width: `${progress * 100}%` }}
                            />
                        </div>
                        <span className="progress-label">{Math.round(progress * 100)}%</span>
                    </div>
                )}

                {statusMessage && (
                    <div className="status-message">
                        {statusMessage}
                    </div>
                )}

                {error && (
                    <div className="error-message">
                        {error}
                    </div>
                )}

                {/* Phase-specific content */}
                {phase === 'researching' && (
                    <div className="phase-content">
                        <div className="thinking-indicator">
                            <span className="dot"></span>
                            <span className="dot"></span>
                            <span className="dot"></span>
                        </div>
                        <p>Researching market context and trends...</p>
                    </div>
                )}

                {phase === 'strategizing' && (
                    <div className="phase-content">
                        <div className="thinking-indicator">
                            <span className="dot"></span>
                            <span className="dot"></span>
                            <span className="dot"></span>
                        </div>
                        <p>Developing creative concepts...</p>
                    </div>
                )}
            </div>
        </div>
    );

    return (
        <div className="campaign-studio">
            {/* Left: Chat Panel */}
            <div className="campaign-studio__chat">
                <ChatPanel
                    organizationId={campaign?.organization_id}
                    campaignId={campaign?.id}
                    onSendMessage={handleChatMessage}
                    selectedDeliverableId={selectedDeliverableId}
                    placeholder={
                        selectedDeliverableId
                            ? "Type to refine selected deliverable..."
                            : "Ask me anything about this campaign..."
                    }
                />
            </div>

            {/* Right: Context / Pitch / Deliverables Panel */}
            <div className="campaign-studio__panel">
                {rightPanel === 'context' && renderContextPanel()}

                {rightPanel === 'pitch' && pitchData && (
                    <ConceptPitch
                        concepts={concepts}
                        strategy={pitchData.strategy}
                        researchSummary={pitchData.research_summary}
                        tension={pitchData.tension}
                        onSelectConcept={handleSelectConcept}
                        onRequestChanges={(feedback) => sendMessage(feedback)}
                    />
                )}

                {rightPanel === 'deliverables' && (
                    <SimpleDeliverablesPanel
                        campaignId={sessionId} // Use sessionId as campaign ID for now
                        selectedId={selectedDeliverableId}
                        onSelect={handleSelectDeliverable}
                        onRefine={refineDeliverable}
                        phase={phase}
                        progress={progress}
                        statusMessage={statusMessage}
                        wsDeliverables={deliverables}
                    />
                )}

                {/* Panel Switcher (when deliverables exist) */}
                {deliverables.length > 0 && rightPanel !== 'pitch' && (
                    <div className="panel-switcher">
                        <button
                            className={rightPanel === 'context' ? 'active' : ''}
                            onClick={() => setRightPanel('context')}
                        >
                            Context
                        </button>
                        <button
                            className={rightPanel === 'deliverables' ? 'active' : ''}
                            onClick={() => setRightPanel('deliverables')}
                        >
                            Deliverables ({deliverables.length})
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
