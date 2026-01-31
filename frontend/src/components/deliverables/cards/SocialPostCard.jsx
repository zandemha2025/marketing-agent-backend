import React, { useState } from 'react';
import './DeliverableCards.css';

const PLATFORM_ICONS = {
    instagram: '📷',
    tiktok: '🎵',
    twitter: '🐦',
    linkedin: '💼',
    facebook: '👤',
};

const PLATFORM_COLORS = {
    instagram: '#E1306C',
    tiktok: '#00f2ea',
    twitter: '#1DA1F2',
    linkedin: '#0077B5',
    facebook: '#4267B2',
};

function SocialPostCard({ deliverable, isSelected, onSelect, onRefine }) {
    const [showFullCaption, setShowFullCaption] = useState(false);
    const { data, platform, status } = deliverable;

    const icon = PLATFORM_ICONS[platform] || '📱';
    const accentColor = PLATFORM_COLORS[platform] || '#6366f1';
    const mediaType = data?.media_type || 'image';

    const caption = data?.caption || '';
    const truncatedCaption = caption.length > 120 ? caption.slice(0, 120) + '...' : caption;
    const hashtags = data?.hashtags || [];

    return (
        <div
            className={`deliverable-card social-post-card ${isSelected ? 'deliverable-card--selected' : ''} ${status === 'generating' ? 'deliverable-card--generating' : ''}`}
            onClick={onSelect}
            style={{ '--accent-color': accentColor }}
        >
            {/* Platform Badge */}
            <div className="social-post-card__header">
                <span className="social-post-card__platform">
                    {icon} {platform}
                </span>
                <span className={`social-post-card__format social-post-card__format--${mediaType}`}>
                    {mediaType === 'carousel' ? '📑 Carousel' :
                     mediaType === 'video' ? '🎬 Video' :
                     mediaType === 'image' ? '🖼️ Image' : '📝 Text'}
                </span>
            </div>

            {/* Media Preview */}
            <div className="social-post-card__media">
                {mediaType === 'video' && data?.video_url ? (
                    <div className="media-preview media-preview--video">
                        <video src={data.video_url} muted />
                        <div className="media-preview__play">▶</div>
                        {data.duration_seconds && (
                            <span className="media-preview__duration">
                                {data.duration_seconds}s
                            </span>
                        )}
                    </div>
                ) : mediaType === 'carousel' && data?.image_urls?.length > 0 ? (
                    <div className="media-preview media-preview--carousel">
                        <img src={data.image_urls[0]} alt="Slide 1" />
                        <span className="media-preview__count">
                            1/{data.image_urls.length}
                        </span>
                    </div>
                ) : data?.image_url ? (
                    <div className="media-preview media-preview--image">
                        <img src={data.image_url} alt="Post" />
                    </div>
                ) : (
                    <div className="media-preview media-preview--placeholder">
                        <span>{icon}</span>
                    </div>
                )}
            </div>

            {/* Caption */}
            <div className="social-post-card__caption">
                <p onClick={(e) => { e.stopPropagation(); setShowFullCaption(!showFullCaption); }}>
                    {showFullCaption ? caption : truncatedCaption}
                </p>
                {hashtags.length > 0 && (
                    <div className="social-post-card__hashtags">
                        {hashtags.slice(0, 4).map((tag, i) => (
                            <span key={i} className="hashtag">
                                {tag.startsWith('#') ? tag : `#${tag}`}
                            </span>
                        ))}
                        {hashtags.length > 4 && (
                            <span className="hashtag hashtag--more">+{hashtags.length - 4}</span>
                        )}
                    </div>
                )}
            </div>

            {/* TikTok-specific: Sound suggestion */}
            {platform === 'tiktok' && data?.sound_suggestion && (
                <div className="social-post-card__sound">
                    🎵 {data.sound_suggestion}
                </div>
            )}

            {/* Status indicator */}
            <div className={`social-post-card__status social-post-card__status--${status}`}>
                {status === 'generating' ? '⏳ Creating...' :
                 status === 'ready' ? '✓ Ready' :
                 status === 'approved' ? '✓✓ Approved' : status}
            </div>
        </div>
    );
}

export default SocialPostCard;
