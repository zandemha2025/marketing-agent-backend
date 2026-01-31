import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import './CampaignList.css';

const STATUS_CONFIG = {
  draft: { label: 'Draft', className: 'status-draft' },
  queued: { label: 'Queued', className: 'status-queued' },
  running: { label: 'Running', className: 'status-running' },
  complete: { label: 'Complete', className: 'status-complete' },
  failed: { label: 'Failed', className: 'status-failed' },
};

export default function CampaignList({ organizationId, onSelectCampaign, onCreateCampaign }) {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!organizationId) return;
    setLoading(true);
    api.listCampaigns(organizationId)
      .then((data) => {
        setCampaigns(Array.isArray(data) ? data : []);
        setError(null);
      })
      .catch((err) => setError(err.message || 'Failed to load campaigns'))
      .finally(() => setLoading(false));
  }, [organizationId]);

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="campaign-list">
        <div className="campaign-list__header">
          <h2 className="campaign-list__title">Campaigns</h2>
        </div>
        <div className="campaign-list__loading">Loading campaigns...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="campaign-list">
        <div className="campaign-list__header">
          <h2 className="campaign-list__title">Campaigns</h2>
        </div>
        <div className="campaign-list__error">{error}</div>
      </div>
    );
  }

  return (
    <div className="campaign-list">
      <div className="campaign-list__header">
        <h2 className="campaign-list__title">Campaigns</h2>
        <button className="campaign-list__create-btn" onClick={onCreateCampaign}>
          + New Campaign
        </button>
      </div>

      {campaigns.length === 0 ? (
        <div className="campaign-list__empty">
          <div className="campaign-list__empty-icon">&#x1F4CB;</div>
          <h3>No campaigns yet</h3>
          <p>Create your first campaign to get started.</p>
          <button className="campaign-list__create-btn" onClick={onCreateCampaign}>
            + New Campaign
          </button>
        </div>
      ) : (
        <div className="campaign-list__grid">
          {campaigns.map((campaign) => {
            const status = STATUS_CONFIG[campaign.status] || STATUS_CONFIG.draft;
            return (
              <div
                key={campaign.id}
                className="campaign-card"
                onClick={() => onSelectCampaign(campaign)}
              >
                <div className="campaign-card__top">
                  <span className={`campaign-card__status ${status.className}`}>
                    {status.label}
                  </span>
                  <span className="campaign-card__date">{formatDate(campaign.created_at)}</span>
                </div>
                <h3 className="campaign-card__name">{campaign.name}</h3>
                {campaign.objective && (
                  <p className="campaign-card__objective">{campaign.objective}</p>
                )}
                <div className="campaign-card__footer">
                  {campaign.asset_count != null && (
                    <span className="campaign-card__assets">{campaign.asset_count} assets</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
