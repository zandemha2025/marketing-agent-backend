import React, { useState, useCallback, useMemo } from 'react';
import './SocialCalendar.css';

/**
 * SocialCalendar - Visual content scheduling and planning calendar.
 *
 * Features:
 * - Month/Week/Day views
 * - Drag-and-drop scheduling
 * - Platform color coding
 * - Best time recommendations
 * - Quick post preview
 */

const PLATFORMS = {
    instagram: { name: 'Instagram', color: '#E4405F', icon: '📸' },
    twitter: { name: 'Twitter', color: '#1DA1F2', icon: '🐦' },
    facebook: { name: 'Facebook', color: '#1877F2', icon: '📘' },
    linkedin: { name: 'LinkedIn', color: '#0A66C2', icon: '💼' },
    tiktok: { name: 'TikTok', color: '#000000', icon: '🎵' },
    youtube: { name: 'YouTube', color: '#FF0000', icon: '▶️' },
    pinterest: { name: 'Pinterest', color: '#E60023', icon: '📌' },
};

const VIEWS = {
    month: 'Month',
    week: 'Week',
    day: 'Day',
};

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];

export default function SocialCalendar({
    scheduledPosts = [],
    onPostClick,
    onPostMove,
    onAddPost,
    onDeletePost,
    bestTimes = {},
}) {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [view, setView] = useState('month');
    const [selectedDate, setSelectedDate] = useState(null);
    const [draggedPost, setDraggedPost] = useState(null);
    const [showPostModal, setShowPostModal] = useState(null);

    // Get calendar grid data
    const calendarData = useMemo(() => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();

        if (view === 'month') {
            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            const startPadding = firstDay.getDay();
            const totalDays = lastDay.getDate();

            const days = [];

            // Padding days from previous month
            for (let i = startPadding - 1; i >= 0; i--) {
                const date = new Date(year, month, -i);
                days.push({ date, isCurrentMonth: false });
            }

            // Days of current month
            for (let i = 1; i <= totalDays; i++) {
                days.push({ date: new Date(year, month, i), isCurrentMonth: true });
            }

            // Padding days for next month
            const remaining = 42 - days.length;
            for (let i = 1; i <= remaining; i++) {
                days.push({ date: new Date(year, month + 1, i), isCurrentMonth: false });
            }

            return days;
        }

        if (view === 'week') {
            const startOfWeek = new Date(currentDate);
            startOfWeek.setDate(currentDate.getDate() - currentDate.getDay());

            const days = [];
            for (let i = 0; i < 7; i++) {
                const date = new Date(startOfWeek);
                date.setDate(startOfWeek.getDate() + i);
                days.push({ date, isCurrentMonth: true });
            }
            return days;
        }

        return [{ date: currentDate, isCurrentMonth: true }];
    }, [currentDate, view]);

    // Get posts for a specific date
    const getPostsForDate = useCallback((date) => {
        return scheduledPosts.filter(post => {
            const postDate = new Date(post.scheduledAt);
            return postDate.toDateString() === date.toDateString();
        });
    }, [scheduledPosts]);

    // Navigation
    const navigate = useCallback((direction) => {
        const newDate = new Date(currentDate);
        if (view === 'month') {
            newDate.setMonth(newDate.getMonth() + direction);
        } else if (view === 'week') {
            newDate.setDate(newDate.getDate() + (direction * 7));
        } else {
            newDate.setDate(newDate.getDate() + direction);
        }
        setCurrentDate(newDate);
    }, [currentDate, view]);

    const goToToday = useCallback(() => {
        setCurrentDate(new Date());
    }, []);

    // Drag and Drop
    const handleDragStart = useCallback((e, post) => {
        setDraggedPost(post);
        e.dataTransfer.effectAllowed = 'move';
    }, []);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }, []);

    const handleDrop = useCallback((e, date) => {
        e.preventDefault();
        if (draggedPost && onPostMove) {
            onPostMove(draggedPost.id, date);
        }
        setDraggedPost(null);
    }, [draggedPost, onPostMove]);

    const handleDateClick = useCallback((date) => {
        setSelectedDate(date);
    }, []);

    const formatDate = useCallback((date) => {
        return `${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
    }, []);

    const isToday = useCallback((date) => {
        const today = new Date();
        return date.toDateString() === today.toDateString();
    }, []);

    const getPlatformInfo = (platform) => PLATFORMS[platform] || { name: platform, color: '#666', icon: '📄' };

    return (
        <div className="social-calendar">
            {/* Header */}
            <div className="social-calendar__header">
                <div className="social-calendar__nav">
                    <button
                        className="nav-btn"
                        onClick={() => navigate(-1)}
                    >
                        ←
                    </button>
                    <h2 className="social-calendar__title">{formatDate(currentDate)}</h2>
                    <button
                        className="nav-btn"
                        onClick={() => navigate(1)}
                    >
                        →
                    </button>
                </div>

                <div className="social-calendar__controls">
                    <button className="today-btn" onClick={goToToday}>Today</button>

                    <div className="view-switcher">
                        {Object.entries(VIEWS).map(([key, label]) => (
                            <button
                                key={key}
                                className={`view-btn ${view === key ? 'view-btn--active' : ''}`}
                                onClick={() => setView(key)}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Platform Legend */}
            <div className="social-calendar__legend">
                {Object.entries(PLATFORMS).map(([key, platform]) => (
                    <div key={key} className="legend-item">
                        <span
                            className="legend-dot"
                            style={{ backgroundColor: platform.color }}
                        />
                        <span>{platform.name}</span>
                    </div>
                ))}
            </div>

            {/* Calendar Grid */}
            <div className={`social-calendar__grid social-calendar__grid--${view}`}>
                {/* Day Headers (Month/Week view) */}
                {view !== 'day' && (
                    <div className="calendar-header-row">
                        {DAYS_OF_WEEK.map(day => (
                            <div key={day} className="calendar-header-cell">
                                {day}
                            </div>
                        ))}
                    </div>
                )}

                {/* Calendar Days */}
                <div className={`calendar-body calendar-body--${view}`}>
                    {calendarData.map(({ date, isCurrentMonth }, index) => {
                        const posts = getPostsForDate(date);
                        const isSelected = selectedDate?.toDateString() === date.toDateString();
                        const hasBestTime = bestTimes[date.getDay()];

                        return (
                            <div
                                key={index}
                                className={`calendar-cell ${!isCurrentMonth ? 'calendar-cell--muted' : ''} ${isToday(date) ? 'calendar-cell--today' : ''} ${isSelected ? 'calendar-cell--selected' : ''}`}
                                onClick={() => handleDateClick(date)}
                                onDragOver={handleDragOver}
                                onDrop={(e) => handleDrop(e, date)}
                            >
                                <div className="calendar-cell__header">
                                    <span className="calendar-cell__day">
                                        {date.getDate()}
                                    </span>
                                    {hasBestTime && (
                                        <span className="calendar-cell__best-time" title="Optimal posting time">
                                            ⚡
                                        </span>
                                    )}
                                </div>

                                <div className="calendar-cell__posts">
                                    {posts.slice(0, view === 'month' ? 3 : 10).map(post => {
                                        const platform = getPlatformInfo(post.platform);
                                        return (
                                            <div
                                                key={post.id}
                                                className="calendar-post"
                                                style={{ borderLeftColor: platform.color }}
                                                draggable
                                                onDragStart={(e) => handleDragStart(e, post)}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onPostClick?.(post);
                                                }}
                                            >
                                                <span className="calendar-post__icon">{platform.icon}</span>
                                                <span className="calendar-post__title">
                                                    {post.title || 'Untitled'}
                                                </span>
                                                <span className="calendar-post__time">
                                                    {new Date(post.scheduledAt).toLocaleTimeString('en-US', {
                                                        hour: 'numeric',
                                                        minute: '2-digit',
                                                    })}
                                                </span>
                                            </div>
                                        );
                                    })}

                                    {posts.length > (view === 'month' ? 3 : 10) && (
                                        <div className="calendar-cell__more">
                                            +{posts.length - (view === 'month' ? 3 : 10)} more
                                        </div>
                                    )}
                                </div>

                                {/* Add Post Button */}
                                <button
                                    className="calendar-cell__add"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onAddPost?.(date);
                                    }}
                                    title="Schedule post"
                                >
                                    +
                                </button>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Stats Footer */}
            <div className="social-calendar__stats">
                <div className="stat-item">
                    <span className="stat-value">{scheduledPosts.length}</span>
                    <span className="stat-label">Scheduled</span>
                </div>
                <div className="stat-item">
                    <span className="stat-value">
                        {scheduledPosts.filter(p => new Date(p.scheduledAt) > new Date()).length}
                    </span>
                    <span className="stat-label">Upcoming</span>
                </div>
                <div className="stat-item">
                    <span className="stat-value">
                        {[...new Set(scheduledPosts.map(p => p.platform))].length}
                    </span>
                    <span className="stat-label">Platforms</span>
                </div>
            </div>
        </div>
    );
}
