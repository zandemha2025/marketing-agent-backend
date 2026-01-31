import React from "react";
import { ConvexProvider as BaseConvexProvider, ConvexReactClient } from "convex/react";

// Get the Convex URL from environment variables
// Falls back to the deployed Convex URL
const convexUrl = (import.meta as any).env?.VITE_CONVEX_URL || "https://steady-pig-234.convex.cloud";

const convex = new ConvexReactClient(convexUrl);

// Wrapper component that provides the Convex client
function ConvexProvider({ children }: { children: React.ReactNode }) {
    return (
        <BaseConvexProvider client={convex}>
            {children}
        </BaseConvexProvider>
    );
}

export { convex, ConvexProvider };