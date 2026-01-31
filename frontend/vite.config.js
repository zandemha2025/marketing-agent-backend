import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    // Load env file based on `mode` in the current working directory.
    const env = loadEnv(mode, process.cwd(), '');

    // Generate build timestamp for version tracking
    const buildTimestamp = new Date().toISOString();
    const buildId = `${Date.now().toString(36)}-${Math.random().toString(36).substr(2, 5)}`;

    return {
        plugins: [react()],

        // Define global constants available in the app
        define: {
            '__APP_VERSION__': JSON.stringify(env.VITE_APP_VERSION || '2.0.0'),
            '__BUILD_TIMESTAMP__': JSON.stringify(buildTimestamp),
            '__BUILD_ID__': JSON.stringify(buildId),
            '__BUILD_ENV__': JSON.stringify(mode),
        },

        server: {
            port: 3000,
            host: true,
            proxy: {
                '/api': {
                    target: env.VITE_API_URL || 'http://localhost:8000',
                    changeOrigin: true,
                    ws: true,  // Enable WebSocket proxying
                },
            },
        },

        build: {
            // Output directory
            outDir: 'dist',

            // Generate source maps for production debugging
            sourcemap: mode !== 'production',

            // Rollup options for better chunking
            rollupOptions: {
                output: {
                    manualChunks: {
                        'vendor': ['react', 'react-dom'],
                        'ui': ['lucide-react'],
                    },
                },
            },
        },

        // Preview server config (for testing production builds locally)
        preview: {
            port: 3001,
            host: true,
        },
    };
});
