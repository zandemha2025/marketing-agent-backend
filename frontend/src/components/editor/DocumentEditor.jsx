import React, { useState, useRef, useCallback, useEffect } from 'react';
import './DocumentEditor.css';

/**
 * DocumentEditor - A Jasper-style inline document editor.
 * Supports real-time AI suggestions, formatting, and collaborative editing.
 *
 * Props:
 * - content: string - Initial content
 * - onChange: function - Called when content changes
 * - onAIRequest: function - Called when AI assistance is requested
 * - documentType: string - Type of document (blog, email, social, ad)
 * - placeholder: string - Placeholder text
 * - readOnly: boolean - Whether editor is read-only
 * - showToolbar: boolean - Whether to show formatting toolbar
 * - aiSuggestions: boolean - Whether to show AI suggestions
 */
function DocumentEditor({
    content = '',
    onChange,
    onAIRequest,
    documentType = 'general',
    placeholder = 'Start writing...',
    readOnly = false,
    showToolbar = true,
    aiSuggestions = true,
}) {
    const [editorContent, setEditorContent] = useState(content);
    const [selectedText, setSelectedText] = useState('');
    const [showAIMenu, setShowAIMenu] = useState(false);
    const [aiMenuPosition, setAIMenuPosition] = useState({ x: 0, y: 0 });
    const [isGenerating, setIsGenerating] = useState(false);
    const [suggestion, setSuggestion] = useState('');
    const editorRef = useRef(null);
    const textareaRef = useRef(null);

    // Sync external content changes
    useEffect(() => {
        if (content !== editorContent) {
            setEditorContent(content);
        }
    }, [content]);

    const handleContentChange = useCallback((e) => {
        const newContent = e.target.value;
        setEditorContent(newContent);
        onChange?.(newContent);
    }, [onChange]);

    const handleTextSelect = useCallback(() => {
        if (!aiSuggestions) return;

        const textarea = textareaRef.current;
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selected = editorContent.substring(start, end);

        if (selected.length > 0) {
            setSelectedText(selected);

            // Get position for AI menu
            const rect = textarea.getBoundingClientRect();
            const lineHeight = 24;
            const lines = editorContent.substring(0, start).split('\n').length;

            setAIMenuPosition({
                x: rect.left + 20,
                y: rect.top + (lines * lineHeight) + 40,
            });
            setShowAIMenu(true);
        } else {
            setShowAIMenu(false);
            setSelectedText('');
        }
    }, [editorContent, aiSuggestions]);

    const handleAIAction = useCallback(async (action) => {
        if (!onAIRequest || !selectedText) return;

        setIsGenerating(true);
        setShowAIMenu(false);

        try {
            const result = await onAIRequest(action, selectedText, documentType);
            if (result) {
                // Replace selected text with AI result
                const textarea = textareaRef.current;
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;

                const newContent =
                    editorContent.substring(0, start) +
                    result +
                    editorContent.substring(end);

                setEditorContent(newContent);
                onChange?.(newContent);
            }
        } catch (err) {
            console.error('AI request failed:', err);
        } finally {
            setIsGenerating(false);
        }
    }, [onAIRequest, selectedText, documentType, editorContent, onChange]);

    const insertText = useCallback((text) => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;

        const newContent =
            editorContent.substring(0, start) +
            text +
            editorContent.substring(end);

        setEditorContent(newContent);
        onChange?.(newContent);

        // Set cursor position after inserted text
        setTimeout(() => {
            textarea.selectionStart = textarea.selectionEnd = start + text.length;
            textarea.focus();
        }, 0);
    }, [editorContent, onChange]);

    const formatText = useCallback((format) => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selected = editorContent.substring(start, end);

        let formatted;
        switch (format) {
            case 'bold':
                formatted = `**${selected}**`;
                break;
            case 'italic':
                formatted = `*${selected}*`;
                break;
            case 'heading':
                formatted = `## ${selected}`;
                break;
            case 'bullet':
                formatted = selected.split('\n').map(line => `- ${line}`).join('\n');
                break;
            case 'numbered':
                formatted = selected.split('\n').map((line, i) => `${i + 1}. ${line}`).join('\n');
                break;
            case 'quote':
                formatted = `> ${selected}`;
                break;
            case 'code':
                formatted = `\`${selected}\``;
                break;
            default:
                formatted = selected;
        }

        const newContent =
            editorContent.substring(0, start) +
            formatted +
            editorContent.substring(end);

        setEditorContent(newContent);
        onChange?.(newContent);
    }, [editorContent, onChange]);

    // AI Action Menu Items
    const aiActions = [
        { key: 'improve', label: 'Improve Writing', icon: '✨' },
        { key: 'expand', label: 'Expand', icon: '📝' },
        { key: 'shorten', label: 'Make Shorter', icon: '📐' },
        { key: 'professional', label: 'More Professional', icon: '👔' },
        { key: 'casual', label: 'More Casual', icon: '😊' },
        { key: 'persuasive', label: 'More Persuasive', icon: '🎯' },
    ];

    return (
        <div className={`document-editor ${readOnly ? 'document-editor--readonly' : ''}`} ref={editorRef}>
            {/* Toolbar */}
            {showToolbar && !readOnly && (
                <div className="document-editor__toolbar">
                    <div className="toolbar-group">
                        <button
                            className="toolbar-btn"
                            onClick={() => formatText('bold')}
                            title="Bold"
                        >
                            <strong>B</strong>
                        </button>
                        <button
                            className="toolbar-btn"
                            onClick={() => formatText('italic')}
                            title="Italic"
                        >
                            <em>I</em>
                        </button>
                        <button
                            className="toolbar-btn"
                            onClick={() => formatText('heading')}
                            title="Heading"
                        >
                            H
                        </button>
                    </div>
                    <div className="toolbar-divider" />
                    <div className="toolbar-group">
                        <button
                            className="toolbar-btn"
                            onClick={() => formatText('bullet')}
                            title="Bullet List"
                        >
                            •
                        </button>
                        <button
                            className="toolbar-btn"
                            onClick={() => formatText('numbered')}
                            title="Numbered List"
                        >
                            1.
                        </button>
                        <button
                            className="toolbar-btn"
                            onClick={() => formatText('quote')}
                            title="Quote"
                        >
                            "
                        </button>
                    </div>
                    {aiSuggestions && (
                        <>
                            <div className="toolbar-divider" />
                            <div className="toolbar-group">
                                <button
                                    className="toolbar-btn toolbar-btn--ai"
                                    onClick={() => handleAIAction('improve')}
                                    disabled={isGenerating}
                                    title="AI Improve"
                                >
                                    ✨ AI
                                </button>
                            </div>
                        </>
                    )}
                    {isGenerating && (
                        <div className="toolbar-status">
                            <span className="generating-indicator">Generating...</span>
                        </div>
                    )}
                </div>
            )}

            {/* Editor Area */}
            <div className="document-editor__body">
                <textarea
                    ref={textareaRef}
                    className="document-editor__textarea"
                    value={editorContent}
                    onChange={handleContentChange}
                    onSelect={handleTextSelect}
                    onBlur={() => setTimeout(() => setShowAIMenu(false), 200)}
                    placeholder={placeholder}
                    readOnly={readOnly}
                    spellCheck
                />

                {/* Word/Character Count */}
                <div className="document-editor__stats">
                    <span>{editorContent.split(/\s+/).filter(w => w).length} words</span>
                    <span>{editorContent.length} characters</span>
                </div>
            </div>

            {/* AI Suggestion Menu */}
            {showAIMenu && selectedText && (
                <div
                    className="ai-menu"
                    style={{
                        position: 'fixed',
                        left: aiMenuPosition.x,
                        top: aiMenuPosition.y,
                    }}
                >
                    <div className="ai-menu__header">
                        <span>✨ AI Actions</span>
                    </div>
                    <div className="ai-menu__actions">
                        {aiActions.map(action => (
                            <button
                                key={action.key}
                                className="ai-menu__action"
                                onClick={() => handleAIAction(action.key)}
                            >
                                <span className="ai-menu__action-icon">{action.icon}</span>
                                <span>{action.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Suggestion Overlay */}
            {suggestion && (
                <div className="suggestion-overlay">
                    <div className="suggestion-content">
                        <span className="suggestion-text">{suggestion}</span>
                        <div className="suggestion-actions">
                            <button
                                className="suggestion-btn suggestion-btn--accept"
                                onClick={() => {
                                    insertText(suggestion);
                                    setSuggestion('');
                                }}
                            >
                                Accept (Tab)
                            </button>
                            <button
                                className="suggestion-btn suggestion-btn--dismiss"
                                onClick={() => setSuggestion('')}
                            >
                                Dismiss (Esc)
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default DocumentEditor;
