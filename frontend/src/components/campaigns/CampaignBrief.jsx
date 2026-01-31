import React from 'react';
import './CampaignBrief.css';

const SECTION_ORDER = [
  { key: 'executive_summary', title: 'Executive Summary' },
  { key: 'business_context', title: 'Business Context' },
  { key: 'market_situation', title: 'Market Situation' },
  { key: 'objectives', title: 'Objectives' },
  { key: 'target_audiences', title: 'Target Audiences' },
  { key: 'key_messages', title: 'Key Messages' },
  { key: 'creative_direction', title: 'Creative Direction' },
  { key: 'channels', title: 'Channels' },
  { key: 'budget', title: 'Budget' },
  { key: 'timeline', title: 'Timeline' },
  { key: 'success_metrics', title: 'Success Metrics' },
];

function renderValue(value) {
  if (value == null) return null;

  if (Array.isArray(value)) {
    return (
      <ul className="campaign-brief__list">
        {value.map((item, i) => (
          <li key={i}>
            {typeof item === 'object' ? renderObject(item) : String(item)}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof value === 'object') {
    return renderObject(value);
  }

  return <p className="campaign-brief__text">{String(value)}</p>;
}

function renderObject(obj) {
  return (
    <div className="campaign-brief__nested">
      {Object.entries(obj).map(([k, v]) => (
        <div key={k} className="campaign-brief__nested-item">
          <span className="campaign-brief__nested-key">
            {k.replace(/_/g, ' ')}:
          </span>{' '}
          {typeof v === 'object' ? renderValue(v) : String(v)}
        </div>
      ))}
    </div>
  );
}

export default function CampaignBrief({ brief }) {
  if (!brief) {
    return (
      <div className="campaign-brief campaign-brief--empty">
        <p>No brief available yet.</p>
      </div>
    );
  }

  const knownKeys = new Set(SECTION_ORDER.map((s) => s.key));
  const extraKeys = Object.keys(brief).filter((k) => !knownKeys.has(k) && brief[k] != null);

  return (
    <article className="campaign-brief">
      <header className="campaign-brief__header">
        <h1 className="campaign-brief__title">Campaign Brief</h1>
        <div className="campaign-brief__divider" />
      </header>

      {SECTION_ORDER.map(({ key, title }) => {
        const value = brief[key];
        if (value == null) return null;
        return (
          <section key={key} className="campaign-brief__section">
            <h2 className="campaign-brief__section-title">{title}</h2>
            {renderValue(value)}
          </section>
        );
      })}

      {extraKeys.map((key) => (
        <section key={key} className="campaign-brief__section">
          <h2 className="campaign-brief__section-title">
            {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
          </h2>
          {renderValue(brief[key])}
        </section>
      ))}
    </article>
  );
}
