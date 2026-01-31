import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import './AnalyticsDashboard.css';

/**
 * Analytics Dashboard Component
 * 
 * Displays comprehensive analytics for the organization:
 * - Campaign stats (total, by status, created this week)
 * - Asset counts
 * - Task stats (total, by status, completion rate)
 * - Scheduled posts stats (total, by status)
 * - Deliverables by type and status (pie charts)
 * - Campaign progress with completion rates
 * - Activity timeline chart
 * - Recent activity tracking
 * - Date range filtering
 */

const AnalyticsDashboard = ({ organizationId }) => {
  const [analytics, setAnalytics] = useState(null);
  const [campaignProgress, setCampaignProgress] = useState([]);
  const [deliverablesByType, setDeliverablesByType] = useState({});
  const [deliverablesByStatus, setDeliverablesByStatus] = useState({});
  const [postsByPlatform, setPostsByPlatform] = useState({});
  const [activityTimeline, setActivityTimeline] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchAnalytics();
  }, [organizationId, days]);

  const fetchAnalytics = async () => {
    if (!organizationId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const [
        overviewData,
        progressData,
        byTypeData,
        byStatusData,
        byPlatformData,
        timelineData
      ] = await Promise.all([
        api.getAnalyticsOverview(organizationId, days),
        api.getCampaignProgress(organizationId),
        api.getDeliverablesByType(organizationId),
        api.getDeliverablesByStatus(organizationId),
        api.getPostsByPlatform(organizationId),
        api.getActivityTimeline(organizationId, days)
      ]);
      
      setAnalytics(overviewData);
      setCampaignProgress(progressData);
      setDeliverablesByType(byTypeData);
      setDeliverablesByStatus(byStatusData);
      setPostsByPlatform(byPlatformData);
      setActivityTimeline(timelineData);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => {
    if (num === undefined || num === null) return '0';
    return num.toLocaleString();
  };

  const formatPercentage = (val) => {
    if (val === undefined || val === null) return '0%';
    return `${Math.round(val)}%`;
  };

  const getStatusColor = (status) => {
    const colors = {
      active: '#10b981',
      completed: '#3b82f6',
      draft: '#6b7280',
      published: '#10b981',
      scheduled: '#f59e0b',
      failed: '#ef4444',
      todo: '#6b7280',
      in_progress: '#3b82f6',
      done: '#10b981',
      review: '#f59e0b',
    };
    return colors[status?.toLowerCase()] || '#6b7280';
  };

  // Pie Chart Component
  const PieChart = ({ data, title, colors }) => {
    const total = Object.values(data).reduce((a, b) => a + b, 0);
    const defaultColors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6', '#ec4899', '#14b8a6'];
    const chartColors = colors || defaultColors;
    
    if (total === 0) {
      return (
        <div className="chart-card">
          <h3>{title}</h3>
          <div className="chart-empty">No data available</div>
        </div>
      );
    }
    
    return (
      <div className="chart-card">
        <h3>{title}</h3>
        <div className="pie-chart">
          <div className="pie-visual">
            <svg viewBox="0 0 100 100" className="pie-svg">
              {(() => {
                let cumulativePercent = 0;
                return Object.entries(data).map(([key, value], i) => {
                  const percent = (value / total) * 100;
                  const startAngle = cumulativePercent * 3.6;
                  const endAngle = (cumulativePercent + percent) * 3.6;
                  cumulativePercent += percent;
                  
                  // Calculate SVG arc path
                  const startX = 50 + 40 * Math.cos((startAngle - 90) * Math.PI / 180);
                  const startY = 50 + 40 * Math.sin((startAngle - 90) * Math.PI / 180);
                  const endX = 50 + 40 * Math.cos((endAngle - 90) * Math.PI / 180);
                  const endY = 50 + 40 * Math.sin((endAngle - 90) * Math.PI / 180);
                  const largeArc = percent > 50 ? 1 : 0;
                  
                  return (
                    <path
                      key={key}
                      d={`M 50 50 L ${startX} ${startY} A 40 40 0 ${largeArc} 1 ${endX} ${endY} Z`}
                      fill={chartColors[i % chartColors.length]}
                    />
                  );
                });
              })()}
            </svg>
          </div>
          <div className="pie-legend">
            {Object.entries(data).map(([key, value], i) => (
              <div key={key} className="pie-item">
                <span className="pie-color" style={{ background: chartColors[i % chartColors.length] }} />
                <span className="pie-label">{key.replace(/_/g, ' ')}</span>
                <span className="pie-value">{value} ({total > 0 ? Math.round(value / total * 100) : 0}%)</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  // Progress Bar Component
  const ProgressBar = ({ value, max, label }) => {
    const percentage = max > 0 ? (value / max) * 100 : 0;
    return (
      <div className="progress-item">
        <div className="progress-label">
          <span>{label}</span>
          <span>{value} / {max}</span>
        </div>
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    );
  };

  // Stat Card Component
  const StatCard = ({ title, value, subtitle, icon, color }) => (
    <div className={`stat-card ${color || ''}`}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-content">
        <h3 className="stat-value">{value}</h3>
        <p className="stat-title">{title}</p>
        {subtitle && <span className="stat-subtitle">{subtitle}</span>}
      </div>
    </div>
  );

  const renderOverview = () => {
    if (!analytics) return null;

    const { campaigns, assets, tasks, scheduled_posts } = analytics;

    return (
      <div className="analytics-overview">
        {/* Stats Grid */}
        <div className="stats-grid">
          <StatCard
            title="Total Campaigns"
            value={formatNumber(campaigns?.total)}
            subtitle={`${formatNumber(campaigns?.created_this_week)} this week`}
            icon="📊"
            color="blue"
          />
          <StatCard
            title="Deliverables"
            value={formatNumber(Object.values(deliverablesByType).reduce((a, b) => a + b, 0))}
            icon="📝"
            color="green"
          />
          <StatCard
            title="Assets"
            value={formatNumber(assets?.total)}
            subtitle={`${formatNumber(assets?.created_this_week)} this week`}
            icon="🖼️"
            color="purple"
          />
          <StatCard
            title="Tasks Completed"
            value={formatNumber(tasks?.by_status?.done || 0)}
            subtitle={`${formatNumber(tasks?.overdue_count || 0)} overdue`}
            icon="✅"
            color="amber"
          />
          <StatCard
            title="Posts Scheduled"
            value={formatNumber(scheduled_posts?.by_status?.scheduled || 0)}
            icon="📅"
            color="indigo"
          />
          <StatCard
            title="Posts Published"
            value={formatNumber(scheduled_posts?.published_this_week || 0)}
            subtitle="this week"
            icon="🚀"
            color="teal"
          />
        </div>

        {/* Charts Row */}
        <div className="charts-row">
          <PieChart data={deliverablesByType} title="Deliverables by Type" />
          <PieChart data={deliverablesByStatus} title="Deliverables by Status" />
          <PieChart data={postsByPlatform} title="Posts by Platform" />
        </div>

        {/* Campaign Progress Section */}
        <div className="campaigns-section">
          <h2>Campaign Progress</h2>
          <div className="campaigns-list">
            {campaignProgress.length === 0 ? (
              <div className="analytics-empty">
                <p>No campaigns found</p>
              </div>
            ) : (
              campaignProgress.map(campaign => (
                <div key={campaign.campaign_id} className="campaign-card">
                  <div className="campaign-header">
                    <h4>{campaign.campaign_name}</h4>
                    <span className={`status-badge ${campaign.status}`}>{campaign.status}</span>
                  </div>
                  <div className="campaign-stats">
                    <span>{campaign.deliverables_count} deliverables</span>
                    <span>{campaign.assets_count} assets</span>
                  </div>
                  <ProgressBar
                    value={campaign.tasks_completed}
                    max={campaign.tasks_total}
                    label="Task Completion"
                  />
                  <div className="completion-rate">{campaign.completion_rate}% complete</div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Activity Timeline */}
        <div className="activity-section">
          <h2>Activity Timeline</h2>
          <div className="activity-chart">
            {activityTimeline.length === 0 ? (
              <div className="analytics-empty">
                <p>No activity data available</p>
              </div>
            ) : (
              <div className="timeline-bars">
                {activityTimeline.map((item, i) => {
                  const maxValue = Math.max(...activityTimeline.map(d => d.value), 1);
                  const height = (item.value / maxValue) * 100;
                  return (
                    <div key={i} className="activity-bar-container">
                      <div 
                        className="activity-bar" 
                        style={{ height: `${Math.max(height, 4)}%` }}
                        title={`${item.date}: ${item.value} items`}
                      />
                      {i % 7 === 0 && (
                        <span className="activity-date">{item.date.slice(5)}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Legacy Cards */}
        <div className="legacy-cards">
          {/* Campaign Stats */}
          <div className="analytics-card">
            <div className="analytics-card-header">
              <h3>Campaigns</h3>
              <span className="analytics-total">{formatNumber(campaigns?.total)}</span>
            </div>
            <div className="analytics-card-content">
              <div className="analytics-metric">
                <span className="metric-label">Completion Rate</span>
                <span className="metric-value">{formatPercentage(campaigns?.completion_rate)}</span>
              </div>
              <div className="analytics-metric">
                <span className="metric-label">This Week</span>
                <span className="metric-value">{formatNumber(campaigns?.created_this_week)}</span>
              </div>
              <div className="analytics-metric">
                <span className="metric-label">This Month</span>
                <span className="metric-value">{formatNumber(campaigns?.created_this_month)}</span>
              </div>
              <div className="status-breakdown">
                {Object.entries(campaigns?.by_status || {}).map(([status, count]) => (
                  <div key={status} className="status-item">
                    <span 
                      className="status-dot" 
                      style={{ backgroundColor: getStatusColor(status) }}
                    />
                    <span className="status-name">{status}</span>
                    <span className="status-count">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Asset Stats */}
          <div className="analytics-card">
            <div className="analytics-card-header">
              <h3>Assets</h3>
              <span className="analytics-total">{formatNumber(assets?.total)}</span>
            </div>
            <div className="analytics-card-content">
              <div className="analytics-metric">
                <span className="metric-label">Created This Week</span>
                <span className="metric-value">{formatNumber(assets?.created_this_week)}</span>
              </div>
              <div className="type-breakdown">
                <h4>By Type</h4>
                {Object.entries(assets?.by_type || {})
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 5)
                  .map(([type, count]) => (
                    <div key={type} className="type-item">
                      <span className="type-name">{type.replace(/_/g, ' ')}</span>
                      <span className="type-count">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* Task Stats */}
          <div className="analytics-card">
            <div className="analytics-card-header">
              <h3>Tasks</h3>
              <span className="analytics-total">{formatNumber(tasks?.total)}</span>
            </div>
            <div className="analytics-card-content">
              <div className="analytics-metric">
                <span className="metric-label">Completion Rate</span>
                <span className="metric-value">{formatPercentage(tasks?.completion_rate)}</span>
              </div>
              <div className="analytics-metric">
                <span className="metric-label">Overdue</span>
                <span className="metric-value warning">{formatNumber(tasks?.overdue_count)}</span>
              </div>
              <div className="analytics-metric">
                <span className="metric-label">High Priority</span>
                <span className="metric-value">{formatNumber(tasks?.high_priority_count)}</span>
              </div>
              <div className="status-breakdown">
                {Object.entries(tasks?.by_status || {}).map(([status, count]) => (
                  <div key={status} className="status-item">
                    <span 
                      className="status-dot" 
                      style={{ backgroundColor: getStatusColor(status) }}
                    />
                    <span className="status-name">{status}</span>
                    <span className="status-count">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Scheduled Posts Stats */}
          <div className="analytics-card">
            <div className="analytics-card-header">
              <h3>Social Posts</h3>
              <span className="analytics-total">{formatNumber(scheduled_posts?.total)}</span>
            </div>
            <div className="analytics-card-content">
              <div className="analytics-metric">
                <span className="metric-label">Published This Week</span>
                <span className="metric-value success">{formatNumber(scheduled_posts?.published_this_week)}</span>
              </div>
              <div className="analytics-metric">
                <span className="metric-label">Scheduled</span>
                <span className="metric-value">{formatNumber(scheduled_posts?.scheduled_this_week)}</span>
              </div>
              <div className="platform-breakdown">
                <h4>By Platform</h4>
                {Object.entries(scheduled_posts?.by_platform || {}).map(([platform, count]) => (
                  <div key={platform} className="platform-item">
                    <span className="platform-icon">{getPlatformIcon(platform)}</span>
                    <span className="platform-name">{platform}</span>
                    <span className="platform-count">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const getPlatformIcon = (platform) => {
    const icons = {
      twitter: '🐦',
      linkedin: '💼',
      instagram: '📷',
      facebook: '👥',
    };
    return icons[platform?.toLowerCase()] || '📱';
  };

  const getActivityIcon = (type) => {
    const icons = {
      campaign: '📊',
      asset: '🎨',
      task: '✅',
      post: '📝',
    };
    return icons[type] || '📌';
  };

  const formatTimeAgo = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const daysAgo = Math.floor(hours / 24);
    if (daysAgo < 7) return `${daysAgo}d ago`;
    return date.toLocaleDateString();
  };

  const renderRecentActivity = () => {
    if (!analytics?.recent_activity?.length) {
      return (
        <div className="analytics-empty">
          <p>No recent activity</p>
        </div>
      );
    }

    return (
      <div className="activity-list">
        {analytics.recent_activity.map((activity) => (
          <div key={`${activity.type}-${activity.id}`} className="activity-item">
            <span className="activity-icon">{getActivityIcon(activity.type)}</span>
            <div className="activity-content">
              <div className="activity-header">
                <span className="activity-title">{activity.title}</span>
                <span className="activity-time">{formatTimeAgo(activity.timestamp)}</span>
              </div>
              <div className="activity-meta">
                <span className={`activity-action action-${activity.action}`}>
                  {activity.action}
                </span>
                {activity.user_name && (
                  <span className="activity-user">by {activity.user_name}</span>
                )}
              </div>
              {activity.description && (
                <p className="activity-description">{activity.description}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="analytics-dashboard loading">
        <div className="analytics-spinner" />
        <p>Loading analytics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-dashboard error">
        <p>{error}</p>
        <button onClick={fetchAnalytics} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="analytics-dashboard">
      <div className="analytics-header">
        <h2>Analytics Dashboard</h2>
        <div className="analytics-controls">
          <select 
            value={days} 
            onChange={(e) => setDays(Number(e.target.value))}
            className="days-selector"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button onClick={fetchAnalytics} className="refresh-button">
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="analytics-tabs">
        <button
          className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`tab-button ${activeTab === 'activity' ? 'active' : ''}`}
          onClick={() => setActiveTab('activity')}
        >
          Recent Activity
        </button>
      </div>

      <div className="analytics-content">
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'activity' && (
          <div className="activity-section-tab">
            <h3>Recent Activity</h3>
            {renderRecentActivity()}
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
