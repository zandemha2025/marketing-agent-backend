import React from 'react';
import './ProgressIndicator.css';

function ProgressIndicator({ phases = [], currentPhase = 0 }) {
    return (
        <div className="progress-indicator">
            {phases.map((phase, index) => {
                const status = phase.status || (
                    index < currentPhase ? 'complete' :
                    index === currentPhase ? 'active' : 'pending'
                );

                return (
                    <React.Fragment key={index}>
                        {index > 0 && (
                            <div className={`progress-line progress-line--${status === 'pending' ? 'pending' : 'filled'}`} />
                        )}
                        <div className={`progress-step progress-step--${status}`}>
                            <div className="progress-circle">
                                {status === 'complete' ? (
                                    <svg viewBox="0 0 16 16" width="14" height="14" fill="none">
                                        <path d="M3 8.5l3 3 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                ) : (
                                    <span className="progress-dot" />
                                )}
                            </div>
                            <span className="progress-label">{phase.name}</span>
                        </div>
                    </React.Fragment>
                );
            })}
        </div>
    );
}

export default ProgressIndicator;
