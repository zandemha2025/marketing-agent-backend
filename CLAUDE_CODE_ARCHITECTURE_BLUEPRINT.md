# Claude Code Architecture Blueprint for Marketing Agent Platform

## Executive Summary

This document captures the architectural patterns from Claude Code (Anthropic's agentic coding assistant) and the Claude Agent SDK, and maps them directly to the Marketing Agent platform. Claude Code represents "as close to AGI as we could get" in terms of autonomous agent design - this blueprint ensures we're building on proven patterns rather than reinventing the wheel.

---

## Part 1: Claude Code's Core Design Philosophy

### The Genius of Simplicity

Claude Code's architecture is deceptively simple. While the AI industry is obsessed with complex multi-agent swarms, critic patterns, and sophisticated memory systems, Claude Code proves that **the simple thing works best**.

> "Notice how Claude Code does not use a critic pattern to review its own work, or assume different roles. It also does not have a sophisticated memory system. It does not use any databases to represent knowledge or do anything else fancy."

**Key Philosophy:**
- Flat message history (no complex threading)
- Regex over embeddings for search
- Markdown files over databases for memory
- Single main thread, not competing agent personas
- One sub-agent at a time (no uncontrolled proliferation)

### The Core Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE CLAUDE CODE AGENT LOOP                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   while (tool_call):                                             │
│       execute_tool()                                             │
│       feed_results_back()                                        │
│       repeat                                                     │
│                                                                  │
│   # Loop terminates when Claude produces text without tool calls │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**This is it.** No explicit stop command. No termination regex. When the agent is done, it outputs text explaining what it did and stops calling tools.

---

## Part 2: The Four-Phase Cycle

Every Claude Code action follows this cycle:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│                  │     │                  │     │                  │     │                  │
│  GATHER CONTEXT  │────▶│   TAKE ACTION    │────▶│   VERIFY WORK    │────▶│     REPEAT       │
│                  │     │                  │     │                  │     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ • Agentic search │     │ • Custom tools   │     │ • Rules-based    │
│ • File reading   │     │ • Bash commands  │     │   (linting)      │
│ • Semantic query │     │ • Code gen       │     │ • Visual (UI)    │
│ • Folder context │     │ • MCP calls      │     │ • LLM-as-judge   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

### Mapping to Marketing Agent

| Claude Code Phase | Marketing Agent Equivalent |
|-------------------|---------------------------|
| **Gather Context** | Read brand knowledge base, research market via Perplexity, analyze trends |
| **Take Action** | Generate content, create assets, write copy, build campaigns |
| **Verify Work** | Check brand voice alignment, verify format specs, validate quality |
| **Repeat** | Iterate based on feedback, refine outputs, continue workflow |

---

## Part 3: Tool Architecture

### Claude Code's Tool Philosophy

Tools are "prominent in Claude's context window" - they're the primary way Claude interacts with the world. Claude Code gives Claude access to a developer's **entire toolkit**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE TOOL CATEGORIES                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CORE TOOLS (Built-in)                                          │
│  ├── Read           - Read files                                │
│  ├── Write          - Create/overwrite files                    │
│  ├── Edit           - Modify existing files                     │
│  ├── Bash           - Execute shell commands                    │
│  ├── Glob           - Pattern-based file search                 │
│  ├── Grep           - Content search                            │
│  └── Task           - Spawn subagents                           │
│                                                                  │
│  MCP TOOLS (Plugin)                                             │
│  ├── GitHub         - Repo operations                           │
│  ├── Slack          - Messaging                                 │
│  ├── Google Drive   - File storage                              │
│  ├── Postgres       - Database                                  │
│  └── [Custom]       - Your own tools                            │
│                                                                  │
│  SUBAGENT TYPES                                                 │
│  ├── Explore        - Fast codebase exploration                 │
│  ├── Plan           - Architecture and design                   │
│  └── General        - Multi-purpose                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Marketing Agent Tool Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  MARKETING AGENT TOOL CATEGORIES                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CORE TOOLS (Built-in)                                          │
│  ├── ReadKnowledgeBase   - Access brand/org data                │
│  ├── CreateDeliverable   - Generate content assets              │
│  ├── EditDeliverable     - Modify existing content              │
│  ├── GenerateImage       - Create visual assets                 │
│  ├── ResearchMarket      - Perplexity/web research             │
│  └── SpawnAgent          - Delegate to specialist agents        │
│                                                                  │
│  MCP TOOLS (Integrations)                                       │
│  ├── SocialPublish       - Post to platforms                    │
│  ├── EmailSend           - Email campaigns                      │
│  ├── AnalyticsRead       - Performance data                     │
│  ├── StorageWrite        - Asset management                     │
│  └── CalendarSchedule    - Content scheduling                   │
│                                                                  │
│  SPECIALIST AGENTS (Subagents)                                  │
│  ├── Strategist          - Research and insights                │
│  ├── CreativeDirector    - Concepts and direction               │
│  ├── Copywriter          - Text content                         │
│  ├── ArtDirector         - Visual direction                     │
│  ├── Producer            - Asset production                     │
│  ├── MediaPlanner        - Distribution                         │
│  └── Analyst             - Measurement                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Tool Design Principles

From Claude Code best practices:

1. **Conscious Simplicity** - Design tools around primary actions, not exhaustive APIs
2. **Clear Naming** - Tool names should signal intent (e.g., `ResearchCompetitors`, not `query_data`)
3. **Rich Feedback** - Tools should return detailed, structured responses
4. **Error Handling** - Let the agent know when something fails so it can adapt

```python
# GOOD: Clear, focused tool
@tool
def generate_headline(
    product: str,
    audience: str,
    tone: str,
    count: int = 5
) -> HeadlineResult:
    """Generate headlines for a product targeting a specific audience."""
    # Implementation
    return HeadlineResult(
        headlines=headlines,
        rationale=why_these_work,
        variations_available=True
    )

# BAD: Generic, unclear tool
@tool
def create_content(data: dict) -> dict:
    """Create content."""
    # Too vague - what content? For whom? What format?
    pass
```

---

## Part 4: Context Management

### The Context Window is Sacred

Claude Code's approach to context management is critical for long-running tasks:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT HIERARCHY                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LAYER 1: System Prompt (Permanent)                              │
│  ├── Agent role and capabilities                                 │
│  ├── Tool descriptions                                           │
│  └── Safety rules                                                │
│                                                                  │
│  LAYER 2: CLAUDE.md (Persistent)                                 │
│  ├── Project-specific context                                    │
│  ├── Coding standards                                            │
│  └── Important instructions                                      │
│                                                                  │
│  LAYER 3: Conversation History (Compactable)                     │
│  ├── User messages                                               │
│  ├── Tool calls and results                                      │
│  └── Previous outputs                                            │
│                                                                  │
│  LAYER 4: Current Turn (Active)                                  │
│  ├── Current user request                                        │
│  └── Immediate context                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Compaction Strategy

When context fills up (95% capacity), Claude Code:

1. **First**: Clears older tool outputs (least valuable)
2. **Then**: Summarizes conversation history
3. **Preserves**: User requests, key decisions, current state

**Marketing Agent Equivalent:**

```python
# Context priority for Marketing Agent
CONTEXT_PRIORITY = {
    "system_prompt": "never_compact",      # Agent instructions
    "brand_knowledge": "never_compact",     # Core brand data
    "current_brief": "preserve",            # Active project brief
    "recent_approvals": "preserve",         # Client decisions
    "tool_outputs": "compact_first",        # Generated content
    "research_results": "compact_second",   # Market research
    "conversation": "summarize"             # Chat history
}
```

### Subagent Context Isolation

This is crucial: **Subagents have their own context windows**.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│   ORCHESTRATOR (Main Agent)                                       │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │ Context: Brand brief, workflow state, approvals         │    │
│   │ Tokens used: 50,000                                     │    │
│   └─────────────────────────────────────────────────────────┘    │
│         │                                                         │
│         │ Spawns subagent with focused task                       │
│         ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │ COPYWRITER SUBAGENT                                     │    │
│   │ Context: Brief excerpt, brand voice, format specs       │    │
│   │ Tokens used: 15,000 (separate window!)                  │    │
│   │                                                         │    │
│   │ Returns: 10 headlines + rationale (summarized)          │    │
│   └─────────────────────────────────────────────────────────┘    │
│         │                                                         │
│         │ Only summary returns to orchestrator                    │
│         ▼                                                         │
│   Orchestrator receives: "Generated 10 headlines. Top 3: ..."    │
│   (NOT the full 15,000 token subagent context)                   │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

This pattern lets you scale workload without blowing up context.

---

## Part 5: Multi-Agent Orchestration

### Anthropic's Orchestrator-Worker Pattern

From their multi-agent research system:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR-WORKER PATTERN                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                      ┌─────────────────┐                        │
│                      │   ORCHESTRATOR  │                        │
│                      │    (Lead Agent) │                        │
│                      └────────┬────────┘                        │
│                               │                                  │
│           ┌───────────────────┼───────────────────┐              │
│           │                   │                   │              │
│           ▼                   ▼                   ▼              │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│    │  SUBAGENT   │    │  SUBAGENT   │    │  SUBAGENT   │        │
│    │  (Worker)   │    │  (Worker)   │    │  (Worker)   │        │
│    │             │    │             │    │             │        │
│    │ Fresh       │    │ Fresh       │    │ Fresh       │        │
│    │ Context     │    │ Context     │    │ Context     │        │
│    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘        │
│           │                   │                   │              │
│           └───────────────────┼───────────────────┘              │
│                               │                                  │
│                      Returns: Summary only                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Rules:**
1. Lead agent analyzes, develops strategy, spawns subagents
2. Subagents work in parallel on different aspects
3. Each subagent has isolated context
4. Only relevant summaries return to orchestrator
5. Subagents cannot spawn other subagents

### Applied to Marketing Agent

```
┌─────────────────────────────────────────────────────────────────┐
│                    MARKETING AGENT ORCHESTRATION                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User: "Create a launch campaign for our new product"           │
│                               │                                  │
│                               ▼                                  │
│                      ┌─────────────────┐                        │
│                      │   ORCHESTRATOR  │                        │
│                      │ (Account Agent) │                        │
│                      │                 │                        │
│                      │ 1. Parse intent │                        │
│                      │ 2. Gather brief │                        │
│                      │ 3. Plan phases  │                        │
│                      │ 4. Spawn agents │                        │
│                      └────────┬────────┘                        │
│                               │                                  │
│    ┌──────────────────────────┼──────────────────────────┐      │
│    │                          │                          │      │
│    ▼                          ▼                          ▼      │
│ ┌──────────┐            ┌──────────┐            ┌──────────┐   │
│ │STRATEGIST│            │CREATIVE  │            │COPYWRITER│   │
│ │          │            │DIRECTOR  │            │          │   │
│ │Research  │            │          │            │Headlines │   │
│ │market &  │───────────▶│Develop 3 │───────────▶│Body copy │   │
│ │audience  │  provides  │concepts  │  provides  │Scripts   │   │
│ │          │  brief     │          │  direction │          │   │
│ └──────────┘            └──────────┘            └──────────┘   │
│                                                                  │
│                    [Human Checkpoint]                            │
│                    User approves concept                         │
│                               │                                  │
│    ┌──────────────────────────┼──────────────────────────┐      │
│    │                          │                          │      │
│    ▼                          ▼                          ▼      │
│ ┌──────────┐            ┌──────────┐            ┌──────────┐   │
│ │ART       │            │PRODUCER  │            │MEDIA     │   │
│ │DIRECTOR  │            │          │            │PLANNER   │   │
│ │          │            │          │            │          │   │
│ │Visuals & │───────────▶│Generate  │───────────▶│Schedule &│   │
│ │layouts   │  specs     │all assets│  assets    │distribute│   │
│ │          │            │          │            │          │   │
│ └──────────┘            └──────────┘            └──────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Delegation Framework

Each subagent receives:
- Clear objective (what to produce)
- Output format (structure of response)
- Task boundaries (what NOT to do)
- Heuristics (guidelines, not rigid rules)

```python
# Example subagent delegation
strategist_task = SubagentTask(
    agent_type="strategist",
    objective="Research the sustainable packaging market and identify key consumer insights",
    output_format={
        "market_overview": "3-5 bullet summary",
        "competitors": "Top 5 with positioning",
        "consumer_insights": "3 key truths",
        "opportunity": "Single sentence"
    },
    boundaries=[
        "Do not develop creative concepts",
        "Focus on B2C consumer packaged goods",
        "Prioritize environmental concern data"
    ],
    heuristics=[
        "Simple fact-finding: 1 agent, 3-10 searches",
        "Start broad, then narrow",
        "Prioritize recency for market data"
    ]
)
```

---

## Part 6: Workflow Phases with Human Checkpoints

### Claude Code's Lesson: Let Humans Review Outcomes, Not Every Action

Claude Code is classified as "Level 4 - Autonomous Agent":
- Executes multi-step plans with minimal supervision
- Iterates on failures
- Completes entire features
- **Humans review outcomes, not every action**

### Marketing Agent Workflow with Checkpoints

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMPAIGN WORKFLOW PHASES                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PHASE 1: INTAKE (Autonomous)                                    │
│  ────────────────────────────                                    │
│  • Orchestrator gathers requirements                             │
│  • Creates structured brief                                      │
│  • No human intervention needed                                  │
│                                                                  │
│  PHASE 2: DISCOVERY (Autonomous)                                 │
│  ──────────────────────────────                                  │
│  • Strategist researches market                                  │
│  • Analyzes competition                                          │
│  • Identifies insights                                           │
│  • No human intervention needed                                  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ CHECKPOINT 1: Strategy Review                              │  │
│  │ Human reviews: Research, insights, brief                   │  │
│  │ Decision: Approve / Request changes / Redirect             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  PHASE 3: CONCEPTING (Autonomous)                                │
│  ─────────────────────────────────                               │
│  • Creative Director develops 3 concepts                         │
│  • Each with headlines, visuals, rationale                       │
│  • No human intervention needed                                  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ CHECKPOINT 2: Concept Selection                            │  │
│  │ Human reviews: 3 creative directions                       │  │
│  │ Decision: Select direction / Merge ideas / New directions  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  PHASE 4: DEVELOPMENT (Autonomous)                               │
│  ──────────────────────────────────                              │
│  • Copywriter creates all copy                                   │
│  • Art Director creates visual specs                             │
│  • Full creative package generated                               │
│  • No human intervention needed                                  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ CHECKPOINT 3: Creative Approval                            │  │
│  │ Human reviews: Complete creative package                   │  │
│  │ Decision: Approve / Revise copy / Revise visuals          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  PHASE 5: PRODUCTION (Autonomous)                                │
│  ─────────────────────────────────                               │
│  • Producer generates all assets                                 │
│  • All formats, all platforms                                    │
│  • Quality checked automatically                                 │
│  • No human intervention needed                                  │
│                                                                  │
│  PHASE 6: DISTRIBUTION (Autonomous with Confirmation)            │
│  ──────────────────────────────────────────────────────          │
│  • Media Planner creates schedule                                │
│  • Posts scheduled but not published                             │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ CHECKPOINT 4: Launch Approval                              │  │
│  │ Human reviews: Publishing schedule                         │  │
│  │ Decision: Launch / Adjust timing / Hold                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  PHASE 7: MEASUREMENT (Autonomous)                               │
│  ──────────────────────────────────                              │
│  • Analyst tracks performance                                    │
│  • Generates reports                                             │
│  • Recommends optimizations                                      │
│  • Human notified on significant findings                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 7: Error Handling and Reliability

### Claude Code's Approach: Graceful Degradation

> "We use the model's intelligence to handle issues gracefully: letting the agent know when a tool is failing and letting it adapt works surprisingly well."

**Key Patterns:**

1. **Stateful Error Handling** - Resume from failure points, not full restarts
2. **Retry Logic** - Deterministic safeguards for transient failures
3. **Regular Checkpoints** - Save state frequently
4. **Rainbow Deployments** - Don't disrupt running agents during updates

### Marketing Agent Error Handling

```python
class AgentErrorHandler:
    """
    Error handling following Claude Code patterns.
    """

    async def handle_tool_failure(self, tool: str, error: Exception, context: dict):
        """
        When a tool fails, let the agent adapt.
        """
        # 1. Log the failure with context
        await self.log_error(tool, error, context)

        # 2. Return informative error to agent
        return ToolResult(
            success=False,
            error_message=f"The {tool} tool failed: {str(error)}",
            suggestion="You might try an alternative approach or retry with different parameters.",
            can_retry=self.is_transient_error(error),
            context_preserved=True  # Don't lose state
        )

    async def checkpoint_workflow(self, workflow_id: str, phase: str, state: dict):
        """
        Save state regularly so we can resume.
        """
        await self.db.save_checkpoint(
            workflow_id=workflow_id,
            phase=phase,
            state=state,
            timestamp=datetime.now()
        )

    async def resume_from_checkpoint(self, workflow_id: str):
        """
        Resume work from last successful checkpoint.
        """
        checkpoint = await self.db.get_latest_checkpoint(workflow_id)
        if checkpoint:
            return await self.orchestrator.resume(
                workflow_id=workflow_id,
                phase=checkpoint.phase,
                state=checkpoint.state
            )
```

---

## Part 8: MCP Integration Strategy

### Model Context Protocol (MCP) Overview

MCP is the "USB-C of AI" - a standardized way to connect Claude to external tools.

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   AGENT                                                          │
│     │                                                            │
│     │ Uses standardized MCP protocol                             │
│     ▼                                                            │
│   ┌───────────────────────────────────────────────────────┐     │
│   │                    MCP LAYER                           │     │
│   │  Handles: Authentication, API calls, Rate limiting     │     │
│   └───────────────────────────────────────────────────────┘     │
│     │                                                            │
│     │ Connects to multiple services                              │
│     ▼                                                            │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│   │ GitHub  │ │ Slack   │ │ Google  │ │Postgres │ │ Custom  │  │
│   │ Server  │ │ Server  │ │ Drive   │ │ Server  │ │ Server  │  │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Marketing Agent MCP Strategy

```python
# MCP Server Configuration for Marketing Agent
mcp_config = {
    "servers": {
        # Research Tools
        "perplexity": {
            "type": "http",
            "url": "https://api.perplexity.ai/v1",
            "auth": {"type": "bearer", "env": "PERPLEXITY_API_KEY"}
        },
        "firecrawl": {
            "type": "http",
            "url": "https://api.firecrawl.dev/v1",
            "auth": {"type": "bearer", "env": "FIRECRAWL_API_KEY"}
        },

        # Content Generation
        "openrouter": {
            "type": "http",
            "url": "https://openrouter.ai/api/v1",
            "auth": {"type": "bearer", "env": "OPENROUTER_API_KEY"}
        },
        "replicate": {
            "type": "http",
            "url": "https://api.replicate.com/v1",
            "auth": {"type": "bearer", "env": "REPLICATE_API_KEY"}
        },

        # Distribution
        "social_publish": {
            "type": "stdio",
            "command": "npx",
            "args": ["@marketing-agent/social-mcp-server"]
        },

        # Analytics
        "analytics": {
            "type": "http",
            "url": "${ANALYTICS_API_URL}",
            "auth": {"type": "oauth", "env": "ANALYTICS_OAUTH_TOKEN"}
        }
    }
}
```

### Tool Search for Large Tool Sets

When you have many MCP tools, they can consume too much context. Claude Code's solution:

```python
# Enable tool search when tool descriptions > 10% of context
tool_search_config = {
    "enabled": True,
    "mode": "auto",  # Activates when tools exceed threshold
    "threshold_percent": 10,
    "max_tools_loaded": 15  # Only load relevant tools per turn
}
```

---

## Part 9: Implementation Roadmap

### Phase 1: Core Agent Loop (Week 1-2)

```python
# Implement the basic agent loop
class MarketingAgentLoop:
    async def run(self, user_request: str):
        # 1. Initialize context
        context = await self.gather_context(user_request)

        # 2. Main loop
        while True:
            # Get model response
            response = await self.llm.complete(
                system_prompt=self.system_prompt,
                messages=context.messages,
                tools=self.get_available_tools()
            )

            # Check for tool calls
            if response.has_tool_calls():
                # Execute tools
                for tool_call in response.tool_calls:
                    result = await self.execute_tool(tool_call)
                    context.add_tool_result(result)
            else:
                # No tool calls = agent is done
                return response.text
```

### Phase 2: Specialist Agents (Week 3-4)

Implement each specialist as a subagent:

```python
SPECIALIST_AGENTS = {
    "strategist": StrategistAgent(
        system_prompt=STRATEGIST_PROMPT,
        tools=["research_market", "analyze_competitors", "generate_insights"]
    ),
    "creative_director": CreativeDirectorAgent(
        system_prompt=CREATIVE_DIRECTOR_PROMPT,
        tools=["generate_concepts", "create_moodboard", "evaluate_creative"]
    ),
    "copywriter": CopywriterAgent(
        system_prompt=COPYWRITER_PROMPT,
        tools=["generate_headlines", "write_copy", "adapt_tone"]
    ),
    # ... etc
}
```

### Phase 3: Workflow Orchestration (Week 5-6)

```python
class WorkflowOrchestrator:
    async def execute_campaign_workflow(self, brief: CampaignBrief):
        # Phase 1: Discovery
        research = await self.spawn_agent("strategist", {
            "task": "research_market",
            "brief": brief
        })

        # Checkpoint 1
        await self.request_approval("strategy", research)

        # Phase 2: Concepting
        concepts = await self.spawn_agent("creative_director", {
            "task": "develop_concepts",
            "brief": brief,
            "research": research.summary
        })

        # Checkpoint 2
        selected = await self.request_approval("concept", concepts)

        # ... continue workflow
```

### Phase 4: Context Management (Week 7-8)

```python
class ContextManager:
    def __init__(self, max_tokens: int = 200000):
        self.max_tokens = max_tokens
        self.compact_threshold = 0.95

    async def manage(self, context: AgentContext):
        usage = self.calculate_usage(context)

        if usage > self.compact_threshold:
            # Step 1: Clear old tool outputs
            context.clear_old_tool_outputs(keep_last=5)

            # Step 2: Summarize if still too large
            if self.calculate_usage(context) > self.compact_threshold:
                summary = await self.generate_summary(context)
                context.replace_with_summary(summary)
```

### Phase 5: MCP Integration (Week 9-10)

Connect external services through MCP:
- Perplexity for research
- Replicate for image generation
- Social platform APIs
- Analytics services

### Phase 6: Production Hardening (Week 11-12)

- Error handling and retry logic
- Checkpointing and recovery
- Monitoring and observability
- Rate limiting and cost control

---

## Part 10: Key Takeaways

### What We Learn from Claude Code

1. **Simplicity wins.** A single agent loop with tool access outperforms complex multi-agent swarms.

2. **Context is everything.** Manage it carefully with compaction and subagent isolation.

3. **Tools are the interface.** Design clear, focused tools that give rich feedback.

4. **Let it iterate.** The loop continues until the agent decides it's done.

5. **Human checkpoints, not supervision.** Review outcomes at key phases, not every action.

6. **Graceful degradation.** Let the agent know when things fail so it can adapt.

7. **Subagents for parallelism and context.** Use them to scale work without blowing up context.

8. **MCP for extensibility.** Standardized integrations reduce custom code.

### The Marketing Agent Advantage

By applying these patterns, the Marketing Agent becomes:

- **Truly autonomous** - Completes entire campaigns with minimal intervention
- **Scalable** - Subagents handle parallel work without context explosion
- **Reliable** - Checkpoints and error handling ensure work isn't lost
- **Extensible** - MCP makes adding new tools trivial
- **Quality-focused** - Specialist agents with clear roles produce better output

---

## Sources

- [Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Claude Code overview - Claude Code Docs](https://code.claude.com/docs/en/overview)
- [Claude Code Internals: The Agent Loop](https://kotrotsos.medium.com/claude-code-internals-part-2-the-agent-loop-5b3977640894)
- [Agent design lessons from Claude Code](https://jannesklaas.github.io/ai/2025/07/20/claude-code-agent-design.html)
- [Claude Code: Behind-the-scenes of the master agent loop](https://blog.promptlayer.com/claude-code-behind-the-scenes-of-the-master-agent-loop/)
- [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Claude Agent SDK - Anthropic Docs](https://platform.claude.com/docs/en/agent-sdk/overview)
