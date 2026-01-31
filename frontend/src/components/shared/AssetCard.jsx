import React from 'react';
import {
    FileText,
    Image,
    Video,
    Mail,
    Share2,
    Megaphone,
    Globe,
    File
} from 'lucide-react';
import './AssetCard.css';

const TYPE_ICONS = {
    copy: <FileText size={20} />,
    image: <Image size={20} />,
    video: <Video size={20} />,
    email: <Mail size={20} />,
    social: <Share2 size={20} />,
    blog: <FileText size={20} />,
    ad: <Megaphone size={20} />,
    landing_page: <Globe size={20} />,
};

function AssetCard({ asset, onClick }) {
    const icon = TYPE_ICONS[asset.type] || <File size={20} />;
    const status = asset.status || 'draft';

    return (
        <div className="asset-card" onClick={onClick}>
            <div className="asset-card-icon">{icon}</div>
            <div className="asset-card-body">
                <h4 className="asset-card-name">{asset.name || 'Untitled Asset'}</h4>
                <div className="asset-card-row">
                    <span className={`asset-card-status asset-card-status--${status.toLowerCase()}`}>
                        {status}
                    </span>
                    {asset.platform && (
                        <span className="asset-card-platform">{asset.platform}</span>
                    )}
                </div>
            </div>
            <div className="asset-card-version">v{asset.version ?? 1}</div>
        </div>
    );
}

export default AssetCard;
