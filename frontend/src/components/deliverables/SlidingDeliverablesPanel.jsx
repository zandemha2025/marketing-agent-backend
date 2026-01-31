import React, { useState, useCallback } from 'react';
import SlidingDrawer from '../shared/SlidingDrawer';
import DocumentEditor from '../editor/DocumentEditor';
import DeliverablesPanel from './DeliverablesPanel';
import './SlidingDeliverablesPanel.css';

/**
 * SlidingDeliverablesPanel - Enhanced deliverables panel in a sliding drawer.
 *
 * Features:
 * - Slides in from the right side
 * - Shows list of deliverables
 * - Click any deliverable to edit with Jasper-style editor
 * - AI-powered content refinement
 * - Export/copy functionality
 */

const TYPE_INFO = {
    social_post: { icon: '📱', label: 'Social Post', color: '#6366f1' },
    email: { icon: '✉️', label: 'Email', color: '#10b981' },
    ad: { icon: '📢', label: 'Ad Copy', color: '#f59e0b' },
    blog_post: { icon: '📝', label: 'Blog Post', color: '#ec4899' },
    landing_page: { icon: '🌐', label: 'Landing Page', color: '#06b6d4' },
    video: { icon: '🎬', label: 'Video Script', color: '#ef4444' },
    strategy_doc: { icon: '📊', label: 'Strategy', color: '#8b5cf6' },
};

export default function SlidingDeliverablesPanel({
    isOpen,
    onClose,
    deliverables = [],
    selectedId,
    onSelect,
    onRefine,
    onSave,
    onGenerate,
    campaignName = 'Campaign',
    phase = 'ready',
    progress = 1,
    statusMessage = '',
}) {
    const [editingDeliverable, setEditingDeliverable] = useState(null);
    const [editedContent, setEditedContent] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // Find the selected deliverable
    const selectedDeliverable = deliverables.find(d => d.id === selectedId);

    const handleSelectDeliverable = useCallback((id) => {
        const deliverable = deliverables.find(d => d.id === id);
        if (deliverable) {
            setEditingDeliverable(deliverable);
            setEditedContent(deliverable.content || deliverable.text || '');
        }
        onSelect?.(id);
    }, [deliverables, onSelect]);

    const handleBackToList = useCallback(() => {
        setEditingDeliverable(null);
        onSelect?.(null);
    }, [onSelect]);

    const handleContentChange = useCallback((newContent) => {
        setEditedContent(newContent);
    }, []);

    const handleAIRequest = useCallback(async (action, text, type) => {
        // Call parent's onRefine or onGenerate for AI actions
        if (onGenerate) {
            try {
                const result = await onGenerate(action, text, type);
                return result;
            } catch (err) {
                console.error('AI action failed:', err);
                return text;
            }
        }
        return text;
    }, [onGenerate]);

    const handleSave = useCallback(async () => {
        if (!editingDeliverable) return;

        setIsSaving(true);
        try {
            if (onSave) {
                await onSave({
                    ...editingDeliverable,
                    content: editedContent,
                    text: editedContent,
                    updatedAt: new Date().toISOString(),
                });
            }
        } catch (err) {
            console.error('Save failed:', err);
        } finally {
            setIsSaving(false);
        }
    }, [editingDeliverable, editedContent, onSave]);

    const handleCopy = useCallback(() => {
        navigator.clipboard.writeText(editedContent);
    }, [editedContent]);

    const handleExport = useCallback(() => {
        const blob = new Blob([editedContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${editingDeliverable?.title || 'deliverable'}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }, [editedContent, editingDeliverable]);

    const getTypeInfo = (type) => TYPE_INFO[type] || { icon: '📄', label: 'Document', color: '#888' };

    // Render editor view when a deliverable is selected for editing
    const renderEditorView = () => {
        if (!editingDeliverable) return null;

        const typeInfo = getTypeInfo(editingDeliverable.type);

        return (
            <div className="sdp-editor">
                {/* Editor Header */}
                <div className="sdp-editor__header">
                    <button className="sdp-editor__back" onClick={handleBackToList}>
                        ← Back
                    </button>
                    <div className="sdp-editor__type" style={{ backgroundColor: typeInfo.color + '20' }}>
                        {typeInfo.icon} {typeInfo.label}
                    </div>
                </div>

                {/* Title */}
                <div className="sdp-editor__title-row">
                    <input
                        type="text"
                        className="sdp-editor__title-input"
                        value={editingDeliverable.title || ''}
                        onChange={(e) => setEditingDeliverable({
                            ...editingDeliverable,
                            title: e.target.value
                        })}
                        placeholder="Enter title..."
                    />
                    {editingDeliverable.platform && (
                        <span className="sdp-editor__platform">{editingDeliverable.platform}</span>
                    )}
                </div>

                {/* Document Editor */}
                <div className="sdp-editor__content">
                    <DocumentEditor
                        content={editedContent}
                        onChange={handleContentChange}
                        onAIRequest={handleAIRequest}
                        documentType={editingDeliverable.type}
                        placeholder={`Write your ${typeInfo.label.toLowerCase()} content...`}
                    />
                </div>

                {/* Action Bar */}
                <div className="sdp-editor__actions">
                    <button className="sdp-action-btn" onClick={handleCopy} title="Copy to clipboard">
                        📋 Copy
                    </button>
                    <button className="sdp-action-btn" onClick={handleExport} title="Download as file">
                        ⬇️ Export
                    </button>
                    <button
                        className="sdp-action-btn sdp-action-btn--primary"
                        onClick={handleSave}
                        disabled={isSaving}
                    >
                        {isSaving ? '💾 Saving...' : '💾 Save'}
                    </button>
                </div>
            </div>
        );
    };

    return (
        <SlidingDrawer
            isOpen={isOpen}
            onClose={onClose}
            title="Deliverables"
            subtitle={campaignName}
            width="600px"
            actions={
                editingDeliverable ? null : (
                    <button
                        className="sdp-generate-btn"
                        onClick={() => onGenerate?.('create', '', 'social_post')}
                    >
                        + Generate
                    </button>
                )
            }
        >
            {editingDeliverable ? (
                renderEditorView()
            ) : (
                <DeliverablesPanel
                    deliverables={deliverables}
                    selectedId={selectedId}
                    onSelect={handleSelectDeliverable}
                    onRefine={onRefine}
                    phase={phase}
                    progress={progress}
                    statusMessage={statusMessage}
                />
            )}
        </SlidingDrawer>
    );
}
