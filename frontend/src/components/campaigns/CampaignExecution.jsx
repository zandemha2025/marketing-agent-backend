import React, { useState, useEffect, useRef } from 'react';
import './CampaignExecution.css';

const PHASES = ['Research', 'Strategy', 'Creative', 'Production', 'Complete'];

export default function CampaignExecution({ campaignId, sessionId, onComplete }) {
  const [currentPhase, setCurrentPhase] = useState(null);
  const [progress, setProgress] = useState(0);
  const [messages, setMessages] = useState([]);
  const [completed, setCompleted] = useState(false);
  const [completionData, setCompletionData] = useState(null);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const logRef = useRef(null);

  useEffect(() => {
    if (!campaignId || !sessionId) return;

    const wsUrl = `ws://localhost:8000/api/campaigns/${campaignId}/ws/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ action: 'start' }));
      addMessage('system', 'Connected. Starting campaign execution...');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
          setCurrentPhase(data.phase);
          setProgress(data.progress || 0);
          if (data.message) {
            addMessage('progress', data.message, data.phase);
          }
        } else if (data.type === 'complete') {
          setCompleted(true);
          setCompletionData(data);
          setCurrentPhase('Complete');
          setProgress(100);
          addMessage('complete', 'Campaign execution complete.');
          if (onComplete) onComplete(data);
        } else if (data.type === 'error') {
          setError(data.message || 'Execution error');
          addMessage('error', data.message || 'An error occurred.');
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      setError('WebSocket connection error');
      addMessage('error', 'Connection error.');
    };

    ws.onclose = () => {
      if (!completed) {
        addMessage('system', 'Connection closed.');
      }
    };

    return () => {
      ws.close();
    };
  }, [campaignId, sessionId]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [messages]);

  const addMessage = (type, text, phase) => {
    setMessages((prev) => [
      ...prev,
      { id: Date.now() + Math.random(), type, text, phase, time: new Date() },
    ]);
  };

  const getPhaseIndex = (phaseName) => {
    if (!phaseName) return -1;
    return PHASES.findIndex((p) => phaseName.toLowerCase().includes(p.toLowerCase()));
  };

  const activeIndex = getPhaseIndex(currentPhase);

  if (completed && completionData) {
    return (
      <div className="campaign-exec">
        <div className="campaign-exec__complete">
          <div className="campaign-exec__complete-icon">&#10003;</div>
          <h2>Campaign Complete</h2>
          <p className="campaign-exec__complete-sub">All phases finished successfully.</p>
          {completionData.summary && (
            <p className="campaign-exec__complete-summary">{completionData.summary}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="campaign-exec">
      <h2 className="campaign-exec__title">Executing Campaign</h2>

      {error && <div className="campaign-exec__error">{error}</div>}

      <div className="campaign-exec__phases">
        {PHASES.map((phase, i) => {
          let state = 'pending';
          if (i < activeIndex) state = 'done';
          else if (i === activeIndex) state = 'active';

          return (
            <div key={phase} className={`campaign-exec__phase campaign-exec__phase--${state}`}>
              <div className="campaign-exec__phase-indicator">
                {state === 'done' ? (
                  <span className="campaign-exec__check">&#10003;</span>
                ) : (
                  <span>{i + 1}</span>
                )}
              </div>
              <span className="campaign-exec__phase-label">{phase}</span>
            </div>
          );
        })}
      </div>

      <div className="campaign-exec__progress-bar">
        <div className="campaign-exec__progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="campaign-exec__progress-text">{Math.round(progress)}%</div>

      <div className="campaign-exec__log" ref={logRef}>
        {messages.map((msg) => (
          <div key={msg.id} className={`campaign-exec__msg campaign-exec__msg--${msg.type}`}>
            <span className="campaign-exec__msg-time">
              {msg.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
            {msg.phase && <span className="campaign-exec__msg-phase">[{msg.phase}]</span>}
            <span className="campaign-exec__msg-text">{msg.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
