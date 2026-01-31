import React, { useState } from 'react';
import api from '../../services/api';
import './CampaignCreate.css';

const PLATFORMS = ['Instagram', 'LinkedIn', 'Twitter', 'Facebook', 'Google Ads', 'Email'];
const BUDGET_TIERS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
];

export default function CampaignCreate({ organizationId, onCreated, onCancel }) {
  const [form, setForm] = useState({
    name: '',
    objective: '',
    product_focus: '',
    target_audience: '',
    budget_tier: 'medium',
    timeline: '',
    platforms: [],
    yolo_mode: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const togglePlatform = (platform) => {
    setForm((prev) => ({
      ...prev,
      platforms: prev.platforms.includes(platform)
        ? prev.platforms.filter((p) => p !== platform)
        : [...prev.platforms, platform],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.objective.trim()) {
      setError('Name and objective are required.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const result = await api.createCampaign({
        organization_id: organizationId,
        ...form,
      });
      onCreated(result);
    } catch (err) {
      setError(err.message || 'Failed to create campaign');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="campaign-create__overlay" onClick={onCancel}>
      <div className="campaign-create__modal" onClick={(e) => e.stopPropagation()}>
        <div className="campaign-create__header">
          <h2>New Campaign</h2>
          <button className="campaign-create__close" onClick={onCancel} aria-label="Close">
            &times;
          </button>
        </div>

        <form className="campaign-create__form" onSubmit={handleSubmit}>
          {error && <div className="campaign-create__error">{error}</div>}

          <label className="campaign-create__label">
            Campaign Name *
            <input
              type="text"
              className="campaign-create__input"
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
              placeholder="Q1 Brand Awareness Push"
            />
          </label>

          <label className="campaign-create__label">
            Objective *
            <textarea
              className="campaign-create__textarea"
              value={form.objective}
              onChange={(e) => updateField('objective', e.target.value)}
              placeholder="Describe the campaign goal..."
              rows={3}
            />
          </label>

          <label className="campaign-create__label">
            Product Focus
            <input
              type="text"
              className="campaign-create__input"
              value={form.product_focus}
              onChange={(e) => updateField('product_focus', e.target.value)}
              placeholder="e.g. New SaaS Dashboard"
            />
          </label>

          <label className="campaign-create__label">
            Target Audience
            <input
              type="text"
              className="campaign-create__input"
              value={form.target_audience}
              onChange={(e) => updateField('target_audience', e.target.value)}
              placeholder="e.g. Marketing managers at mid-market B2B companies"
            />
          </label>

          <div className="campaign-create__row">
            <label className="campaign-create__label">
              Budget Tier
              <select
                className="campaign-create__select"
                value={form.budget_tier}
                onChange={(e) => updateField('budget_tier', e.target.value)}
              >
                {BUDGET_TIERS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </label>

            <label className="campaign-create__label">
              Timeline
              <input
                type="text"
                className="campaign-create__input"
                value={form.timeline}
                onChange={(e) => updateField('timeline', e.target.value)}
                placeholder="e.g. 4 weeks"
              />
            </label>
          </div>

          <fieldset className="campaign-create__fieldset">
            <legend className="campaign-create__legend">Platforms</legend>
            <div className="campaign-create__platforms">
              {PLATFORMS.map((p) => (
                <label key={p} className="campaign-create__checkbox-label">
                  <input
                    type="checkbox"
                    checked={form.platforms.includes(p)}
                    onChange={() => togglePlatform(p)}
                  />
                  <span>{p}</span>
                </label>
              ))}
            </div>
          </fieldset>

          {/* YOLO Mode Toggle */}
          <div className="campaign-create__yolo">
            <label className="campaign-create__yolo-toggle">
              <input
                type="checkbox"
                checked={form.yolo_mode}
                onChange={(e) => updateField('yolo_mode', e.target.checked)}
              />
              <span className="yolo-toggle__slider"></span>
              <span className="yolo-toggle__label">
                <strong>YOLO Mode</strong>
                <small>Skip approval steps and run end-to-end automatically</small>
              </span>
            </label>
            {form.yolo_mode && (
              <div className="yolo-warning">
                ⚡ The AI will automatically select the best concept and generate all assets without pausing for your approval.
              </div>
            )}
          </div>

          <div className="campaign-create__actions">
            <button type="button" className="campaign-create__cancel-btn" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="campaign-create__submit-btn" disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Campaign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
