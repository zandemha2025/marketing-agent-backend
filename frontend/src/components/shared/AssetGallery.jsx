import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import AssetCard from './AssetCard';
import './AssetGallery.css';

function AssetGallery({ campaignId }) {
    const [assets, setAssets] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedAsset, setSelectedAsset] = useState(null);

    useEffect(() => {
        if (!campaignId) {
            setAssets([]);
            return;
        }
        let cancelled = false;
        setLoading(true);
        (async () => {
            try {
                const data = await api.listAssets(campaignId);
                if (!cancelled) {
                    setAssets(Array.isArray(data) ? data : data.assets || []);
                }
            } catch (err) {
                console.error('Failed to load assets:', err);
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [campaignId]);

    if (!campaignId) {
        return (
            <div className="asset-gallery-empty">
                <span className="asset-gallery-empty-icon">📦</span>
                <h3>No campaign selected</h3>
                <p>Select a campaign first to view its assets.</p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="asset-gallery-loading">
                <div className="asset-gallery-spinner" />
                <p>Loading assets...</p>
            </div>
        );
    }

    if (assets.length === 0) {
        return (
            <div className="asset-gallery-empty">
                <span className="asset-gallery-empty-icon">📦</span>
                <h3>No assets yet</h3>
                <p>Assets will appear here once they are generated for this campaign.</p>
            </div>
        );
    }

    return (
        <div className="asset-gallery">
            <div className="asset-gallery-grid">
                {assets.map(asset => (
                    <AssetCard
                        key={asset.id}
                        asset={asset}
                        onClick={() => setSelectedAsset(asset)}
                    />
                ))}
            </div>

            {selectedAsset && (
                <div className="asset-detail-overlay" onClick={() => setSelectedAsset(null)}>
                    <div className="asset-detail-panel" onClick={e => e.stopPropagation()}>
                        <div className="asset-detail-header">
                            <h3>{selectedAsset.name}</h3>
                            <button className="asset-detail-close" onClick={() => setSelectedAsset(null)}>
                                &times;
                            </button>
                        </div>
                        <div className="asset-detail-body">
                            {selectedAsset.content && (
                                <div className="asset-detail-content">
                                    {selectedAsset.content}
                                </div>
                            )}
                            <div className="asset-detail-meta">
                                <div className="asset-detail-field">
                                    <span className="asset-detail-label">Type</span>
                                    <span>{selectedAsset.type || '—'}</span>
                                </div>
                                <div className="asset-detail-field">
                                    <span className="asset-detail-label">Status</span>
                                    <span>{selectedAsset.status || '—'}</span>
                                </div>
                                <div className="asset-detail-field">
                                    <span className="asset-detail-label">Platform</span>
                                    <span>{selectedAsset.platform || '—'}</span>
                                </div>
                                <div className="asset-detail-field">
                                    <span className="asset-detail-label">Version</span>
                                    <span>{selectedAsset.version ?? 1}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default AssetGallery;
