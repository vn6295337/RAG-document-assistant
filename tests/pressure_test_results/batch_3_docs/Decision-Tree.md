## 1st variant (ChatGPT)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      AI DECISION FRAMEWORK (AT A GLANCE)                     │
└──────────────────────────────────────────────────────────────────────────────┘

START
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: AGENT vs NON-AGENT                                                   │
└──────────────────────────────────────────────────────────────────────────────┘
  │
  ├─ Are tasks structured, predictable, single-step, or rule-based?
  │     ├─ YES → NON-AGENT (Code, rules engine, RPA, classic ML, simple RAG)
  │     └─ NO ↓
  │
  ├─ Is the goal only content generation, summarization, or Q&A from static data?
  │     ├─ YES → NON-AGENT (Single LLM call or standard RAG)
  │     └─ NO ↓
  │
  └─ Does the task require several of the following?
        • Multi-step reasoning with changing paths
        • Dynamic decision-making under ambiguity
        • Tool or API selection at runtime
        • Handling exceptions and retries
        • Long-running or stateful execution
        • Context from multiple systems
            │
            ├─ NO → NON-AGENT (Workflow or Orchestration)
            └─ YES ↓
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: AGENT READINESS CHECK (STOP IF ANY FAIL)                             │
└──────────────────────────────────────────────────────────────────────────────┘
  │
  ├─ Is occasional non-determinism acceptable?
  ├─ Can cost and latency tolerate multiple model or tool calls?
  └─ Are guardrails, human override, and audit logs feasible?
        │
        ├─ NO to any → REVERT TO NON-AGENT
        └─ YES to all ↓
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: SINGLE AGENT vs MULTI-AGENT                                          │
└──────────────────────────────────────────────────────────────────────────────┘
  │
  └─ Can one agent reasonably:
        • Own the full task?
        • Use a limited, manageable set of tools?
        • Stay accurate and reliable?
            │
            ├─ YES → SINGLE AGENT
            │
            └─ NO → Are these true?
                    • Distinct skills or roles needed?
                    • Parallel work improves speed or quality?
                    • Clear handoffs or supervision required?
                        │
                        ├─ YES → MULTI-AGENT (Supervisor, Router, Specialists)
                        └─ NO  → SIMPLIFY (Non-agent or Hybrid)
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: BUILD vs BUY vs INTEGRATE                                            │
└──────────────────────────────────────────────────────────────────────────────┘
  │
  ├─ Is the use case common and well-served by existing products?
  │  (e.g., IT helpdesk, CRM updates, code assist, productivity agents)
  │     │
  │     └─ YES ↓
  │            ▼
  │     ┌─────────────────────────────────────────┐
  │     │ BUY (SaaS Agent)                        │
  │     ├─────────────────────────────────────────┤
  │     │ • Fast time-to-value                    │
  │     │ • Standard workflows                    │
  │     │ • Lower customization need              │
  │     └─────────────────────────────────────────┘
  │
  ├─ Do you have systems with APIs/events the agent must work within?
  │     │
  │     └─ YES ↓
  │            ▼
  │     ┌─────────────────────────────────────────┐
  │     │ INTEGRATE (Agent + Existing Workflows)  │
  │     ├─────────────────────────────────────────┤
  │     │ • Agent handles reasoning               │
  │     │ • Deterministic systems execute actions │
  │     │ • Strong governance and control         │
  │     └─────────────────────────────────────────┘
  │
  └─ Is this true?
        • Core to competitive advantage
        • Unique data or logic
        • Deep customization required
        • Long-term evolution expected
            │
            ├─ YES ↓
            │      ▼
            │ ┌─────────────────────────────────────────┐
            │ │ BUILD (Custom Agent)                    │
            │ ├─────────────────────────────────────────┤
            │ │ • Start with a single agent             │
            │ │ • Add tools, memory, evaluations        │
            │ │ • Evolve to multi-agent if needed       │
            │ └─────────────────────────────────────────┘
            │
            └─ NO → BUY or INTEGRATE (Reassess Scope)
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: FINAL PROCEED CHECK                                                  │
└──────────────────────────────────────────────────────────────────────────────┘
  │
  ├─ Clear business owner and success metrics?
  ├─ Pilot proves agent outperforms simpler alternatives?
  └─ Ongoing monitoring, cost controls, and kill-switch exist?
        │
        ├─ NO  → DO NOT SCALE
        └─ YES → PROCEED
```

---

## 2nd Variant (Gemini)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│              UNIFIED ENTERPRISE AI-AGENT DECISION FRAMEWORK                  │
└──────────────────────────────────────────────────────────────────────────────┘

START
  │
  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: THE AGENTIC GATE                                                    │
│                                                                              │
│ Does the task require dynamic reasoning, tool-switching,                     │
│ or multi-step judgment?                                                      │
└──────────────────────────────────────────────────────────────────────────────┘
  │
  ├─ NO (Predictable/Linear)          YES (Dynamic/Reasoning) ─┐
  │                                                             │
  ▼                                                             ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│    NON-AGENTIC WORKFLOW     │         │     AI-AGENTIC SYSTEM       │
├─────────────────────────────┤         ├─────────────────────────────┤
│ • Standard RAG              │         │ • Dynamic Tool Use          │
│ • Fixed API Pipelines       │         │ • Self-Correction Loops     │
│ • Deterministic Logic       │         │ • Multi-Step Planning       │
└─────────────────────────────┘         └─────────────────────────────┘
                                                      │
                                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: IMPLEMENTATION STRATEGY                                             │
└──────────────────────────────────────────────────────────────────────────────┘
  │
  ├──────────────────────┬──────────────────────┐
  │                      │                      │
  ▼                      ▼                      ▼
┌────────────┐    ┌────────────┐    ┌────────────┐
│ BUSINESS   │    │ SPEED TO   │    │ TECH       │
│ VALUE      │    │ MARKET     │    │ STACK      │
├────────────┤    ├────────────┤    ├────────────┤
│ Core/IP    │    │ Immediate  │    │ 3rd Party  │
│ Heavy      │    │ Need       │    │ Platform   │
└────────────┘    └────────────┘    └────────────┘
  │                      │                      │
  ▼                      ▼                      ▼
┌────────────┐    ┌────────────┐    ┌────────────┐
│   BUILD    │    │    BUY     │    │ INTEGRATE  │
├────────────┤    ├────────────┤    ├────────────┤
│ • Custom   │    │ • Out-of-  │    │ • Low-code │
│   Orchest. │    │   box      │    │   Hub      │
│ • Max      │    │ • Managed  │    │ • App      │
│   Control  │    │   Security │    │   Plugins  │
│ • Propriet.│    │ • Fast ROI │    │ • Ecosystem│
├────────────┤    ├────────────┤    ├────────────┤
│ AWS/Azure  │    │ ChatGPT    │    │ Studio     │
│ Foundry    │    │ Copilot    │    │ GPTs       │
└────────────┘    └────────────┘    └────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: ORCHESTRATION DEPTH                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
  │
  ├─ COMPLEXITY: Narrow/Single Domain     ACCURACY: Broad/Multi-Step ─┐
  │                                                                    │
  ▼                                                                    ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│    SINGLE-AGENT FLOW        │         │    MULTI-AGENT SYSTEM       │
├─────────────────────────────┤         ├─────────────────────────────┤
│ • Reasoning Loop            │         │ • Specialized Roles         │
│ • Sequential Tools          │         │ • Review/Critique Path      │
│ • Lower Latency             │         │ • Parallel Tasks            │
├─────────────────────────────┤         ├─────────────────────────────┤
│ (Simple Task Assistant)     │         │ (Complex R&D / SW Eng)      │
└─────────────────────────────┘         └─────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                          DECISION CRITERIA LOG                               │
├───────────────────┬─────────────────────────┬────────────────────────────────┤
│ CRITERIA          │ AGENTIC THRESHOLD       │ NON-AGENTIC THRESHOLD          │
├───────────────────┼─────────────────────────┼────────────────────────────────┤
│ Logic Type        │ Reasoning-based         │ Rules-based / Deterministic    │
│ Outcome Variab.   │ High (Unstructured)     │ Low (Structured / Template)    │
│ Error Tolerance   │ Moderate (Iterative)    │ Zero (Mission Critical)        │
│ Tool Access       │ Dynamic / Ad-hoc        │ Fixed / Pre-defined            │
│ Strategic Weight  │ Competitive Advantage   │ Commodity / Utility            │
├───────────────────┴─────────────────────────┴────────────────────────────────┤
│ SOURCES: Anthropic [1], OpenAI [2], Google [3], AWS [4], Microsoft [5]       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3rd Variant (Claude)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED AI AGENT DECISION FRAMEWORK                       │
└──────────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STAGE 1: DO YOU NEED AN AI AGENT?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                              START WITH YOUR TASK
                                      │
                                      ▼
                 ┌────────────────────────────────────────┐
                 │  Can task be completed with a single   │
                 │  LLM call + retrieval/examples?        │
                 └────────────────────────────────────────┘
                          │                    │
                         YES                   NO
                          │                    │
                          ▼                    ▼
              ┌──────────────────┐    ┌───────────────────────────────┐
              │  USE NON-AGENT   │    │  Is the task structured,      │
              │  • Single LLM    │    │  predictable, rule-based?     │
              │  • RAG system    │    └───────────────────────────────┘
              │  • Chatbot       │             │              │
              │  • Classifier    │            YES             NO
              │                  │             │              │
              │  ► STOP HERE     │             ▼              ▼
              └──────────────────┘    ┌──────────────┐  ┌─────────────────────┐
                                      │USE CODE OR   │  │Is it static         │
                                      │NONGENERATIVE │  │knowledge retrieval  │
                                      │AI MODELS     │  │only (no tool use)?  │
                                      │• Deterministic│ └─────────────────────┘
                                      │  automation  │        │          │
                                      │• Predictive  │       YES         NO
                                      │  ML models   │        │          │
                                      │► STOP HERE   │        ▼          ▼
                                      └──────────────┘  ┌──────────┐ ┌──────────┐
                                                        │USE RAG   │ │PROCEED   │
                                                        │APP       │ │TO AGENT  │
                                                        │► STOP    │ │DESIGN    │
                                                        └──────────┘ └──────────┘

    ╔═══════════════════════════════════════════════════════════════════════╗
    ║  AGENT TRIGGERS - Task requires ANY of:                               ║
    ║  • Complex/nuanced judgment       • Multi-step tool use               ║
    ║  • Difficult-to-maintain rules    • Dynamic decision-making           ║
    ║  • Unstructured data input        • Open-ended problem scope          ║
    ║  • Real-time external data        • Adaptive behavior needed          ║
    ╚═══════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STAGE 2: WHAT TYPE OF AGENT DO YOU NEED?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    AGENT AUTONOMY SPECTRUM
    SIMPLE ◄──────────────────────────────────────────────────────► ADVANCED

    ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────────┐
    │  PRODUCTIVITY   │   │     ACTION      │   │      AUTOMATION         │
    │     AGENT       │   │     AGENT       │   │        AGENT            │
    ├─────────────────┤   ├─────────────────┤   ├─────────────────────────┤
    │ Info retrieval  │   │ Performs tasks  │   │ Complex multi-step      │
    │ and synthesis   │   │ within defined  │   │ processes with minimal  │
    │                 │   │ workflows       │   │ oversight               │
    ├─────────────────┤   ├─────────────────┤   ├─────────────────────────┤
    │ Uses:           │   │ Uses:           │   │ Uses:                   │
    │ • Knowledge     │   │ • Knowledge     │   │ • Knowledge tools       │
    │   tools only    │   │   tools         │   │ • Action tools          │
    │                 │   │ • Action tools  │   │ • Triggers              │
    ├─────────────────┤   ├─────────────────┤   ├─────────────────────────┤
    │ Examples:       │   │ Examples:       │   │ Examples:               │
    │ • FAQ bots      │   │ • Ticket        │   │ • Supply chain          │
    │ • Knowledge     │   │   creation      │   │   optimization          │
    │   assistants    │   │ • Record        │   │ • Autonomous            │
    │ • Research      │   │   updates       │   │   monitoring            │
    │   synthesis     │   │ • Process       │   │ • End-to-end            │
    │                 │   │   triggers      │   │   workflow mgmt         │
    └─────────────────┘   └─────────────────┘   └─────────────────────────┘
                                  │
                                  ▼
                    ╔════════════════════════════╗
                    ║  DEFAULT: START WITH       ║
                    ║  SINGLE AGENT              ║
                    ║  Add complexity only       ║
                    ║  when needed               ║
                    ╚════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STAGE 3: SINGLE OR MULTI-AGENT SYSTEM?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                 ┌────────────────────────────────────────┐
                 │  Does your use case require ANY of:    │
                 │  • Crossing security/compliance        │
                 │    boundaries                          │
                 │  • Multiple teams with separate        │
                 │    knowledge domains                   │
                 │  • Future growth/scaling planned       │
                 └────────────────────────────────────────┘
                          │                    │
                         YES                   NO
                          │                    │
                          ▼                    ▼
           ┌─────────────────────────┐   ┌─────────────────────────┐
           │   BUILD MULTI-AGENT     │   │   TEST SINGLE AGENT     │
           │   SYSTEM                │   │   FIRST                 │
           │                         │   │                         │
           │   Patterns:             │   │   When:                 │
           │   • Sequential          │   │   • Clear roles exist   │
           │   • Parallel            │   │   • Fast time-to-market │
           │   • Coordinator         │   │   • Low-cost priority   │
           │   • Hierarchical        │   │   • High data volume    │
           │   • Review & Critique   │   │   • Multiple modalities │
           └─────────────────────────┘   └─────────────────────────┘
                                                   │
                                                   ▼
                                    ┌─────────────────────────────┐
                                    │  Did single-agent test FAIL │
                                    │  to meet requirements?      │
                                    └─────────────────────────────┘
                                          │              │
                                         YES             NO
                                          │              │
                                          ▼              ▼
                               ┌──────────────┐  ┌───────────────────┐
                               │ → MULTI-AGENT│  │ BUILD SINGLE-     │
                               │   (above)    │  │ AGENT SYSTEM      │
                               └──────────────┘  └───────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STAGE 4: BUILD vs BUY vs INTEGRATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                         EVALUATE THESE FACTORS
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
  ┌───────────┐            ┌───────────┐            ┌───────────┐
  │CAPABILITY │            │ RESOURCES │            │  CONTROL  │
  │ FIT       │            │           │            │  NEEDS    │
  └───────────┘            └───────────┘            └───────────┘
        │                         │                         │
  SaaS meets needs?        Engineering team?        Data sovereignty?
  Standard use case?       Time to market?          Custom guardrails?
                           Maintenance capacity?    Proprietary logic?
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              │                                       │
             YES                                      NO
              │                                       │
              ▼                                       ▼
┌───────────────────────────┐           ┌───────────────────────────┐
│         BUY (SaaS)        │           │  Does low-code suffice?   │
├───────────────────────────┤           └───────────────────────────┘
│ • Standard use cases      │                    │            │
│ • Fast deployment         │                   YES           NO
│ • Limited engineering     │                    │            │
│ • Proven patterns work    │                    ▼            ▼
│                           │           ┌─────────────┐ ┌─────────────┐
│ Examples:                 │           │ BUILD       │ │ BUILD       │
│ • M365 Copilot agents     │           │ (Low-Code)  │ │ (Pro-Code)  │
│ • Dynamics 365 agents     │           ├─────────────┤ ├─────────────┤
│ • GitHub Copilot          │           │• Rapid proto│ │• Unique     │
│ • Security Copilot        │           │• Business   │ │  workflows  │
└───────────────────────────┘           │  user builds│ │• Proprietary│
                                        │• Moderate   │ │  data/logic │
                                        │  custom     │ │• Full       │
                                        ├─────────────┤ │  control    │
                                        │Copilot      │ ├─────────────┤
                                        │Studio       │ │MS Foundry   │
                                        └─────────────┘ │Custom       │
                                                        │frameworks   │
                                                        └─────────────┘

    ┌─────────────────────────────────────────────────────────────────────┐
    │                      INTEGRATE (Hybrid/API)                         │
    ├─────────────────────────────────────────────────────────────────────┤
    │ When: Extend existing systems, combine vendor + custom logic        │
    │ Consider: SDK ecosystems, MCP/A2A protocols, tool libraries         │
    └─────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MULTI-AGENT PATTERN SELECTION GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    DETERMINISTIC (Predictable, fixed steps)
    ├─► Steps must run in order ──────────► SEQUENTIAL
    │   (pipeline processing)               Agent A → Agent B → Agent C
    │
    └─► Steps can run concurrently ───────► PARALLEL
        (gather diverse outputs)            Fan-out → Aggregate

    DYNAMIC ORCHESTRATION (Adaptive routing needed)
    ├─► Route to specialists ─────────────► COORDINATOR (Manager)
    │   (structured task dispatch)          Central agent delegates
    │
    ├─► Deep task breakdown ──────────────► HIERARCHICAL DECOMPOSITION
    │   (ambiguous, multi-level)            Parent → Children → Workers
    │
    └─► Peer collaboration ───────────────► DECENTRALIZED (Handoff/Swarm)
        (debate, consensus needed)          Agents hand off to each other

    ITERATIVE REFINEMENT (Progressive improvement)
    ├─► Generate then validate ───────────► REVIEW & CRITIQUE
    │   (quality gates needed)              Generator ↔ Critic loop
    │
    └─► Multiple revision cycles ─────────► EVALUATOR-OPTIMIZER
        (polish until threshold)            Refine → Evaluate → Repeat

    SPECIAL REQUIREMENTS
    ├─► High-stakes decisions ────────────► HUMAN-IN-THE-LOOP
    │   (approval, compliance)              Pause → Human review → Resume
    │
    └─► Unique business logic ────────────► CUSTOM ORCHESTRATION
        (no standard pattern fits)          Code-driven control flow

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ESSENTIAL GUARDRAILS CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ┌────────────────────┬────────────────────┬────────────────────┐
    │   INPUT CONTROLS   │  EXECUTION LIMITS  │  OUTPUT CONTROLS   │
    ├────────────────────┼────────────────────┼────────────────────┤
    │ • Relevance filter │ • Max iterations   │ • Content safety   │
    │ • Safety classifier│ • Tool risk rating │ • PII detection    │
    │ • Jailbreak detect │ • Timeout limits   │ • Brand alignment  │
    │ • Input validation │ • Cost thresholds  │ • Hallucination    │
    │ • Moderation API   │ • Sandboxed exec   │   check            │
    │                    │ • Least privilege  │ • Citation rules   │
    └────────────────────┴────────────────────┴────────────────────┘

    Human Escalation Triggers:
    • Failure threshold exceeded (repeated errors)
    • High-risk/irreversible actions (payments, deletions)
    • Confidence below threshold
    • Explicit user request

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 USE CASE PRIORITIZATION FRAMEWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Score each candidate use case (1-5):

    ┌────────────────────────────────────────────────────────────────────────┐
    │                        BUSINESS IMPACT                                 │
    ├────────────────────────────────────────────────────────────────────────┤
    │ • Executive strategy alignment: Does it support org priorities?        │
    │ • Business value: Quantifiable impact (cost, revenue, satisfaction)?   │
    │ • Change management: Short rollout, low user disruption?               │
    └────────────────────────────────────────────────────────────────────────┘
    ┌────────────────────────────────────────────────────────────────────────┐
    │                      TECHNICAL FEASIBILITY                             │
    ├────────────────────────────────────────────────────────────────────────┤
    │ • Implementation risks: Known, with mitigation plans?                  │
    │ • Sufficient safeguards: Security, RAI, compliance in place?           │
    │ • Technology fit: Clear benefit, integrates with current systems?      │
    └────────────────────────────────────────────────────────────────────────┘
    ┌────────────────────────────────────────────────────────────────────────┐
    │                       USER DESIRABILITY                                │
    ├────────────────────────────────────────────────────────────────────────┤
    │ • Key personas: Stakeholders and users clearly defined?                │
    │ • Value proposition: High appeal and adoption potential?               │
    │ • Change resistance: Low resistance, readiness for adoption?           │
    └────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 KEY PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ╔═════════════════════════════════════════════════════════════════════╗
    ║  SIMPLICITY FIRST      Find simplest solution; add complexity only  ║
    ║                        when demonstrably needed                     ║
    ╠═════════════════════════════════════════════════════════════════════╣
    ║  INCREMENTAL BUILD     Start single agent → refine → split only     ║
    ║                        when performance degrades                    ║
    ╠═════════════════════════════════════════════════════════════════════╣
    ║  EVALUATE EARLY        Set up evals to establish baseline before    ║
    ║                        optimizing for cost/latency                  ║
    ╠═════════════════════════════════════════════════════════════════════╣
    ║  TOOL QUALITY          Invest in tool documentation as much as      ║
    ║                        prompts; clear names, parameters, edge cases ║
    ╠═════════════════════════════════════════════════════════════════════╣
    ║  TRANSPARENCY          Show agent planning steps; enable debugging; ║
    ║                        maintain audit trails                        ║
    ╠═════════════════════════════════════════════════════════════════════╣
    ║  GROUND TRUTH          Agents must verify progress via tool results ║
    ║                        or environment feedback at each step         ║
    ╠═════════════════════════════════════════════════════════════════════╣
    ║  VALIDATE VALUE        Test reasoning in low-code environment       ║
    ║                        before investing in custom code              ║
    ╚═════════════════════════════════════════════════════════════════════╝
```




#consolidated

```
INPUT / CONTEXT
     │
     ▼
[Q1] Are tasks structured, predictable, single-step, or rule-based?
     ├─ YES → NON-AGENT (code, rules engine, RPA, classic ML, simple RAG). END
     └─ NO
         │
         ▼
[Q2] Is the goal limited to content generation, summarization, or Q&A over static data?
     ├─ YES → NON-AGENT (single LLM call or standard RAG). END
     └─ NO
         │
         ▼
[Q3] Are governance constraints (guardrails, human oversight, cost/latency,
     audit logging) satisfied for autonomous execution?
     ├─ YES → Proceed to AGENT decision path
     └─ NO  → WORKFLOW or NON-AGENT; add governance before agentizing. END
         │
         ▼
[Q4] Can one agent reasonably own the full task (manageable tools, clear boundaries)?
     ├─ YES → SINGLE AGENT -------------------------------┐
     │                                                    │
     └─ NO  → MULTI-AGENT --------------------------------┘
                │
                ▼
   ┌─────────────────────────────────────────────────────────────────────────┐
   │                        SINGLE AGENT PATH                                │
   └─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
[Q5] Deployment strategy: Is there an existing SaaS agent that meets reqs?
     ├─ YES → BUY (SaaS agent). IMPLEMENT + INTEGRATE WITH APIs. GO TO RUN LOOP
     └─ NO
         │
         ▼
[Q6] Must agent integrate closely with internal APIs/events or pre-existing systems?
     ├─ YES → INTEGRATE (Agent + orchestrator around existing systems). GO TO RUN LOOP
     └─ NO
         │
         ▼
[Q7] Is capability core to competitive advantage or needs deep customization?
     ├─ YES → BUILD (custom agent). GO TO RUN LOOP
     └─ NO  → BUY or INTEGRATE (reassess). GO TO RUN LOOP

     ┌─────────────────────────────────────────────────────────────────────────┐
     │                              RUN LOOP                                   │
     └─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
[Q8] Problem decomposition / planner: Does the task need
     - external retrieval?    → add RAG
     - tool/action invocation?→ add TOOL-BASED
     - long-term state?       → add MEMORY
     - multi-step conditional planning? → add PLANNER/ORCHESTRATOR
     - parallel subtasks?     → enable PARALLELIZATION
         │
         ▼
[ACTION] Build plan: select model(s), tool registry, memory store, orchestration pattern,
         success metrics and human-in-the-loop gates.
         │
         ▼
[STEP] Execute Plan:
   1) Preprocess input, assemble prompt/context (including retrieved docs & tool schemas)
   2) Call model(s) / invoke tools as planned
   3) Collect outputs and tool responses
         │
         ▼
[EVAL] Does output meet success criteria / validation checks / safety gates?
     ├─ YES →
     │     ├─ If action required: Execute action via tool(s) → RETURN result
     │     ├─ Log, audit, persist state to MEMORY as configured
     │     └─ Emit monitoring metrics; END
     └─ NO →
         │
         ▼
[Q9] Can the agent reflect/auto-correct (evaluator + reflection)?
     ├─ YES → REFLECT & REFINE: run evaluator (scoring/consistency), update plan or prompt,
     │         optionally select alternate model or tool, then RETRY → back to Execute Plan
     └─ NO  →
         │
         ▼
[Q10] Should this escalate to human review or safe-fail?
     ├─ YES → Escalate to HUMAN-IN-THE-LOOP / manual approval; log and END (or loop post-review)
     └─ NO  → Safe-fail: return partial result + explain limitations; log and END

     ┌─────────────────────────────────────────────────────────────────────────┐
     │                           MULTI-AGENT PATH                              │
     └─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
[Q11] Choose multi-agent pattern:
      - SEQUENTIAL (predefined chain)    → use workflow orchestrator
      - PARALLEL (scatter-gather)        → run specialists concurrently + AGGREGATOR
      - ROUTER/SUPERVISOR (classify & dispatch) → use router + specialists + supervisor
      - HIERARCHICAL (manager / specialists)    → supervisor oversees subagents
         │
         ▼
[STEP] Orchestrator: dispatch to specialist agents with scoped contexts & tools;
        collect outputs → AGGREGATOR/EVALUATOR synthesizes result
         │
         ▼
[EVAL-MA] Aggregated result passes validation?
     ├─ YES → Commit actions (as above), update shared MEMORY, log, END
     └─ NO →
         │
         ▼
[Q12] Can reassign / re-run subagents or adjust orchestration rules?
     ├─ YES → adjust dispatch / retry specific subagents → back to Orchestrator
     └─ NO  → Escalate to supervisor/human; safe-fail; log and END
