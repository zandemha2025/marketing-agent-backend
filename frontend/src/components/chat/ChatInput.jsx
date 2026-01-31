import React, { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Auto-growing textarea input with send-on-Enter behavior.
 */
export default function ChatInput({ onSend, disabled = false }) {
    const [value, setValue] = useState('');
    const textareaRef = useRef(null);

    const adjustHeight = useCallback(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 96) + 'px';
    }, []);

    useEffect(() => {
        adjustHeight();
    }, [value, adjustHeight]);

    const handleSend = useCallback(() => {
        const trimmed = value.trim();
        if (!trimmed || disabled) return;
        onSend(trimmed);
        setValue('');
        // Reset height after clearing
        requestAnimationFrame(() => {
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        });
    }, [value, disabled, onSend]);

    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }, [handleSend]);

    return (
        <div className={`chat-input${disabled ? ' chat-input--disabled' : ''}`}>
            <textarea
                ref={textareaRef}
                className="chat-input__textarea"
                placeholder="Send a message..."
                rows={1}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={disabled}
            />
            <button
                className="chat-input__send"
                onClick={handleSend}
                disabled={disabled || !value.trim()}
                title="Send message"
            >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
            </button>
        </div>
    );
}
