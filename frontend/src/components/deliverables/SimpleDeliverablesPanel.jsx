import React, { useState } from 'react';
import DeliverablesPanel from './DeliverablesPanel';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Simple Deliverables Panel - Non-Convex version
 * 
 * This component wraps DeliverablesPanel without Convex integration
 * for testing the backend API functionality.
 */
export default function SimpleDeliverablesPanel({
    campaignId,
    selectedId,
    onSelect,
    onRefine,
    phase = 'producing',
    progress = 0,
    statusMessage = '',
    // Deliverables from WebSocket (fallback)
    wsDeliverables = [],
    // Callback when deliverable is approved (to refresh list)
    onApproved
}) {
    // Just pass through WebSocket deliverables for now
    const deliverables = wsDeliverables || [];
    const [isApproving, setIsApproving] = useState(false);

    // Handle approval/status update - calls backend API
    const handleApprove = async (deliverableId) => {
        if (isApproving) return;
        
        setIsApproving(true);
        try {
            const response = await fetch(`${API_BASE}/api/deliverables/${deliverableId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
                },
                body: JSON.stringify({ status: 'approved' })
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `Failed to approve deliverable: ${response.status}`);
            }
            
            console.log('Deliverable approved:', deliverableId);
            
            // Notify parent to refresh deliverables list
            if (onApproved) {
                onApproved(deliverableId);
            }
        } catch (error) {
            console.error('Failed to approve deliverable:', error);
            alert(`Failed to approve: ${error.message}`);
        } finally {
            setIsApproving(false);
        }
    };

    // Enhanced refine handler that can update status
    const handleRefine = (deliverableId, feedback) => {
        // Call the original refine handler
        if (onRefine) {
            onRefine(deliverableId, feedback);
        }
    };

    return (
        <DeliverablesPanel
            deliverables={deliverables}
            selectedId={selectedId}
            onSelect={onSelect}
            onRefine={handleRefine}
            phase={phase}
            progress={progress}
            statusMessage={statusMessage}
        />
    );
}