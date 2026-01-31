import React, { useState } from 'react';
import './OnboardingResult.css';

function OnboardingResult({ result, onComplete, organizationId }) {
    const [activeTab, setActiveTab] = useState('brand');

    const tabs = [
        { id: 'brand', label: 'Brand' },
        { id: 'market', label: 'Market' },
        { id: 'audiences', label: 'Audiences' },
        { id: 'offerings', label: 'Offerings' },
    ];

    return (
        <div className="onboarding-result animate-fadeIn">
            <div className="result-header">
                <h2>Here's what we found</h2>
                <p>
                    We analyzed {result.pages_analyzed || 'your website'} and gathered insights
                    about your brand. Review and continue when ready.
                </p>
            </div>

            {/* Tab navigation */}
            <div className="result-tabs">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab content */}
            <div className="result-content">
                {activeTab === 'brand' && <BrandTab brand={result.brand} />}
                {activeTab === 'market' && <MarketTab market={result.market} />}
                {activeTab === 'audiences' && <AudiencesTab audiences={result.audiences} />}
                {activeTab === 'offerings' && <OfferingsTab offerings={result.offerings} />}
            </div>

            {/* Actions */}
            <div className="result-actions">
                <button className="btn btn-primary" onClick={onComplete}>
                    Continue
                </button>
            </div>
        </div>
    );
}

function BrandTab({ brand }) {
    if (!brand) return <EmptyState message="No brand data available" />;

    return (
        <div className="tab-content">
            <div className="brand-header">
                <div className="brand-name-section">
                    <h3>{brand.name}</h3>
                    {brand.domain && <span className="domain">{brand.domain}</span>}
                </div>
                {brand.tagline && <p className="tagline">"{brand.tagline}"</p>}
            </div>

            {brand.description && (
                <Section title="About">
                    <p>{brand.description}</p>
                </Section>
            )}

            {brand.voice?.tone?.length > 0 && (
                <Section title="Brand voice">
                    <TagList tags={brand.voice.tone} />
                </Section>
            )}

            {brand.values?.length > 0 && (
                <Section title="Values">
                    <TagList tags={brand.values} variant="accent" />
                </Section>
            )}

            {brand.voice?.vocabulary?.length > 0 && (
                <Section title="Key phrases">
                    <TagList tags={brand.voice.vocabulary.slice(0, 8)} variant="outline" />
                </Section>
            )}
        </div>
    );
}

function MarketTab({ market }) {
    if (!market) return <EmptyState message="No market data available" />;

    return (
        <div className="tab-content">
            {market.industry && (
                <Section title="Industry">
                    <span className="industry-label">{market.industry}</span>
                </Section>
            )}

            {market.market_position && (
                <Section title="Market position">
                    <p>{market.market_position}</p>
                </Section>
            )}

            {market.competitors?.length > 0 && (
                <Section title="Competitors">
                    <div className="competitors-list">
                        {market.competitors.map((comp, i) => (
                            <div key={i} className="competitor-item">
                                <strong>{comp.name}</strong>
                                {comp.positioning && <p>{comp.positioning}</p>}
                            </div>
                        ))}
                    </div>
                </Section>
            )}

            {market.opportunities?.length > 0 && (
                <Section title="Opportunities">
                    <ul className="simple-list">
                        {market.opportunities.map((opp, i) => (
                            <li key={i}>{opp}</li>
                        ))}
                    </ul>
                </Section>
            )}
        </div>
    );
}

function AudiencesTab({ audiences }) {
    if (!audiences?.segments?.length) {
        return <EmptyState message="No audience data available" />;
    }

    return (
        <div className="tab-content">
            {audiences.segments.map((segment, i) => (
                <div key={i} className="audience-segment">
                    <div className="segment-header">
                        <h4>{segment.name}</h4>
                        {segment.size && <span className="segment-badge">{segment.size}</span>}
                    </div>

                    {segment.pain_points?.length > 0 && (
                        <div className="segment-section">
                            <strong>Pain points</strong>
                            <ul className="simple-list">
                                {segment.pain_points.map((point, j) => (
                                    <li key={j}>{point}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {segment.preferred_channels?.length > 0 && (
                        <div className="segment-section">
                            <strong>Preferred channels</strong>
                            <TagList tags={segment.preferred_channels} />
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

function OfferingsTab({ offerings }) {
    if (!offerings) return <EmptyState message="No offerings data available" />;

    const hasProducts = offerings.products?.length > 0;
    const hasServices = offerings.services?.length > 0;

    if (!hasProducts && !hasServices) {
        return <EmptyState message="No products or services detected" />;
    }

    return (
        <div className="tab-content">
            {hasProducts && (
                <Section title="Products">
                    <div className="offerings-list">
                        {offerings.products.map((product, i) => (
                            <div key={i} className="offering-item">
                                <strong>{product.name}</strong>
                                {product.description && <p>{product.description}</p>}
                            </div>
                        ))}
                    </div>
                </Section>
            )}

            {hasServices && (
                <Section title="Services">
                    <div className="offerings-list">
                        {offerings.services.map((service, i) => (
                            <div key={i} className="offering-item">
                                <strong>{service.name}</strong>
                                {service.description && <p>{service.description}</p>}
                            </div>
                        ))}
                    </div>
                </Section>
            )}

            {offerings.key_differentiators?.length > 0 && (
                <Section title="Key differentiators">
                    <ul className="simple-list">
                        {offerings.key_differentiators.map((diff, i) => (
                            <li key={i}>{diff}</li>
                        ))}
                    </ul>
                </Section>
            )}
        </div>
    );
}

// Reusable components
function Section({ title, children }) {
    return (
        <div className="section">
            <h5 className="section-title">{title}</h5>
            {children}
        </div>
    );
}

function TagList({ tags, variant = 'default' }) {
    return (
        <div className="tag-list">
            {tags.map((tag, i) => (
                <span key={i} className={`tag tag-${variant}`}>
                    {tag}
                </span>
            ))}
        </div>
    );
}

function EmptyState({ message }) {
    return (
        <div className="empty-state">
            <p>{message}</p>
        </div>
    );
}

export default OnboardingResult;
