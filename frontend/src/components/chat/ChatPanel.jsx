import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import api from '../../services/api';
import './ChatPanel.css';

/**
 * Main chat panel: message list, SSE streaming, auto-scroll, welcome state.
 */
export default function ChatPanel({ organizationId, conversationId, onConversationChange }) {
    const [messages, setMessages] = useState([]);
    const [streaming, setStreaming] = useState(false);
    const [error, setError] = useState(null);
    const [activeConvId, setActiveConvId] = useState(conversationId);
    const messagesEndRef = useRef(null);
    const abortRef = useRef(null);

    // Sync prop to local state
    useEffect(() => {
        setActiveConvId(conversationId);
    }, [conversationId]);

    // Load messages when conversation changes
    useEffect(() => {
        if (!activeConvId) {
            setMessages([]);
            return;
        }

        let cancelled = false;

        async function load() {
            try {
                const data = await api.getConversation(activeConvId);
                if (!cancelled) {
                    setMessages(data.messages || []);
                }
            } catch (err) {
                if (!cancelled) setError(err.message);
            }
        }

        load();
        return () => { cancelled = true; };
    }, [activeConvId]);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Create conversation if needed, then send + stream response
    const handleSend = useCallback(async (content) => {
        setError(null);
        let convId = activeConvId;

        // Create conversation if none exists
        if (!convId) {
            try {
                const conv = await api.createConversation(organizationId, content.slice(0, 60), 'general');
                convId = conv.id;
                setActiveConvId(convId);
                if (onConversationChange) onConversationChange(convId);
            } catch (err) {
                setError(err.message);
                return;
            }
        }

        // Add user message optimistically
        const userMsg = { role: 'user', content, created_at: new Date().toISOString() };
        setMessages((prev) => [...prev, userMsg]);

        // Stream assistant response via SSE
        setStreaming(true);
        const assistantMsg = { role: 'assistant', content: '', created_at: null };
        setMessages((prev) => [...prev, { ...assistantMsg }]);

        try {
            let fullContent = '';
            
            await api.streamMessage(
                convId,
                content,
                // onChunk callback - update message as chunks arrive
                (chunk) => {
                    fullContent += chunk;
                    setMessages((prev) => {
                        const updated = [...prev];
                        updated[updated.length - 1] = {
                            role: 'assistant',
                            content: fullContent,
                            created_at: new Date().toISOString(),
                        };
                        return updated;
                    });
                },
                // onDone callback - ensure final content is set
                (finalContent) => {
                    setMessages((prev) => {
                        const updated = [...prev];
                        updated[updated.length - 1] = {
                            role: 'assistant',
                            content: finalContent || '(No response)',
                            created_at: new Date().toISOString(),
                        };
                        return updated;
                    });
                }
            );
        } catch (err) {
            if (err.name !== 'AbortError') {
                setError(err.message);
                // Remove the empty assistant placeholder on error
                setMessages((prev) => {
                    const last = prev[prev.length - 1];
                    if (last?.role === 'assistant' && !last.content) {
                        return prev.slice(0, -1);
                    }
                    return prev;
                });
            }
        } finally {
            setStreaming(false);
            abortRef.current = null;
        }
    }, [activeConvId, organizationId, onConversationChange]);

    const hasMessages = messages.length > 0;

    return (
        <div className="chat-panel">
            <div className="chat-panel__header">
                <div>
                    <h3 className="chat-panel__header-title">Chat</h3>
                    <p className="chat-panel__header-subtitle">
                        {activeConvId ? 'Conversation active' : 'Start a new conversation'}
                    </p>
                </div>
            </div>

            {!hasMessages ? (
                <div className="chat-panel__welcome">
                    <div className="chat-panel__welcome-icon">&#x2728;</div>
                    <h2>How can I help?</h2>
                    <p>
                        Ask me anything about your marketing strategy, campaigns, content, or analytics.
                        I can help you plan, create, and optimize.
                    </p>
                </div>
            ) : (
                <div className="chat-panel__messages">
                    {messages.map((msg, i) => (
                        <ChatMessage key={i} message={msg} />
                    ))}
                    {streaming && (
                        <div className="chat-panel__streaming">
                            <div className="chat-panel__streaming-dots">
                                <span /><span /><span />
                            </div>
                            AI is thinking...
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            )}

            {error && (
                <div className="chat-panel__error">
                    {error}
                    <button className="chat-panel__error-dismiss" onClick={() => setError(null)}>
                        Dismiss
                    </button>
                </div>
            )}

            <div className="chat-panel__input-area">
                <ChatInput onSend={handleSend} disabled={streaming} />
            </div>
        </div>
    );
}
