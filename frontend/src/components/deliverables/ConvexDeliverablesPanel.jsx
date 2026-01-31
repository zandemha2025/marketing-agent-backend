/**
 * Convex-Powered Deliverables Panel
 *
 * This component wraps DeliverablesPanel and connects it to Convex
 * for real-time deliverables updates. Deliverables appear instantly
 * as they're created by the backend orchestrator.
 */

import React, { useMemo } from 'react';
import { useSubscribeToDeliverables, useUpdateDeliverableStatus } from '../../hooks/useConvex';
import DeliverablesPanel from './DeliverablesPanel';

/**
 * Transform Convex deliverable format to the format expected by DeliverablesPanel
 */
function transformDeliverable(convexDeliverable) {
    if (!convexDeliverable) return null;

    return {
        id: convexDeliverable._id,
        type: convexDeliverable.type,
        platform: convexDeliverable.platform,
        status: convexDeliverable.status,
        data: convexDeliverable.data || {},
        order: convexDeliverable.order || 0,
        // Add Convex metadata
        _convexId: convexDeliverable._id,
        _creationTime: convexDeliverable._creationTime
    };
}

export default function ConvexDeliverablesPanel({
    campaignId,
    selectedId,
    onSelect,
    onRefine,
    phase = 'producing',
    progress = 0,
    statusMessage = '',
    // Fallback deliverables from WebSocket (for hybrid mode)
    wsDeliverables = []
}) {
    // Subscribe to Convex deliverables for this campaign
    const convexDeliverables = useSubscribeToDeliverables(campaignId);
    const updateStatus = useUpdateDeliverableStatus();

    // Transform and merge deliverables
    // Priority: Convex (real-time) > WebSocket (fallback)
    const deliverables = useMemo(() => {
        if (convexDeliverables && convexDeliverables.length > 0) {
            // Use Convex data - it's real-time and authoritative
            return convexDeliverables
                .map(transformDeliverable)
                .filter(Boolean)
                .sort((a, b) => (b._creationTime || 0) - (a._creationTime || 0));
        }

        // Fall back to WebSocket deliverables if Convex hasn't synced yet
        // This provides a seamless transition during the initial load
        if (wsDeliverables && wsDeliverables.length > 0) {
            return wsDeliverables;
        }

        return [];
    }, [convexDeliverables, wsDeliverables]);

    // Handle approval/status update
    const handleApprove = async (deliverableId) => {
        // Find the Convex ID
        const deliverable = deliverables.find(d => d.id === deliverableId);
        if (deliverable && deliverable._convexId) {
            await updateStatus({
                id: deliverable._convexId,
                status: 'approved'
            });
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
