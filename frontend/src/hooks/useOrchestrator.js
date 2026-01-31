import { useState, useEffect, useCallback, useRef } from 'react';

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

/**
 * Hook for managing the campaign orchestrator connection.
 *
 * Handles:
 * - WebSocket connection to orchestrator
 * - Real-time phase and progress updates
 * - Deliverables streaming
 * - Concept pitch handling
 * - Refinement requests
 */
export function useOrchestrator(sessionId) {
    const [phase, setPhase] = useState('not_started');
    const [progress, setProgress] = useState(0);
    const [statusMessage, setStatusMessage] = useState('');
    const [concepts, setConcepts] = useState([]);
    const [deliverables, setDeliverables] = useState([]);
    const [pitchData, setPitchData] = useState(null);
    const [error, setError] = useState(null);
    const [isConnected, setIsConnected] = useState(false);

    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    // Connect to WebSocket
    const connect = useCallback(() => {
        if (!sessionId) return;

        const ws = new WebSocket(`${WS_BASE}/api/orchestrator/${sessionId}/ws`);
        wsRef.current = ws;

        ws.onopen = () => {
            setIsConnected(true);
            setError(null);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (err) {
                console.error('Failed to parse WebSocket message:', err);
            }
        };

        ws.onerror = (event) => {
            console.error('WebSocket error:', event);
            setError('Connection error');
        };

        ws.onclose = () => {
            setIsConnected(false);
            // Attempt to reconnect after 3 seconds if not intentionally closed
            if (wsRef.current) {
                reconnectTimeoutRef.current = setTimeout(() => {
                    connect();
                }, 3000);
            }
        };
    }, [sessionId]);

    // Handle incoming messages
    const handleMessage = useCallback((data) => {
        switch (data.type) {
            case 'connected':
                setPhase('connected');
                break;

            case 'phase':
                setPhase(data.phase);
                setProgress(data.progress || 0);
                setStatusMessage(data.message || '');
                break;

            case 'pitch':
                setPhase('awaiting_approval');
                setPitchData(data.data);
                setConcepts(data.data?.concepts || []);
                setStatusMessage(data.message || "Here's what I'm thinking...");
                break;

            case 'deliverable':
                setPhase(data.phase);
                setProgress(data.progress || 0);
                setStatusMessage(data.message || '');
                // Add or update deliverable
                setDeliverables(prev => {
                    const existing = prev.findIndex(d => d.id === data.deliverable.id);
                    if (existing >= 0) {
                        const updated = [...prev];
                        updated[existing] = data.deliverable;
                        return updated;
                    }
                    return [...prev, data.deliverable];
                });
                break;

            case 'refinement_complete':
                // Update the specific deliverable
                setDeliverables(prev =>
                    prev.map(d => d.id === data.deliverable.id ? data.deliverable : d)
                );
                break;

            case 'complete':
                setPhase('complete');
                setProgress(1);
                setStatusMessage('Campaign complete!');
                if (data.data?.deliverables_by_type) {
                    // Flatten grouped deliverables
                    const allDeliverables = Object.values(data.data.deliverables_by_type).flat();
                    setDeliverables(allDeliverables);
                }
                break;

            case 'error':
                setError(data.message);
                setPhase('failed');
                break;

            case 'chat_response':
                // Handle chat response if needed
                break;

            default:
                console.log('Unknown message type:', data.type);
        }
    }, []);

    // Start campaign execution
    const start = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ action: 'start' }));
            setPhase('initializing');
            setStatusMessage('Starting campaign...');
        }
    }, []);

    // Select a concept
    const selectConcept = useCallback((index) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                action: 'select_concept',
                index
            }));
            setPhase('briefing');
            setStatusMessage('Creating campaign assets...');
        }
    }, []);

    // Refine a deliverable
    const refineDeliverable = useCallback((deliverableId, feedback) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            // Mark deliverable as generating
            setDeliverables(prev =>
                prev.map(d => d.id === deliverableId ? { ...d, status: 'generating' } : d)
            );
            wsRef.current.send(JSON.stringify({
                action: 'refine',
                deliverable_id: deliverableId,
                feedback
            }));
        }
    }, []);

    // Send a chat message
    const sendMessage = useCallback((message, deliverableId = null) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                action: 'chat',
                message,
                deliverable_id: deliverableId
            }));
        }
    }, []);

    // Disconnect
    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setIsConnected(false);
    }, []);

    // Connect when sessionId changes
    useEffect(() => {
        if (sessionId) {
            connect();
        }
        return () => {
            disconnect();
        };
    }, [sessionId, connect, disconnect]);

    return {
        // State
        phase,
        progress,
        statusMessage,
        concepts,
        deliverables,
        pitchData,
        error,
        isConnected,

        // Actions
        start,
        selectConcept,
        refineDeliverable,
        sendMessage,
        disconnect
    };
}

export default useOrchestrator;
