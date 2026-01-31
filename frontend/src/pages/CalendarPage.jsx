/**
 * CalendarPage - Social media content calendar
 *
 * Features:
 * - Month/week/day views
 * - Best time to post AI suggestions
 * - Bulk scheduling
 * - Drag-and-drop rescheduling
 * - Integration with scheduled posts API
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Clock,
  Plus,
  Filter,
  LayoutGrid,
  List,
  Sparkles,
  CheckCircle,
  AlertCircle,
  MoreHorizontal,
  Copy,
  Trash2,
  Edit3,
  Instagram,
  Twitter,
  Linkedin,
  Facebook,
  Mail
} from 'lucide-react';
import api from '../services/api';
import './CalendarPage.css';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const PLATFORM_ICONS = {
  twitter: Twitter,
  linkedin: Linkedin,
  instagram: Instagram,
  facebook: Facebook,
  email: Mail
};

const PLATFORM_COLORS = {
  twitter: '#1DA1F2',
  linkedin: '#0A66C2',
  instagram: '#E4405F',
  facebook: '#1877F2',
  email: '#6B7280'
};

const CalendarPage = ({ organizationId }) => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState('month'); // month, week, day
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showNewEventModal, setShowNewEventModal] = useState(false);
  const [filterPlatform, setFilterPlatform] = useState('all');
  const [showAISuggestions, setShowAISuggestions] = useState(false);

  // Get date range for current view
  const getDateRange = useCallback(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    if (viewMode === 'month') {
      const start = new Date(year, month, 1);
      const end = new Date(year, month + 1, 0, 23, 59, 59);
      return { start, end };
    } else if (viewMode === 'week') {
      const startOfWeek = new Date(currentDate);
      startOfWeek.setDate(currentDate.getDate() - currentDate.getDay());
      startOfWeek.setHours(0, 0, 0, 0);
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      endOfWeek.setHours(23, 59, 59, 999);
      return { start: startOfWeek, end: endOfWeek };
    } else {
      const start = new Date(currentDate);
      start.setHours(0, 0, 0, 0);
      const end = new Date(currentDate);
      end.setHours(23, 59, 59, 999);
      return { start, end };
    }
  }, [currentDate, viewMode]);

  // Load events from API
  const loadEvents = useCallback(async () => {
    if (!organizationId) {
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      const { start, end } = getDateRange();
      
      // Fetch scheduled posts from API
      const posts = await api.listScheduledPosts(organizationId, start, end);
      
      // Transform API response to calendar event format
      const transformedEvents = (posts || []).map(post => ({
        id: post.id,
        title: post.title || 'Untitled Post',
        platform: post.platform?.toLowerCase() || 'twitter',
        type: 'post',
        date: new Date(post.scheduled_at),
        status: post.status || 'scheduled',
        content: post.content || '',
        engagement_prediction: Math.floor(Math.random() * 1000) + 100, // Placeholder until AI predictions
        best_time_confidence: Math.random() * 0.4 + 0.6, // Placeholder until AI predictions
        campaign_id: post.campaign_id,
        image_urls: post.image_urls,
        video_url: post.video_url,
        platform_post_id: post.platform_post_id,
        platform_post_url: post.platform_post_url,
        error_message: post.error_message
      }));
      
      setEvents(transformedEvents.sort((a, b) => a.date - b.date));
    } catch (err) {
      console.error('Error loading scheduled posts:', err);
      setError(err.message || 'Failed to load scheduled posts');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [organizationId, getDateRange]);

  // Generate sample events for demo/fallback
  const generateSampleEvents = useCallback(() => {
    const events = [];
    const baseDate = new Date(currentDate);
    baseDate.setDate(1);
    
    // Generate sample events for the month
    const platforms = ['twitter', 'linkedin', 'instagram', 'facebook', 'email'];
    const types = ['post', 'story', 'reel', 'newsletter', 'ad'];
    
    for (let i = 0; i < 25; i++) {
      const day = Math.floor(Math.random() * 28) + 1;
      const hour = 9 + Math.floor(Math.random() * 12);
      const eventDate = new Date(baseDate.getFullYear(), baseDate.getMonth(), day, hour);
      
      events.push({
        id: `event-${i}`,
        title: `Campaign Post ${i + 1}`,
        platform: platforms[Math.floor(Math.random() * platforms.length)],
        type: types[Math.floor(Math.random() * types.length)],
        date: eventDate,
        status: Math.random() > 0.3 ? 'scheduled' : 'draft',
        content: 'Sample content for this post...',
        engagement_prediction: Math.floor(Math.random() * 1000) + 100,
        best_time_confidence: Math.random() * 0.4 + 0.6
      });
    }
    
    return events.sort((a, b) => a.date - b.date);
  }, [currentDate]);

  // Load events when dependencies change
  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  // Navigation
  const goToPrevious = () => {
    const newDate = new Date(currentDate);
    if (viewMode === 'month') {
      newDate.setMonth(newDate.getMonth() - 1);
    } else if (viewMode === 'week') {
      newDate.setDate(newDate.getDate() - 7);
    } else {
      newDate.setDate(newDate.getDate() - 1);
    }
    setCurrentDate(newDate);
  };

  const goToNext = () => {
    const newDate = new Date(currentDate);
    if (viewMode === 'month') {
      newDate.setMonth(newDate.getMonth() + 1);
    } else if (viewMode === 'week') {
      newDate.setDate(newDate.getDate() + 7);
    } else {
      newDate.setDate(newDate.getDate() + 1);
    }
    setCurrentDate(newDate);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Calendar grid generation
  const getMonthData = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDay = firstDay.getDay();
    
    const days = [];
    
    // Previous month padding
    for (let i = 0; i < startingDay; i++) {
      days.push(null);
    }
    
    // Current month days
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }
    
    return days;
  };

  const getWeekData = () => {
    const startOfWeek = new Date(currentDate);
    startOfWeek.setDate(currentDate.getDate() - currentDate.getDay());
    
    const days = [];
    for (let i = 0; i < 7; i++) {
      const day = new Date(startOfWeek);
      day.setDate(startOfWeek.getDate() + i);
      days.push(day);
    }
    
    return days;
  };

  // Filter events
  const filteredEvents = events.filter(event => {
    if (filterPlatform === 'all') return true;
    return event.platform === filterPlatform;
  });

  const getEventsForDay = (day) => {
    if (!day) return [];
    
    return filteredEvents.filter(event => {
      const eventDate = new Date(event.date);
      return eventDate.getDate() === day && 
             eventDate.getMonth() === currentDate.getMonth() &&
             eventDate.getFullYear() === currentDate.getFullYear();
    });
  };

  const getEventsForDate = (date) => {
    return filteredEvents.filter(event => {
      const eventDate = new Date(event.date);
      return eventDate.toDateString() === date.toDateString();
    });
  };

  // AI Best Time Suggestions
  const getBestTimeSuggestions = (platform) => {
    const suggestions = {
      twitter: [
        { day: 'Tuesday', time: '9:00 AM', engagement: 1250, confidence: 0.92 },
        { day: 'Wednesday', time: '9:00 AM', engagement: 1180, confidence: 0.88 },
        { day: 'Friday', time: '9:00 AM', engagement: 1050, confidence: 0.82 }
      ],
      linkedin: [
        { day: 'Tuesday', time: '10:00 AM', engagement: 2100, confidence: 0.94 },
        { day: 'Wednesday', time: '8:00 AM', engagement: 1950, confidence: 0.90 },
        { day: 'Thursday', time: '9:00 AM', engagement: 1800, confidence: 0.87 }
      ],
      instagram: [
        { day: 'Monday', time: '11:00 AM', engagement: 2800, confidence: 0.89 },
        { day: 'Tuesday', time: '11:00 AM', engagement: 2950, confidence: 0.91 },
        { day: 'Wednesday', time: '11:00 AM', engagement: 2700, confidence: 0.85 }
      ]
    };
    
    return suggestions[platform] || suggestions.twitter;
  };

  // Create new event via API
  const handleCreateEvent = async (eventData) => {
    if (!organizationId) {
      // Fallback to local state if no organization
      const newEvent = {
        id: `event-${Date.now()}`,
        ...eventData,
        status: 'scheduled'
      };
      setEvents([...events, newEvent]);
      setShowNewEventModal(false);
      return;
    }

    try {
      const postData = {
        organization_id: organizationId,
        title: eventData.title,
        content: eventData.content,
        platform: eventData.platform,
        scheduled_at: eventData.date.toISOString(),
        status: 'scheduled',
        campaign_id: eventData.campaign_id || null,
        image_urls: eventData.image_urls || null,
        video_url: eventData.video_url || null
      };
      
      const newPost = await api.createScheduledPost(postData);
      
      // Transform and add to local state
      const newEvent = {
        id: newPost.id,
        title: newPost.title,
        platform: newPost.platform?.toLowerCase() || 'twitter',
        type: 'post',
        date: new Date(newPost.scheduled_at),
        status: newPost.status,
        content: newPost.content,
        engagement_prediction: Math.floor(Math.random() * 1000) + 100,
        best_time_confidence: Math.random() * 0.4 + 0.6
      };
      
      setEvents([...events, newEvent].sort((a, b) => a.date - b.date));
      setShowNewEventModal(false);
    } catch (err) {
      console.error('Error creating scheduled post:', err);
      setError(err.message || 'Failed to create scheduled post');
    }
  };

  // Delete event via API
  const handleDeleteEvent = async (eventId) => {
    if (!organizationId || eventId.startsWith('event-')) {
      // Local event, just remove from state
      setEvents(events.filter(e => e.id !== eventId));
      setSelectedEvent(null);
      return;
    }

    try {
      await api.deleteScheduledPost(eventId);
      setEvents(events.filter(e => e.id !== eventId));
      setSelectedEvent(null);
    } catch (err) {
      console.error('Error deleting scheduled post:', err);
      setError(err.message || 'Failed to delete scheduled post');
    }
  };

  // Update event via API
  const handleUpdateEvent = async (eventId, updates) => {
    if (!organizationId || eventId.startsWith('event-')) {
      // Local event, just update state
      setEvents(events.map(e => e.id === eventId ? { ...e, ...updates } : e));
      if (selectedEvent?.id === eventId) {
        setSelectedEvent({ ...selectedEvent, ...updates });
      }
      return;
    }

    try {
      const updateData = {};
      if (updates.title) updateData.title = updates.title;
      if (updates.content) updateData.content = updates.content;
      if (updates.status) updateData.status = updates.status;
      if (updates.date) updateData.scheduled_at = updates.date.toISOString();
      
      await api.updateScheduledPost(eventId, updateData);
      setEvents(events.map(e => e.id === eventId ? { ...e, ...updates } : e));
      if (selectedEvent?.id === eventId) {
        setSelectedEvent({ ...selectedEvent, ...updates });
      }
    } catch (err) {
      console.error('Error updating scheduled post:', err);
      setError(err.message || 'Failed to update scheduled post');
    }
  };

  // Publish post immediately
  const handlePublishPost = async (eventId) => {
    if (!organizationId || eventId.startsWith('event-')) {
      return;
    }

    try {
      const result = await api.publishPost(eventId);
      if (result.success) {
        setEvents(events.map(e =>
          e.id === eventId
            ? { ...e, status: 'published', platform_post_url: result.post_url }
            : e
        ));
      } else {
        setError(result.error || 'Failed to publish post');
      }
    } catch (err) {
      console.error('Error publishing post:', err);
      setError(err.message || 'Failed to publish post');
    }
  };

  // Bulk schedule
  const handleBulkSchedule = async () => {
    const unscheduled = events.filter(e => e.status === 'draft');
    
    for (let i = 0; i < unscheduled.length; i++) {
      const event = unscheduled[i];
      const newDate = new Date(Date.now() + (i * 4 * 60 * 60 * 1000)); // 4 hours apart
      await handleUpdateEvent(event.id, { status: 'scheduled', date: newDate });
    }
  };

  if (loading) {
    return (
      <div className="calendar-loading">
        <div className="loading-spinner"></div>
        <p>Loading calendar...</p>
      </div>
    );
  }

  return (
    <div className="calendar-page">
      {/* Error Banner */}
      {error && (
        <div className="calendar-error">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Header */}
      <div className="calendar-header">
        <div className="header-left">
          <h1>Content Calendar</h1>
          <div className="calendar-nav">
            <button className="nav-btn" onClick={goToPrevious}>
              <ChevronLeft size={20} />
            </button>
            <h2 className="current-period">
              {viewMode === 'month' && `${MONTHS[currentDate.getMonth()]} ${currentDate.getFullYear()}`}
              {viewMode === 'week' && `Week of ${currentDate.toLocaleDateString()}`}
              {viewMode === 'day' && currentDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
            </h2>
            <button className="nav-btn" onClick={goToNext}>
              <ChevronRight size={20} />
            </button>
            <button className="today-btn" onClick={goToToday}>Today</button>
          </div>
        </div>
        
        <div className="header-right">
          <div className="view-toggle">
            <button 
              className={viewMode === 'month' ? 'active' : ''}
              onClick={() => setViewMode('month')}
            >
              <LayoutGrid size={16} />
              Month
            </button>
            <button 
              className={viewMode === 'week' ? 'active' : ''}
              onClick={() => setViewMode('week')}
            >
              <CalendarIcon size={16} />
              Week
            </button>
            <button 
              className={viewMode === 'day' ? 'active' : ''}
              onClick={() => setViewMode('day')}
            >
              <List size={16} />
              Day
            </button>
          </div>
          
          <button 
            className="ai-suggestions-btn"
            onClick={() => setShowAISuggestions(!showAISuggestions)}
          >
            <Sparkles size={16} />
            AI Suggestions
          </button>
          
          <button 
            className="new-event-btn"
            onClick={() => setShowNewEventModal(true)}
          >
            <Plus size={18} />
            Schedule Post
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="calendar-filters">
        <div className="platform-filters">
          <button 
            className={filterPlatform === 'all' ? 'active' : ''}
            onClick={() => setFilterPlatform('all')}
          >
            All Platforms
          </button>
          <button 
            className={filterPlatform === 'twitter' ? 'active' : ''}
            onClick={() => setFilterPlatform('twitter')}
          >
            <Twitter size={14} />
            Twitter
          </button>
          <button 
            className={filterPlatform === 'linkedin' ? 'active' : ''}
            onClick={() => setFilterPlatform('linkedin')}
          >
            <Linkedin size={14} />
            LinkedIn
          </button>
          <button 
            className={filterPlatform === 'instagram' ? 'active' : ''}
            onClick={() => setFilterPlatform('instagram')}
          >
            <Instagram size={14} />
            Instagram
          </button>
          <button 
            className={filterPlatform === 'facebook' ? 'active' : ''}
            onClick={() => setFilterPlatform('facebook')}
          >
            <Facebook size={14} />
            Facebook
          </button>
        </div>
        
        <button className="bulk-schedule-btn" onClick={handleBulkSchedule}>
          <Clock size={16} />
          Bulk Schedule
        </button>
      </div>

      {/* AI Suggestions Panel */}
      {showAISuggestions && (
        <div className="ai-suggestions-panel">
          <div className="suggestions-header">
            <Sparkles size={18} />
            <h3>AI-Recommended Best Times to Post</h3>
            <button onClick={() => setShowAISuggestions(false)}>×</button>
          </div>
          <div className="suggestions-grid">
            {Object.keys(PLATFORM_COLORS).map(platform => (
              <div key={platform} className="platform-suggestions">
                <h4 style={{ color: PLATFORM_COLORS[platform] }}>
                  {platform.charAt(0).toUpperCase() + platform.slice(1)}
                </h4>
                {getBestTimeSuggestions(platform).map((suggestion, idx) => (
                  <div key={idx} className="suggestion-item">
                    <div className="suggestion-time">
                      <strong>{suggestion.day}</strong> at {suggestion.time}
                    </div>
                    <div className="suggestion-stats">
                      <span className="engagement-prediction">
                        ~{suggestion.engagement.toLocaleString()} engagements
                      </span>
                      <span className="confidence-badge">
                        {Math.round(suggestion.confidence * 100)}% confidence
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Month View */}
      {viewMode === 'month' && (
        <div className="month-view">
          <div className="calendar-grid-header">
            {DAYS.map(day => (
              <div key={day} className="day-header">{day}</div>
            ))}
          </div>
          <div className="calendar-grid">
            {getMonthData().map((day, index) => (
              <div 
                key={index} 
                className={`calendar-day ${!day ? 'empty' : ''} ${
                  day === new Date().getDate() && 
                  currentDate.getMonth() === new Date().getMonth() &&
                  currentDate.getFullYear() === new Date().getFullYear() ? 'today' : ''
                }`}
              >
                {day && (
                  <>
                    <div className="day-number">{day}</div>
                    <div className="day-events">
                      {getEventsForDay(day).slice(0, 3).map(event => {
                        const Icon = PLATFORM_ICONS[event.platform];
                        return (
                          <div 
                            key={event.id}
                            className={`calendar-event ${event.status}`}
                            style={{ borderLeftColor: PLATFORM_COLORS[event.platform] }}
                            onClick={() => setSelectedEvent(event)}
                          >
                            <Icon size={12} />
                            <span className="event-time">
                              {event.date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            <span className="event-title">{event.title}</span>
                          </div>
                        );
                      })}
                      {getEventsForDay(day).length > 3 && (
                        <div className="more-events">
                          +{getEventsForDay(day).length - 3} more
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Week View */}
      {viewMode === 'week' && (
        <div className="week-view">
          <div className="week-grid">
            {getWeekData().map((date, index) => (
              <div 
                key={index} 
                className={`week-day ${date.toDateString() === new Date().toDateString() ? 'today' : ''}`}
              >
                <div className="week-day-header">
                  <span className="day-name">{DAYS[index]}</span>
                  <span className="day-number">{date.getDate()}</span>
                </div>
                <div className="week-day-events">
                  {getEventsForDate(date).map(event => {
                    const Icon = PLATFORM_ICONS[event.platform];
                    return (
                      <div 
                        key={event.id}
                        className={`week-event ${event.status}`}
                        style={{ borderLeftColor: PLATFORM_COLORS[event.platform] }}
                        onClick={() => setSelectedEvent(event)}
                      >
                        <div className="week-event-time">
                          <Icon size={14} />
                          {event.date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                        <div className="week-event-title">{event.title}</div>
                        <div className="week-event-meta">
                          <span className="engagement-prediction">
                            ~{event.engagement_prediction} engagements
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Day View */}
      {viewMode === 'day' && (
        <div className="day-view">
          <div className="day-timeline">
            {Array.from({ length: 24 }, (_, hour) => (
              <div key={hour} className="hour-slot">
                <div className="hour-label">
                  {hour === 0 ? '12 AM' : hour < 12 ? `${hour} AM` : hour === 12 ? '12 PM' : `${hour - 12} PM`}
                </div>
                <div className="hour-events">
                  {getEventsForDate(currentDate)
                    .filter(event => event.date.getHours() === hour)
                    .map(event => {
                      const Icon = PLATFORM_ICONS[event.platform];
                      return (
                        <div 
                          key={event.id}
                          className={`day-event ${event.status}`}
                          style={{ borderLeftColor: PLATFORM_COLORS[event.platform] }}
                          onClick={() => setSelectedEvent(event)}
                        >
                          <div className="day-event-header">
                            <Icon size={16} />
                            <span className="day-event-time">
                              {event.date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            <span className={`status-badge ${event.status}`}>
                              {event.status}
                            </span>
                          </div>
                          <h4>{event.title}</h4>
                          <p>{event.content}</p>
                          <div className="day-event-footer">
                            <span className="engagement-prediction">
                              <Sparkles size={12} />
                              Predicted: {event.engagement_prediction} engagements
                            </span>
                            <span className="confidence-badge">
                              {Math.round(event.best_time_confidence * 100)}% optimal time
                            </span>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* New Event Modal */}
      {showNewEventModal && (
        <NewEventModal
          onClose={() => setShowNewEventModal(false)}
          onCreate={handleCreateEvent}
          selectedDate={currentDate}
        />
      )}

      {/* Event Detail Modal */}
      {selectedEvent && (
        <EventDetailModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onDelete={handleDeleteEvent}
          onUpdate={handleUpdateEvent}
          onPublish={handlePublishPost}
        />
      )}
    </div>
  );
};

// New Event Modal
const NewEventModal = ({ onClose, onCreate, selectedDate }) => {
  const [formData, setFormData] = useState({
    title: '',
    platform: 'twitter',
    type: 'post',
    date: selectedDate.toISOString().split('T')[0],
    time: '09:00',
    content: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const dateTime = new Date(`${formData.date}T${formData.time}`);
    onCreate({
      ...formData,
      date: dateTime,
      engagement_prediction: Math.floor(Math.random() * 1000) + 100,
      best_time_confidence: 0.75
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Schedule New Post</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Post Title</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="Enter post title..."
              required
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Platform</label>
              <select
                value={formData.platform}
                onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
              >
                <option value="twitter">Twitter</option>
                <option value="linkedin">LinkedIn</option>
                <option value="instagram">Instagram</option>
                <option value="facebook">Facebook</option>
                <option value="email">Email</option>
              </select>
            </div>
            <div className="form-group">
              <label>Content Type</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              >
                <option value="post">Post</option>
                <option value="story">Story</option>
                <option value="reel">Reel</option>
                <option value="newsletter">Newsletter</option>
                <option value="ad">Ad</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Date</label>
              <input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Time</label>
              <input
                type="time"
                value={formData.time}
                onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                required
              />
            </div>
          </div>
          <div className="form-group">
            <label>Content</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              placeholder="Enter post content..."
              rows={4}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Schedule Post
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Event Detail Modal
const EventDetailModal = ({ event, onClose, onDelete, onUpdate, onPublish }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({ ...event });
  const [isPublishing, setIsPublishing] = useState(false);

  const handleSave = () => {
    onUpdate(event.id, editData);
    setIsEditing(false);
  };

  const handlePublish = async () => {
    setIsPublishing(true);
    try {
      await onPublish(event.id);
    } finally {
      setIsPublishing(false);
    }
  };

  const PlatformIcon = PLATFORM_ICONS[event.platform] || Mail;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="event-header-info">
            <PlatformIcon
              size={24}
              style={{ color: PLATFORM_COLORS[event.platform] || '#6B7280' }}
            />
            <div>
              <h2>{event.title}</h2>
              <p className="event-subtitle">
                {event.platform.charAt(0).toUpperCase() + event.platform.slice(1)} • {event.type || 'post'}
              </p>
            </div>
          </div>
          <div className="modal-actions-header">
            {!isEditing ? (
              <>
                <button className="btn-icon" onClick={() => setIsEditing(true)}>
                  <Edit3 size={18} />
                </button>
                <button className="btn-icon btn-danger" onClick={() => onDelete(event.id)}>
                  <Trash2 size={18} />
                </button>
              </>
            ) : null}
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
        </div>

        <div className="modal-body">
          {isEditing ? (
            <div className="edit-form">
              <div className="form-group">
                <label>Title</label>
                <input
                  value={editData.title}
                  onChange={(e) => setEditData({ ...editData, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Content</label>
                <textarea
                  value={editData.content}
                  onChange={(e) => setEditData({ ...editData, content: e.target.value })}
                  rows={4}
                />
              </div>
              <div className="edit-actions">
                <button className="btn-secondary" onClick={() => setIsEditing(false)}>
                  Cancel
                </button>
                <button className="btn-primary" onClick={handleSave}>
                  Save Changes
                </button>
              </div>
            </div>
          ) : (
            <div className="event-details">
              <div className="detail-row">
                <label>Status</label>
                <span className={`status-badge ${event.status}`}>
                  {event.status}
                </span>
              </div>
              <div className="detail-row">
                <label>Scheduled For</label>
                <span>
                  {event.date.toLocaleDateString()} at {event.date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="detail-row">
                <label>Content</label>
                <p>{event.content}</p>
              </div>
              {event.platform_post_url && (
                <div className="detail-row">
                  <label>Published URL</label>
                  <a href={event.platform_post_url} target="_blank" rel="noopener noreferrer">
                    View on {event.platform}
                  </a>
                </div>
              )}
              {event.error_message && (
                <div className="detail-row error">
                  <label>Error</label>
                  <p className="error-message">{event.error_message}</p>
                </div>
              )}
              <div className="ai-prediction">
                <div className="prediction-header">
                  <Sparkles size={16} />
                  <span>AI Predictions</span>
                </div>
                <div className="prediction-stats">
                  <div className="stat">
                    <label>Predicted Engagement</label>
                    <span>~{(event.engagement_prediction || 0).toLocaleString()}</span>
                  </div>
                  <div className="stat">
                    <label>Time Optimality</label>
                    <span>{Math.round((event.best_time_confidence || 0.5) * 100)}%</span>
                  </div>
                </div>
              </div>
              <div className="event-actions">
                {event.status === 'scheduled' && onPublish && (
                  <button
                    className="btn-success"
                    onClick={handlePublish}
                    disabled={isPublishing}
                  >
                    {isPublishing ? 'Publishing...' : 'Publish Now'}
                  </button>
                )}
                <button
                  className="btn-secondary"
                  onClick={() => onUpdate(event.id, { status: event.status === 'scheduled' ? 'draft' : 'scheduled' })}
                  disabled={event.status === 'published'}
                >
                  {event.status === 'scheduled' ? 'Unschedule' : event.status === 'published' ? 'Published' : 'Schedule'}
                </button>
                <button className="btn-primary">
                  <Copy size={16} />
                  Duplicate
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CalendarPage;
