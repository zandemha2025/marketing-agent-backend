/**
 * Version and Build Information
 *
 * This module provides version tracking to prevent confusion between
 * different frontend builds during development and production.
 */

// These are injected by Vite at build time
export const APP_VERSION = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '2.0.0';
export const BUILD_TIMESTAMP = typeof __BUILD_TIMESTAMP__ !== 'undefined' ? __BUILD_TIMESTAMP__ : new Date().toISOString();
export const BUILD_ID = typeof __BUILD_ID__ !== 'undefined' ? __BUILD_ID__ : 'dev';
export const BUILD_ENV = typeof __BUILD_ENV__ !== 'undefined' ? __BUILD_ENV__ : 'development';

// Environment variables from Vite
export const ENV = import.meta.env.VITE_ENV || 'development';
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const DEBUG_ENABLED = import.meta.env.VITE_ENABLE_DEBUG === 'true';

/**
 * Get formatted version string for display
 */
export function getVersionString() {
    return `v${APP_VERSION} (${BUILD_ENV})`;
}

/**
 * Get full version info for debugging
 */
export function getVersionInfo() {
    return {
        version: APP_VERSION,
        buildId: BUILD_ID,
        buildTimestamp: BUILD_TIMESTAMP,
        buildEnv: BUILD_ENV,
        environment: ENV,
        apiUrl: API_URL,
    };
}

/**
 * Log version info to console on app start
 */
export function logVersionInfo() {
    const info = getVersionInfo();
    console.log(
        `%c Marketing Agent ${info.version} %c ${info.buildEnv.toUpperCase()} %c`,
        'background: #f97316; color: white; padding: 4px 8px; border-radius: 4px 0 0 4px; font-weight: bold;',
        `background: ${info.buildEnv === 'production' ? '#22c55e' : '#3b82f6'}; color: white; padding: 4px 8px; border-radius: 0 4px 4px 0;`,
        ''
    );
    console.log('Build ID:', info.buildId);
    console.log('Build Time:', new Date(info.buildTimestamp).toLocaleString());
    console.log('API URL:', info.apiUrl);
}

/**
 * Check if running in development mode
 */
export function isDevelopment() {
    return BUILD_ENV === 'development' || ENV === 'development';
}

/**
 * Check if running in production mode
 */
export function isProduction() {
    return BUILD_ENV === 'production' && ENV === 'production';
}
