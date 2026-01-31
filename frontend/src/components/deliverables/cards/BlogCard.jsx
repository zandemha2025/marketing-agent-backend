import React, { useState } from 'react';
import './DeliverableCards.css';

function BlogCard({ deliverable, isSelected, onSelect, onRefine }) {
    const [expanded, setExpanded] = useState(false);
    const { data, status } = deliverable;

    const title = data?.title || 'Untitled Blog Post';
    const content = data?.content || '';
    const heroImage = data?.hero_image;
    const wordCount = data?.word_count || 0;
    const readTime = data?.read_time_minutes || Math.ceil(wordCount / 200);

    // Get first paragraph for preview
    const paragraphs = content.split('\n\n');
    const preview = paragraphs[0]?.replace(/^#+ /, '') || '';
    const truncatedPreview = preview.length > 150 ? preview.slice(0, 150) + '...' : preview;

    return (
        <div
            className={`deliverable-card blog-card ${isSelected ? 'deliverable-card--selected' : ''} ${status === 'generating' ? 'deliverable-card--generating' : ''}`}
            onClick={onSelect}
        >
            {/* Hero Image */}
            {heroImage && (
                <div className="blog-card__hero">
                    <img src={heroImage} alt={title} />
                </div>
            )}

            {/* Content */}
            <div className="blog-card__content">
                {/* Header */}
                <div className="blog-card__header">
                    <span className="blog-card__icon">📝</span>
                    <span className="blog-card__label">Blog Post</span>
                </div>

                {/* Title */}
                <h4 className="blog-card__title">{title}</h4>

                {/* Meta */}
                <div className="blog-card__meta">
                    <span className="meta-item">{wordCount} words</span>
                    <span className="meta-divider">•</span>
                    <span className="meta-item">{readTime} min read</span>
                </div>

                {/* Preview */}
                <div className="blog-card__preview">
                    <p>{expanded ? content : truncatedPreview}</p>
                    {content.length > 150 && (
                        <button
                            className="expand-toggle"
                            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
                        >
                            {expanded ? 'Show less' : 'Read more'}
                        </button>
                    )}
                </div>
            </div>

            {/* Status */}
            <div className={`blog-card__status blog-card__status--${status}`}>
                {status === 'generating' ? '⏳ Writing...' :
                 status === 'ready' ? '✓ Ready' :
                 status === 'approved' ? '✓✓ Approved' : status}
            </div>
        </div>
    );
}

export default BlogCard;
