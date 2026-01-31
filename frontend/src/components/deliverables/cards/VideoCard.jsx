import React, { useState, useRef } from 'react';
import './DeliverableCards.css';

function VideoCard({ deliverable, isSelected, onSelect, onRefine }) {
    const [isPlaying, setIsPlaying] = useState(false);
    const [showScript, setShowScript] = useState(false);
    const videoRef = useRef(null);
    const { data, platform, status } = deliverable;

    const videoUrl = data?.video_url;
    const duration = data?.duration_seconds || 0;
    const script = data?.script || '';
    const hasVoiceover = data?.has_voiceover;
    const aspectRatio = data?.aspect_ratio || '16:9';

    const togglePlay = (e) => {
        e.stopPropagation();
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.pause();
            } else {
                videoRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    const formatDuration = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div
            className={`deliverable-card video-card ${isSelected ? 'deliverable-card--selected' : ''} ${status === 'generating' ? 'deliverable-card--generating' : ''}`}
            onClick={onSelect}
        >
            {/* Header */}
            <div className="video-card__header">
                <span className="video-card__icon">🎬</span>
                <span className="video-card__label">
                    {platform === 'tiktok' ? 'TikTok' :
                     platform === 'reels' ? 'Reels' :
                     platform === 'shorts' ? 'Shorts' : 'Video'}
                </span>
                <span className="video-card__duration">{formatDuration(duration)}</span>
            </div>

            {/* Video Player */}
            <div className={`video-card__player video-card__player--${aspectRatio.replace(':', 'x')}`}>
                {videoUrl ? (
                    <>
                        <video
                            ref={videoRef}
                            src={videoUrl}
                            loop
                            muted={!hasVoiceover}
                            playsInline
                            onEnded={() => setIsPlaying(false)}
                        />
                        <button
                            className={`video-card__play-btn ${isPlaying ? 'video-card__play-btn--playing' : ''}`}
                            onClick={togglePlay}
                        >
                            {isPlaying ? '⏸' : '▶'}
                        </button>
                    </>
                ) : (
                    <div className="video-card__placeholder">
                        <span>🎬</span>
                        <p>Video generating...</p>
                    </div>
                )}
            </div>

            {/* Video Info */}
            <div className="video-card__info">
                <div className="video-card__badges">
                    <span className={`badge badge--${aspectRatio === '9:16' ? 'vertical' : 'horizontal'}`}>
                        {aspectRatio === '9:16' ? '📱 Vertical' : '🖥️ Horizontal'}
                    </span>
                    {hasVoiceover && <span className="badge badge--audio">🔊 Voiceover</span>}
                    {data?.has_captions && <span className="badge badge--captions">CC</span>}
                </div>
            </div>

            {/* Script Toggle */}
            {script && (
                <div className="video-card__script">
                    <button
                        className="script-toggle"
                        onClick={(e) => { e.stopPropagation(); setShowScript(!showScript); }}
                    >
                        📜 {showScript ? 'Hide Script' : 'View Script'}
                    </button>
                    {showScript && (
                        <div className="script-content">
                            <pre>{script}</pre>
                        </div>
                    )}
                </div>
            )}

            {/* Status */}
            <div className={`video-card__status video-card__status--${status}`}>
                {status === 'generating' ? '⏳ Rendering...' :
                 status === 'ready' ? '✓ Ready' :
                 status === 'approved' ? '✓✓ Approved' : status}
            </div>
        </div>
    );
}

export default VideoCard;
