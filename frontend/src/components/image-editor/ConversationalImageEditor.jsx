import React, { useState, useCallback, useRef, useEffect } from 'react';
import api from '../../services/api';
import './ConversationalImageEditor.css';

/**
 * ConversationalImageEditor - AI-powered image editing with natural language.
 *
 * Features:
 * - Natural language editing commands
 * - Real-time preview
 * - Version history
 * - Quick preset adjustments
 * - Export in multiple formats
 */

const QUICK_ACTIONS = [
    { key: 'remove-bg', label: 'Remove Background', icon: '✂️', prompt: 'Remove the background' },
    { key: 'enhance', label: 'Enhance Quality', icon: '✨', prompt: 'Enhance image quality and clarity' },
    { key: 'resize-social', label: 'Resize for Social', icon: '📐', prompt: 'Resize to Instagram square (1080x1080)' },
    { key: 'add-text', label: 'Add Text', icon: '🔤', prompt: 'Add promotional text overlay' },
    { key: 'filters', label: 'Apply Filter', icon: '🎨', prompt: 'Apply a professional marketing filter' },
    { key: 'crop', label: 'Smart Crop', icon: '⬜', prompt: 'Crop to focus on the main subject' },
];

const EXPORT_FORMATS = [
    { key: 'png', label: 'PNG', description: 'Lossless, transparent background' },
    { key: 'jpg', label: 'JPG', description: 'Smaller file size' },
    { key: 'webp', label: 'WebP', description: 'Modern web format' },
];

const SOCIAL_PRESETS = [
    { key: 'ig-square', label: 'Instagram Square', size: '1080x1080' },
    { key: 'ig-story', label: 'Instagram Story', size: '1080x1920' },
    { key: 'fb-post', label: 'Facebook Post', size: '1200x630' },
    { key: 'twitter', label: 'Twitter Post', size: '1200x675' },
    { key: 'linkedin', label: 'LinkedIn Post', size: '1200x627' },
    { key: 'youtube', label: 'YouTube Thumbnail', size: '1280x720' },
];

export default function ConversationalImageEditor({
    organizationId,
    initialImage = null,
    onSave,
    onExport,
    campaignId = null,
    deliverableId = null,
    isProcessing: externalIsProcessing = false,
}) {
    const [image, setImage] = useState(initialImage);
    const [sessionId, setSessionId] = useState(null);
    const [isProcessing, setIsProcessing] = useState(externalIsProcessing);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [isUploading, setIsUploading] = useState(false);
    const [prompt, setPrompt] = useState('');
    const [history, setHistory] = useState([]);
    const [currentVersion, setCurrentVersion] = useState(0);
    const [selectedPreset, setSelectedPreset] = useState(null);
    const [showExportModal, setShowExportModal] = useState(false);
    const [chatMessages, setChatMessages] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const [uploadError, setUploadError] = useState(null);
    const fileInputRef = useRef(null);
    const chatEndRef = useRef(null);

    // Scroll chat to bottom on new messages
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatMessages]);

    const handleImageUpload = useCallback(async (file) => {
        if (!file || !file.type.startsWith('image/')) {
            setUploadError('Please select a valid image file (PNG, JPG, WebP, GIF)');
            return;
        }

        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            setUploadError('Image too large. Maximum size is 10MB.');
            return;
        }

        setIsUploading(true);
        setUploadProgress(0);
        setUploadError(null);

        try {
            // Upload to S3 via API
            const uploadResult = await api.uploadImage(file, (progress) => {
                setUploadProgress(progress);
            });

            // Create preview from file
            const reader = new FileReader();
            reader.onload = async (e) => {
                const newImage = e.target.result;
                setImage(newImage);
                setHistory([newImage]);
                setCurrentVersion(0);
                setChatMessages([
                    {
                        role: 'assistant',
                        content: 'Great! I\'ve uploaded your image. What would you like me to do with it? You can describe any edit in natural language, like "remove the background" or "make it look more vibrant".',
                    }
                ]);

                // Create a new session in the backend with the uploaded URL
                if (organizationId) {
                    try {
                        const sessionData = {
                            title: file.name || 'Untitled Image',
                            original_image_url: uploadResult.url,
                            organization_id: organizationId,
                        };

                        if (campaignId) sessionData.campaign_id = campaignId;
                        if (deliverableId) sessionData.deliverable_id = deliverableId;

                        const session = await api.createImageEditSession(sessionData, organizationId);
                        setSessionId(session.id);

                        // Add history entry for the upload
                        await api.addImageEditHistory(session.id, {
                            operation: 'upload',
                            prompt: 'Initial upload',
                            parameters: {
                                original_filename: file.name,
                                uploaded_url: uploadResult.url,
                                size_bytes: uploadResult.size_bytes,
                            },
                            result_image_url: uploadResult.url,
                        });
                    } catch (err) {
                        console.error('Failed to create image session:', err);
                        setChatMessages(prev => [...prev, {
                            role: 'assistant',
                            content: 'Image uploaded successfully, but I couldn\'t create an edit session. You can still edit the image.',
                            isWarning: true,
                        }]);
                    }
                }

                setIsUploading(false);
                setUploadProgress(100);
            };
            reader.readAsDataURL(file);
        } catch (error) {
            console.error('Upload failed:', error);
            setUploadError(`Upload failed: ${error.message}`);
            setIsUploading(false);
            setUploadProgress(0);
        }
    }, [organizationId, campaignId, deliverableId]);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        handleImageUpload(file);
    }, [handleImageUpload]);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleFileSelect = useCallback((e) => {
        const file = e.target.files[0];
        handleImageUpload(file);
    }, [handleImageUpload]);

    const handleSendPrompt = useCallback(async () => {
        if (!prompt.trim() || !image) return;

        const userMessage = prompt.trim();
        setPrompt('');
        setIsProcessing(true);

        // Add user message to chat
        setChatMessages(prev => [...prev, {
            role: 'user',
            content: userMessage,
        }]);

        try {
            // Determine operation based on prompt (simple heuristic for now)
            let operation = 'edit';
            if (userMessage.toLowerCase().includes('generate')) operation = 'generate';
            else if (userMessage.toLowerCase().includes('remove background')) operation = 'remove_background';
            
            let result;
            if (operation === 'generate') {
                result = await api.generateImage({
                    prompt: userMessage,
                    n: 1
                });
            } else {
                result = await api.editImage({
                    operation: operation,
                    prompt: userMessage,
                    parameters: {}
                }, sessionId);
            }

            // Add AI response
            setChatMessages(prev => [...prev, {
                role: 'assistant',
                content: result.message || 'Done! I\'ve applied your edit. What else would you like to change?',
            }]);

            // Update image if edit was successful
            if (result.image_url) {
                // For demo, we might get a placeholder URL. In a real app, we'd fetch the image.
                // Here we'll just use the returned URL directly.
                const newImage = result.image_url;
                
                const newHistory = [...history.slice(0, currentVersion + 1), newImage];
                setHistory(newHistory);
                setCurrentVersion(newHistory.length - 1);
                setImage(newImage);
            }
        } catch (error) {
            console.error('AI Edit error:', error);
            setChatMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Sorry, I couldn\'t process that edit. Could you try rephrasing your request?',
                isError: true,
            }]);
        } finally {
            setIsProcessing(false);
        }
    }, [prompt, image, sessionId, history, currentVersion]);

    const handleQuickAction = useCallback((action) => {
        setPrompt(action.prompt);
        // Auto-send after a brief delay
        setTimeout(() => {
            // We can just call handleSendPrompt here if we update state correctly, 
            // but since handleSendPrompt depends on state that might not be updated yet in this closure,
            // it's safer to trigger it via effect or just duplicate the logic slightly or use a ref.
            // For simplicity, let's just set the prompt and let user press enter or click send for now,
            // OR better: trigger the send logic directly with the prompt text.
            
            // To properly trigger send, we'd need to refactor handleSendPrompt to accept an argument
            // Let's do that in a follow-up or just simulate the click.
            
            // Actually, let's just update the prompt and let the user confirm, 
            // or better, implement a direct call version.
        }, 100);
    }, []);

    // Helper to send a specific message directly
    const sendDirectMessage = useCallback(async (message) => {
        if (!image) return;
        
        setIsProcessing(true);
        setChatMessages(prev => [...prev, {
            role: 'user',
            content: message,
        }]);

        try {
             // Determine operation based on prompt/action key
            let operation = 'edit';
            // Map common phrases to operations
            if (message.includes('Remove the background')) operation = 'remove_background';
            else if (message.includes('Enhance')) operation = 'enhance';
            else if (message.includes('Resize')) operation = 'resize';
            else if (message.includes('Crop')) operation = 'crop';
            else if (message.includes('filter')) operation = 'filter';
            
            const result = await api.editImage({
                operation: operation,
                prompt: message,
                parameters: {}
            }, sessionId);

            setChatMessages(prev => [...prev, {
                role: 'assistant',
                content: result.message || 'Done!',
            }]);

            if (result.image_url) {
                const newImage = result.image_url;
                const newHistory = [...history.slice(0, currentVersion + 1), newImage];
                setHistory(newHistory);
                setCurrentVersion(newHistory.length - 1);
                setImage(newImage);
            }
        } catch (error) {
            console.error('Quick Action error:', error);
            setChatMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Sorry, I encountered an error processing that action.',
                isError: true,
            }]);
        } finally {
            setIsProcessing(false);
        }
    }, [image, sessionId, history, currentVersion]);

    const handleQuickActionClick = useCallback((action) => {
        sendDirectMessage(action.prompt);
    }, [sendDirectMessage]);

    const handleUndo = useCallback(() => {
        if (currentVersion > 0) {
            setCurrentVersion(currentVersion - 1);
            setImage(history[currentVersion - 1]);
        }
    }, [currentVersion, history]);

    const handleRedo = useCallback(() => {
        if (currentVersion < history.length - 1) {
            setCurrentVersion(currentVersion + 1);
            setImage(history[currentVersion + 1]);
        }
    }, [currentVersion, history]);

    const handleExport = useCallback((format) => {
        if (onExport) {
            onExport(image, format);
        }
        setShowExportModal(false);
    }, [image, onExport]);

    const handlePresetSelect = useCallback((preset) => {
        setSelectedPreset(preset);
        setPrompt(`Resize to ${preset.size} (${preset.label})`);
    }, []);

    return (
        <div className="conversational-image-editor">
            {/* Header */}
            <div className="cie-header">
                <div className="cie-header__title">
                    <h2>🎨 AI Image Editor</h2>
                    <span className="cie-header__subtitle">Edit with natural language</span>
                </div>
                <div className="cie-header__actions">
                    {image && (
                        <>
                            <button
                                className="cie-btn"
                                onClick={handleUndo}
                                disabled={currentVersion === 0}
                                title="Undo"
                            >
                                ↩️ Undo
                            </button>
                            <button
                                className="cie-btn"
                                onClick={handleRedo}
                                disabled={currentVersion >= history.length - 1}
                                title="Redo"
                            >
                                ↪️ Redo
                            </button>
                            <button
                                className="cie-btn cie-btn--primary"
                                onClick={() => setShowExportModal(true)}
                            >
                                📥 Export
                            </button>
                        </>
                    )}
                </div>
            </div>

            <div className="cie-main">
                {/* Image Canvas */}
                <div className="cie-canvas">
                    {!image ? (
                        <div
                            className={`cie-upload-zone ${isDragging ? 'cie-upload-zone--dragging' : ''}`}
                            onDrop={handleDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <div className="cie-upload-zone__icon">🖼️</div>
                            <h3>Drop image here or click to upload</h3>
                            <p>Supports PNG, JPG, WebP up to 10MB</p>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                onChange={handleFileSelect}
                                hidden
                            />
                        </div>
                    ) : (
                        <div className="cie-image-container">
                            <img
                                src={image}
                                alt="Editing"
                                className={`cie-image ${isProcessing ? 'cie-image--processing' : ''}`}
                            />
                            {isProcessing && (
                                <div className="cie-processing-overlay">
                                    <div className="cie-spinner" />
                                    <span>Processing...</span>
                                </div>
                            )}
                            <div className="cie-image-info">
                                Version {currentVersion + 1} of {history.length}
                            </div>
                        </div>
                    )}
                </div>

                {/* Chat/Controls Panel */}
                <div className="cie-panel">
                    {/* Quick Actions */}
                    <div className="cie-quick-actions">
                        <h4>Quick Actions</h4>
                        <div className="cie-quick-actions__grid">
                            {QUICK_ACTIONS.map(action => (
                                <button
                                    key={action.key}
                                    className="cie-quick-action"
                                    onClick={() => handleQuickActionClick(action)}
                                    disabled={!image || isProcessing}
                                >
                                    <span className="cie-quick-action__icon">{action.icon}</span>
                                    <span className="cie-quick-action__label">{action.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Social Presets */}
                    <div className="cie-presets">
                        <h4>Social Media Sizes</h4>
                        <div className="cie-presets__list">
                            {SOCIAL_PRESETS.map(preset => (
                                <button
                                    key={preset.key}
                                    className={`cie-preset ${selectedPreset?.key === preset.key ? 'cie-preset--selected' : ''}`}
                                    onClick={() => handlePresetSelect(preset)}
                                    disabled={!image}
                                >
                                    <span className="cie-preset__label">{preset.label}</span>
                                    <span className="cie-preset__size">{preset.size}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Chat Interface */}
                    <div className="cie-chat">
                        <div className="cie-chat__messages">
                            {chatMessages.length === 0 ? (
                                <div className="cie-chat__welcome">
                                    <span className="cie-chat__welcome-icon">💬</span>
                                    <p>Upload an image to start editing with AI</p>
                                </div>
                            ) : (
                                chatMessages.map((msg, idx) => (
                                    <div
                                        key={idx}
                                        className={`cie-message cie-message--${msg.role} ${msg.isError ? 'cie-message--error' : ''}`}
                                    >
                                        {msg.content}
                                    </div>
                                ))
                            )}
                            <div ref={chatEndRef} />
                        </div>

                        <div className="cie-chat__input">
                            <input
                                type="text"
                                placeholder={image ? 'Describe your edit...' : 'Upload an image first'}
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSendPrompt()}
                                disabled={!image || isProcessing}
                            />
                            <button
                                className="cie-chat__send"
                                onClick={handleSendPrompt}
                                disabled={!image || !prompt.trim() || isProcessing}
                            >
                                ✨
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Export Modal */}
            {showExportModal && (
                <div className="cie-modal-overlay" onClick={() => setShowExportModal(false)}>
                    <div className="cie-modal" onClick={e => e.stopPropagation()}>
                        <h3>Export Image</h3>
                        <div className="cie-export-formats">
                            {EXPORT_FORMATS.map(format => (
                                <button
                                    key={format.key}
                                    className="cie-export-option"
                                    onClick={() => handleExport(format.key)}
                                >
                                    <span className="cie-export-option__label">{format.label}</span>
                                    <span className="cie-export-option__desc">{format.description}</span>
                                </button>
                            ))}
                        </div>
                        <button
                            className="cie-modal__close"
                            onClick={() => setShowExportModal(false)}
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
