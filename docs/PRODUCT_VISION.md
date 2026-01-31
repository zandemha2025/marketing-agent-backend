# Marketing Agent Platform: Product Vision

## The Core Problem

Current state: Website URL → Generic AI slop
What we need: An intelligent marketing partner that thinks and works like a senior agency strategist

## The Vision: "Claude Code for Marketing"

Just as Claude Code understands software engineering end-to-end (architecture, implementation, testing, debugging), this platform should understand marketing end-to-end:

- **Strategy**: Brand positioning, competitive analysis, audience insights
- **Creative**: Concept development, visual direction, copywriting
- **Execution**: Asset production, campaign management, optimization
- **Presentation**: Client-ready decks, rationale, storytelling

A "T-shaped marketer" that can go deep on any aspect while understanding the whole picture.

---

## What's Wrong Today

### 1. No Context Understanding
- We analyze a website, not the actual brief
- Real briefs are: "Launch the Air Max DN for Gen Z runners who care about sustainability"
- Not: "Make stuff for nike.com"

### 2. Generic Visuals
- Images look "AI" because they're not brand-specific
- Nike visuals should have: athletes in motion, high contrast, grit, product integration
- We generate: generic futuristic tech imagery

### 3. Pipeline, Not Intelligence
- Current flow is linear: research → strategy → concept → assets
- Real agencies iterate, explore territories, get buy-in at each stage
- No conversation, no understanding, no adaptation

### 4. Missing the "Why"
- Agencies justify every creative decision
- We just output stuff without rationale
- CMOs need to understand and defend choices to stakeholders

### 5. Developer UI, Not Enterprise UX
- The interface looks like a dev tool
- Enterprise clients expect polish, trust signals, professional presentation

---

## The New Architecture

### Phase 1: Intelligent Intake (Conversational)

Instead of a URL field, a conversation:

```
Agent: "What are we working on today?"

User: "Nike wants to launch the new Air Max DN"

Agent: "Got it - Air Max DN launch. Let me understand the brief better:
- Who's the primary audience? (I'm guessing Gen Z runners based on the DN line)
- What's the campaign goal? (Awareness, pre-orders, retail traffic?)
- Any specific channels or formats required?
- What's the timeline and budget range?
- Any reference campaigns or competitors to consider?"

User: "Gen Z, sustainability-focused. Goal is pre-order signups.
Social-first, especially TikTok and Instagram. $500K budget,
launching in 8 weeks. Look at what Adidas did with the Futurecraft."

Agent: "Perfect. Before I develop concepts, let me do some discovery:
- Deep dive on the Air Max DN (features, materials, sustainability story)
- Gen Z sustainability attitudes and sneaker culture
- Adidas Futurecraft campaign analysis
- Current Nike brand guidelines and recent campaigns
- TikTok/Instagram trends in sneaker marketing

I'll come back with a strategic foundation and 3 creative territories
for you to react to. Give me 10 minutes."
```

### Phase 2: Discovery & Research (Autonomous)

The agent researches like a strategist:
- Product deep-dive (features, USPs, sustainability claims)
- Audience insights (Gen Z values, sneaker culture, purchase drivers)
- Competitive analysis (Adidas Futurecraft, On Running, etc.)
- Platform trends (TikTok formats, Instagram best practices)
- Brand guidelines (Nike's visual language, tone, dos/don'ts)

Output: Research brief with key insights, not raw data

### Phase 3: Strategic Foundation

Present findings before creative work:

```
## Discovery Summary

### The Opportunity
Gen Z cares about sustainability but is skeptical of greenwashing.
The Air Max DN uses 20% recycled materials - real, but not revolutionary.
The opportunity isn't "we're sustainable" - it's "style doesn't require sacrifice."

### The Tension
"I want to look fresh AND feel good about my choices" - but most sustainable
sneakers look like they're trying too hard. Nike can own "sustainability that
doesn't compromise on style."

### Competitive Landscape
- Adidas Futurecraft: Tech-forward, lab aesthetic
- On Running: Performance-first, muted colors
- Gap: Nike can be bold AND sustainable (competitors are one or the other)

### Audience Insight
Gen Z doesn't want to be preached to. They want brands that share their
values without making it their whole personality.
```

### Phase 4: Creative Territories (Not Concepts)

Present 3 strategic directions, each with:
- **Territory Name**: The creative idea in 3 words
- **The Insight**: What human truth it's based on
- **Visual World**: Mood board with reference images
- **Tone**: How it sounds and feels
- **Why It Works**: Strategic rationale
- **Risk**: What could go wrong

Example territories:
1. **"Flex Different"** - Sustainability as quiet confidence, not loud activism
2. **"Made From Tomorrow"** - Future-forward tech aesthetic, innovation story
3. **"Run It Back"** - Circular economy, the shoe that keeps giving

Client picks a direction (or hybrid) before production begins.

### Phase 5: Creative Development

Only after territory approval:
- Full campaign concept with manifesto
- Detailed creative briefs per channel
- Copywriting (headlines, body, CTAs)
- Visual production with brand-authentic aesthetics
- Video scripts and storyboards

### Phase 6: Presentation

Output is a client-ready deck, not a list of files:
- Executive summary
- Strategic rationale
- Creative concept with visual examples
- Channel-by-channel breakdown
- Timeline and next steps
- Appendix with research

---

## Brand-Authentic Visuals

### The Problem
Current images are generic because we're prompting for "tech" or "futuristic" instead of brand DNA.

### The Solution

1. **Brand Reference Library**
   - Scrape the brand's actual campaigns (Nike.com, Instagram, YouTube)
   - Build a visual DNA profile: color grading, composition patterns, model casting, typography

2. **Style Transfer/IP-Adapter**
   - Use reference images from the brand's own work
   - Generate images that match their aesthetic, not generic AI style

3. **Product Integration**
   - For product launches, the PRODUCT must be in the image
   - Use product shots as reference/compositing base

4. **Human Direction**
   - Nike images feature real athletes with real sweat
   - We need to specify: "photograph of athlete mid-stride, Canon EOS R5, 85mm f/1.4, motion blur on background, sharp focus on subject, Nike campaign aesthetic"

5. **No AI Text**
   - Never generate text in images (already fixed)
   - Composite headlines using brand fonts after generation

---

## Enterprise UI/UX

### Current State: Developer Tool
- Dark mode, minimal, functional
- Progress bars and task lists
- File outputs in a grid

### Target State: Premium SaaS

**Dashboard**
- Active campaigns with status
- Recent activity feed
- Quick actions (new campaign, review pending)

**Campaign View**
- Visual timeline showing stages
- Current stage highlighted with context
- Approval gates clearly marked
- Comments and feedback inline

**Presentation Mode**
- Full-screen, beautiful presentation of work
- Shareable links for client review
- Annotation and feedback tools
- Version history

**Asset Library**
- Organized by campaign/channel
- Preview, download, share
- Edit history and approval status

**Brand Center**
- Brand guidelines stored and referenced
- Asset library (logos, fonts, approved images)
- Tone of voice documentation

---

## Technical Implementation

### New Agent Architecture

```
ConversationalIntake
    ↓
DiscoveryAgent (autonomous research)
    ↓
StrategyAgent (insights → territories)
    ↓
[CLIENT APPROVAL GATE]
    ↓
ConceptAgent (territory → full concept)
    ↓
[CLIENT APPROVAL GATE]
    ↓
ExecutionAgents (copy, design, video, web)
    ↓
PresentationAgent (package into deck)
```

### Key New Components

1. **Conversational Interface**
   - Chat-based brief intake
   - Clarifying questions
   - Ongoing dialogue throughout

2. **Approval Gates**
   - Pause workflow for client input
   - Present options for decisions
   - Track approvals and feedback

3. **Brand DNA Engine**
   - Crawl and analyze brand's visual/verbal identity
   - Store as reference for all generation
   - Auto-apply to all outputs

4. **Presentation Generator**
   - Turn campaign into beautiful deck
   - Auto-generate rationale text
   - Include visual examples in context

5. **Reference Image System**
   - IP-Adapter or style transfer integration
   - Product shot compositing
   - Brand image matching

---

## Success Metrics

### Quality
- Would this pass creative review at an agency?
- Would a CMO feel comfortable presenting this to their board?
- Does it look like the brand, not generic AI?

### Process
- Does the workflow mirror how agencies actually work?
- Are decisions justified with rationale?
- Can clients give feedback at appropriate stages?

### Business
- Would enterprise clients pay $50K+/year for this?
- Does it replace 80% of the agency discovery/concept phase?
- Does it accelerate time-to-market by 10x?

---

## Next Steps

1. **Conversational Intake**: Build chat interface for brief development
2. **Discovery Agent**: Autonomous research with structured output
3. **Territory System**: Multiple creative directions with rationale
4. **Approval Gates**: Pause points with client decision UI
5. **Brand DNA Engine**: Visual/verbal brand analysis and storage
6. **Presentation Mode**: Beautiful output packaging
7. **Reference Images**: Style transfer and product integration
8. **Enterprise UI**: Full redesign of interface

---

## The North Star

A CMO at Nike should be able to say:

"Create a campaign for the Air Max DN launch targeting Gen Z on TikTok and Instagram, focusing on sustainability without being preachy. Budget is $500K, launching in 8 weeks. Reference the Adidas Futurecraft approach but make it more Nike."

And get back:
1. A strategic brief showing we understood the opportunity
2. Three creative territories with mood boards to choose from
3. A full campaign concept with rationale for every choice
4. Production-ready assets that look like Nike made them
5. A presentation deck ready to share with stakeholders

All in the time it would take an agency to schedule the kickoff meeting.
