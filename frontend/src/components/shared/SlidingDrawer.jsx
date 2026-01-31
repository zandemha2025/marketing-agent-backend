import React, { useEffect, useRef } from 'react';
import './SlidingDrawer.css';

/**
 * SlidingDrawer - A panel that slides in from the right side of the screen.
 * Used for deliverables, document previews, asset details, etc.
 *
 * Props:
 * - isOpen: boolean - Whether the drawer is open
 * - onClose: function - Called when drawer should close
 * - title: string - Header title
 * - subtitle: string - Optional subtitle
 * - width: string - Width of drawer (default: '400px')
 * - children: React node - Drawer content
 * - showOverlay: boolean - Whether to show a dark overlay (default: true)
 * - closeOnOverlayClick: boolean - Close when clicking overlay (default: true)
 * - actions: React node - Optional header actions (buttons, etc.)
 */
function SlidingDrawer({
    isOpen,
    onClose,
    title,
    subtitle,
    width = '400px',
    children,
    showOverlay = true,
    closeOnOverlayClick = true,
    actions,
}) {
    const drawerRef = useRef(null);

    // Handle escape key
    useEffect(() => {
        const handleEscape = (e) => {
            if (e.key === 'Escape' && isOpen) {
                onClose?.();
            }
        };

        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, [isOpen, onClose]);

    // Prevent body scroll when open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => {
            document.body.style.overflow = '';
        };
    }, [isOpen]);

    const handleOverlayClick = () => {
        if (closeOnOverlayClick) {
            onClose?.();
        }
    };

    return (
        <div className={`sliding-drawer-container ${isOpen ? 'sliding-drawer-container--open' : ''}`}>
            {/* Overlay */}
            {showOverlay && (
                <div
                    className="sliding-drawer-overlay"
                    onClick={handleOverlayClick}
                    aria-hidden="true"
                />
            )}

            {/* Drawer */}
            <div
                ref={drawerRef}
                className="sliding-drawer"
                style={{ width }}
                role="dialog"
                aria-modal="true"
                aria-labelledby="drawer-title"
            >
                {/* Header */}
                <div className="sliding-drawer__header">
                    <div className="sliding-drawer__header-content">
                        <button
                            className="sliding-drawer__close"
                            onClick={onClose}
                            aria-label="Close drawer"
                        >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="18" y1="6" x2="6" y2="18" />
                                <line x1="6" y1="6" x2="18" y2="18" />
                            </svg>
                        </button>
                        <div className="sliding-drawer__titles">
                            <h2 id="drawer-title" className="sliding-drawer__title">{title}</h2>
                            {subtitle && (
                                <span className="sliding-drawer__subtitle">{subtitle}</span>
                            )}
                        </div>
                    </div>
                    {actions && (
                        <div className="sliding-drawer__actions">
                            {actions}
                        </div>
                    )}
                </div>

                {/* Content */}
                <div className="sliding-drawer__content">
                    {children}
                </div>
            </div>
        </div>
    );
}

export default SlidingDrawer;
