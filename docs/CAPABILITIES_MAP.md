# Marketing Agent: Full Capabilities Map

## The Core Principle

This agent must understand marketing the way Claude Code understands software engineering:
- Not just "write code" but understand architecture, dependencies, testing, deployment
- Not just "make marketing" but understand strategy, channels, audiences, creative, measurement

When a user says "launch campaign for Nike Air Max DN", the agent should KNOW:
- What a product launch campaign requires
- What Nike's brand looks like
- What channels make sense for sneaker launches
- What creative formats each channel needs
- How to integrate the actual product into visuals
- What success looks like and how to measure it

---

## 1. BRAND INTELLIGENCE (The Foundation)

Before ANY campaign work, the agent needs deep brand understanding:

### Brand DNA Profile
- **Visual Identity**: Logo variants, color palette (primary/secondary/accent), typography (heading/body), photography style, illustration style
- **Verbal Identity**: Tone of voice, vocabulary, phrases they use/avoid, taglines, manifesto
- **Positioning**: Who they are, who they're not, competitive differentiation
- **Audience**: Primary/secondary personas with demographics, psychographics, pain points
- **Products/Services**: Full catalog understanding, features, benefits, pricing
- **Past Campaigns**: What they've done, what worked, what didn't, learnings
- **Guidelines**: Dos and don'ts, approval requirements, legal constraints

### Brand Intelligence Storage
- Persistent storage per client (not re-researched every time)
- Updated when new campaigns launch or guidelines change
- Referenced automatically in all generation

### Product Deep-Dive
- When launching a specific product:
  - Features, specs, materials
  - Unique selling points
  - Target audience (may differ from brand-wide)
  - Competitive products
  - Product imagery for compositing
  - Pricing and availability

---

## 2. CAMPAIGN TYPES (Each Has Different Requirements)

### Product Launch
**Required**: Product imagery, feature deep-dive, launch timeline, availability info
**Channels**: Usually full-funnel (awareness → consideration → conversion)
**Deliverables**:
- Hero creative with product integration
- Product detail page / landing page
- Email announcement + sequence
- Social (teaser → reveal → ongoing)
- Paid ads (awareness + retargeting)
- PR / influencer kit
- Retail / POS materials (if applicable)

### Brand Awareness
**Required**: Clear differentiation, emotional territory, memorable creative
**Channels**: Top-of-funnel focus (video, social, display)
**Deliverables**:
- Brand manifesto / anthem video
- Social content series
- Display / video ads
- PR narrative

### Lead Generation
**Required**: Clear value prop, lead magnet, nurture strategy
**Channels**: Performance-focused (search, social, email)
**Deliverables**:
- Landing page with form
- Lead magnet (ebook, webinar, tool)
- Email nurture sequence
- Paid ads (search, social, display)
- Retargeting creative

### Seasonal / Promotional
**Required**: Offer details, urgency mechanics, promo codes
**Channels**: Conversion-focused
**Deliverables**:
- Promotional creative
- Email blast + reminder sequence
- Landing page
- Paid ads
- Social posts

### Event
**Required**: Event details, registration flow, content agenda
**Channels**: Registration-focused + follow-up
**Deliverables**:
- Event landing page
- Registration emails
- Reminder sequence
- Social promotion
- Post-event follow-up
- Content from event (if applicable)

### Retention / Loyalty
**Required**: Customer data, loyalty mechanics, personalization
**Channels**: Owned (email, app, SMS)
**Deliverables**:
- Email sequences (onboarding, re-engagement, win-back)
- Loyalty program creative
- Personalized recommendations
- NPS / feedback requests

---

## 3. CHANNEL REQUIREMENTS (What Each Actually Needs)

### Instagram
**Formats**: Feed post (1:1, 4:5), Carousel (up to 10), Story (9:16), Reel (9:16)
**Creative Requirements**:
- Feed: High-quality imagery, strong visual hook, text overlay optional
- Carousel: Each slide tells part of story, CTA on last slide
- Story: Full-screen, interactive elements (polls, links, stickers)
- Reel: Hook in first 1 sec, trending audio, 15-60 sec
**Copy**: Caption (2,200 char max), hashtags (3-5 relevant), CTA
**Best Practices**: Faces perform better, authenticity > polish for Reels

### TikTok
**Formats**: Standard video (9:16), Carousel photos
**Creative Requirements**:
- Hook in first second (or swipe away)
- Native look (not polished ads)
- Trending sounds/formats
- 15-60 seconds optimal
**Copy**: Caption (2,200 char), hashtags (3-5), sounds
**Best Practices**: UGC-style outperforms branded, humor works, faces essential

### LinkedIn
**Formats**: Text post, Single image, Carousel (PDF), Video, Article
**Creative Requirements**:
- Professional but not boring
- Educational content performs best
- Faces (especially leadership) perform well
- Document carousels for thought leadership
**Copy**: 3,000 char max, but 150-300 optimal, no hashtag stuffing
**Best Practices**: Personal POV > brand speak, controversy drives engagement

### Twitter/X
**Formats**: Text, Image, Video, Thread
**Creative Requirements**:
- Strong hook in first line
- Images: 2:1 or 16:9 for optimal display
- Video: Short, captioned, autoplay-optimized
**Copy**: 280 char, threads for longer content
**Best Practices**: Hot takes > safe content, timing matters

### YouTube
**Formats**: Long-form, Shorts (60 sec max)
**Creative Requirements**:
- Long-form: Hook in 30 sec, chaptered, SEO-optimized
- Shorts: Hook in 1 sec, vertical, trend-aware
- Thumbnails critical (faces, contrast, text)
**Copy**: Title (SEO), description (links, timestamps), tags

### Email
**Formats**: Announcement, Newsletter, Nurture, Transactional, Win-back
**Creative Requirements**:
- Mobile-first design
- Clear CTA above fold
- Personalization
- Plain text option
**Copy**: Subject (40 char), preheader (90 char), body, CTA
**Best Practices**: Segmentation > blast, timing matters, test subject lines

### Paid Ads
**Google Search**: Headlines (30 char x3), descriptions (90 char x2), keywords
**Google Display**: Various sizes (300x250, 728x90, 160x600, etc.), responsive
**Meta (FB/IG)**: Primary text (125 char), headline (40 char), multiple creative variants
**LinkedIn Ads**: Sponsored content, message ads, text ads
**TikTok Ads**: Spark ads (boost organic), TopView, In-feed

### Landing Pages
**Requirements**:
- Hero section with value prop
- Social proof
- Feature/benefit breakdown
- CTA (form, button, purchase)
- Mobile responsive
- Fast load time
**Variations**: Lead gen (form), Product (purchase), Event (register)

### Website
**Requirements**:
- Homepage
- Product/service pages
- About
- Contact
- Blog (if content marketing)
- Navigation structure
- SEO foundation

---

## 4. AUDIENCE INTELLIGENCE

### Persona Development
- **Demographics**: Age, gender, location, income, education
- **Psychographics**: Values, interests, lifestyle, personality
- **Behavioral**: Purchase patterns, media consumption, decision process
- **Pain Points**: Problems they're trying to solve
- **Goals**: What success looks like for them
- **Objections**: What might stop them from buying

### ICP (Ideal Customer Profile)
- Company size, industry, revenue
- Tech stack, tools used
- Decision-making process
- Budget cycle
- Common challenges

### Audience Segments
- Multiple personas = multiple creative variations
- Personalization per segment
- Different messaging per awareness stage

---

## 5. CREATIVE PRODUCTION CAPABILITIES

### Imagery
- **Hero Images**: Brand-authentic, product-integrated, premium quality
- **Social Graphics**: Platform-optimized dimensions, text overlay
- **Ad Creatives**: Multiple sizes, variants for testing
- **Product Photography**: Compositing, lifestyle integration
- **Mood Boards**: Visual territory exploration

### Video
- **Brand Videos**: Anthem, manifesto, story
- **Product Videos**: Demo, features, unboxing
- **Social Videos**: TikTok-native, Reels, Stories
- **Ads**: 6-sec bumper, 15-sec, 30-sec
- **Explainer**: Animated, live-action hybrid

### Copy
- **Headlines**: Punchy, benefit-driven, variations
- **Body Copy**: Long-form, short-form, emotional, rational
- **CTAs**: Action-oriented, benefit-focused
- **Email**: Subject lines, preview text, body
- **Ad Copy**: Platform-specific constraints
- **Scripts**: Video, podcast, voiceover

### Design
- **Landing Pages**: Wireframe → design → code
- **Email Templates**: Responsive, brand-consistent
- **Presentation Decks**: Strategy, creative, reporting
- **Social Templates**: Branded, reusable
- **Print Materials**: If applicable (brochures, posters)

---

## 6. STRATEGIC CAPABILITIES

### Research & Analysis
- Competitor analysis
- Market trends
- Audience research
- Cultural moments
- Platform trends

### Strategy Development
- Campaign strategy
- Channel strategy
- Content strategy
- Budget allocation
- Timeline planning

### Creative Strategy
- Tension identification
- Creative territories
- Concept development
- Manifesto writing
- Visual world development

### Media Planning
- Channel selection
- Budget allocation
- Timing strategy
- Targeting strategy
- Measurement plan

---

## 7. MEASUREMENT & OPTIMIZATION

### KPIs by Objective
- **Awareness**: Reach, impressions, video views, brand lift
- **Consideration**: Engagement, clicks, time on site, email opens
- **Conversion**: Leads, sales, sign-ups, ROAS
- **Retention**: Repeat purchase, LTV, NPS, churn

### Attribution
- First-touch vs last-touch
- Multi-touch models
- Incrementality testing

### Testing
- A/B testing creative
- Multivariate testing
- Audience testing
- Message testing

---

## 8. WORKFLOW & COLLABORATION

### Approval Gates
1. **Brief Approval**: Align on strategy before creative
2. **Territory Approval**: Pick direction before development
3. **Concept Approval**: Approve concept before production
4. **Creative Approval**: Review deliverables before launch
5. **Final Sign-off**: Legal, brand, stakeholder

### Feedback Loops
- Comment on specific elements
- Version control
- Revision tracking
- Stakeholder management

### Deliverable Packaging
- Organized file structure
- Naming conventions
- Format specs
- Usage guidelines
- Presentation decks

---

## 9. THE AGENT'S DECISION TREE

When given a brief, the agent should automatically determine:

```
1. WHAT TYPE OF CAMPAIGN?
   → Product launch? Awareness? Lead gen? Seasonal?
   → This determines deliverable requirements

2. WHAT'S THE PRODUCT/FOCUS?
   → Do we need product imagery?
   → What features/benefits to highlight?
   → What's the unique angle?

3. WHO'S THE AUDIENCE?
   → Single persona or multiple?
   → What stage of awareness?
   → What channels do they use?

4. WHAT CHANNELS MAKE SENSE?
   → Based on audience + objective + budget
   → Each channel = specific deliverables

5. WHAT CREATIVE FORMATS NEEDED?
   → Per channel requirements
   → Variations for testing
   → Personalization needs

6. WHAT'S THE TIMELINE?
   → Teaser → Launch → Sustain → Retarget
   → Content calendar

7. HOW DO WE MEASURE SUCCESS?
   → KPIs aligned to objective
   → Attribution model
   → Reporting cadence
```

---

## 10. EXAMPLE: Nike Air Max DN Launch (What Should Happen)

### Brief
"Launch Air Max DN for Gen Z on social, focus on sustainability"

### Agent Understanding
- **Campaign Type**: Product launch
- **Product**: Air Max DN (needs imagery, specs, sustainability story)
- **Audience**: Gen Z sneakerheads who care about environment
- **Channels**: TikTok (primary), Instagram (secondary)
- **Timeline**: Teaser (2 weeks) → Launch (1 week) → Sustain (4 weeks)

### Automatic Deliverable List
**TikTok**:
- 3x teaser videos (product hints, sustainability story)
- 1x launch video (product reveal)
- 3x sustain videos (lifestyle, features, UGC-style)
- Creator brief for influencer content

**Instagram**:
- Teaser carousel (countdown, hints)
- Launch carousel (product details)
- Story sequence (swipe-up to shop)
- Reels (TikTok repurposed + native)
- Feed posts (lifestyle shots)

**Paid**:
- Meta ads (awareness + retargeting)
- TikTok ads (Spark ads from organic)
- Display retargeting

**Owned**:
- Product landing page
- Email announcement
- Email sequence (launch → reminder → review)

**All Creative**:
- Product integrated into every visual
- Nike aesthetic (high contrast, athletic, gritty)
- Sustainability messaging woven in (not preachy)
- Gen Z tone (authentic, not trying too hard)

---

## Summary

The agent needs to be a **T-shaped marketer**:
- Deep expertise across all these capabilities
- Understanding of how they connect
- Automatic decision-making based on brief
- Brand intelligence as foundation
- Product integration when needed
- Channel-specific execution
- Full-funnel thinking

Not: "Here's an image and a video"
But: "Here's a complete campaign system designed for your specific situation"
