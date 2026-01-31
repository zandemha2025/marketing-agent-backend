I fully understand. We are not just filling out a form; we are building the **Brand DNA** that will power the entire autonomous agency. If the Orchestrator doesn't deeply understand the client (like Nike's history, specific product lines like Air Max vs. Pegasus, and their exact tone), it cannot effectively act as a Creative Director or Strategist later.

I will transform the onboarding flow into a **Deep Research Engine** that leverages FireCrawl and Perplexity to their absolute limits.

### **Implementation Plan: Building the Brand DNA Engine**

#### **1. FireCrawl: Strategic Deep Dive (The "Eyes")**
*   **Smart Strategic Crawling**: Instead of a flat 50-page crawl, implement a "Smart Sampler" that identifies and prioritizes high-value sections:
    *   **Brand Core**: `/about`, `/history`, `/mission`, `/careers` (for culture).
    *   **Product Pillars**: Identify major categories (e.g., "Running", "Basketball") and deeply analyze representative product pages for each.
    *   **Press & IR**: Scan for recent press releases and investor reports (crucial for public companies like Nike).
*   **Content-to-DNA Extraction**: Use an LLM to read the *content* of these pages to extract:
    *   **Manifesto & Voice**: Not just keywords, but the actual rhetorical style (e.g., "Inspirational, punchy, athlete-focused").
    *   **Visual Language**: Analyze descriptions of imagery and design systems.

#### **2. Perplexity: Massive Multi-Dimensional Research (The "Brain")**
*   **Expanded Research Modules**: Go beyond basic "competitors" to include:
    *   **Brand Heritage**: History, founding story, and evolution.
    *   **Cultural Impact**: How the brand sits in culture (citations required).
    *   **Advertising Strategy**: Analysis of recent campaigns and messaging pillars.
*   **Citation-Backed Knowledge**: Ensure every insight in the Brand DNA includes **Perplexity citations**. The Orchestrator must know *where* it learned a fact (e.g., "According to 2024 Annual Report...").
*   **Dynamic Fallbacks**: Remove all hardcoded B2B defaults. If research is ambiguous, the agent must ask clarifying questions or dig deeper, never guess "Technology Company".

#### **3. Synthesis: Constructing the Brand Kit**
*   **Unified Brand DNA Object**: Create a robust data structure that holds:
    *   **Core Identity**: Mission, Vision, Values, Voice (with examples).
    *   **Strategic Context**: SWOT, Market Position, Competitor Landscape.
    *   **Product Ecosystem**: A structured hierarchy of offerings.
    *   **Knowledge Graph**: Links to sources and citations.

**Immediate First Step**:
I will start by **removing the broken heuristics and defaults** (the "Technology" and "B2B" fallbacks) and hooking up the **LLM-based analysis** for the Nike.com test case. This will immediately fix the "generic" results while we build out the deeper "Massive Research" capabilities.
