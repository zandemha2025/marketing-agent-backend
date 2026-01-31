import React from 'react';

/**
 * Renders a single chat message bubble.
 * Handles user (right-aligned, accent) and assistant (left-aligned, dark) styles.
 */

// Simple HTML sanitizer - only allows safe tags
function sanitizeHtml(html) {
    if (!html) return '';
    // Remove script tags and event handlers
    let clean = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    clean = clean.replace(/on\w+="[^"]*"/gi, '');
    clean = clean.replace(/on\w+='[^']*'/gi, '');
    // Only allow safe tags
    const allowedTags = ['strong', 'em', 'b', 'i', 'br', 'p', 'ul', 'ol', 'li', 'code', 'pre'];
    const tagRegex = /<\/?([a-z][a-z0-9]*)\b[^>]*>/gi;
    clean = clean.replace(tagRegex, (match, tag) => {
        return allowedTags.includes(tag.toLowerCase()) ? match : '';
    });
    return clean;
}

function formatContent(text) {
    if (!text) return '';
    // Escape HTML first
    let escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    // Bold: **text**
    let html = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic: *text*
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Code: `text`
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');
    // Line breaks
    html = html.replace(/\n/g, '<br/>');
    return html;
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function ChatMessage({ message }) {
    const { role, content, created_at } = message;
    const isUser = role === 'user';

    return (
        <div className={`chat-message chat-message--${role}`}>
            <div
                className="chat-message__bubble"
                dangerouslySetInnerHTML={{ __html: formatContent(content) }}
            />
            {created_at && (
                <span className="chat-message__time">{formatTime(created_at)}</span>
            )}
        </div>
    );
}
