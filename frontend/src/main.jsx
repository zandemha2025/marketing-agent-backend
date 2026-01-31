import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/tokens.css';
import './styles/global.css';
// import { ConvexProvider } from './convex';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';
import { logVersionInfo, isDevelopment } from './utils/version';

// Log version info on app start (helps identify which build is running)
logVersionInfo();

// In development, add version indicator to document title
if (isDevelopment()) {
    document.title = `${document.title} [DEV]`;
}

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <ErrorBoundary>
            <ToastProvider>
                {/* <ConvexProvider> */}
                    <App />
                {/* </ConvexProvider> */}
            </ToastProvider>
        </ErrorBoundary>
    </React.StrictMode>
);