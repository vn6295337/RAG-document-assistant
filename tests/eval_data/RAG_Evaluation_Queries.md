# RAG Evaluation Query Set

Queries designed to test RAG system performance across different query types and edge cases.

## Query Set 1: Core Query Types

| Query Type              | Query Text                                                                                                             | Source Document                                                     |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Factual lookup          | What are the two key variations of the parallelization workflow pattern according to Anthropic?                        | Anthropic_AI_Agents.pdf                                             |
| Cross-document          | How do Anthropic, OpenAI, and Google each define the distinction between workflows and agents?                         | Anthropic_AI_Agents.pdf, OpenAI_AI_Agents.pdf, Google_AI_Agents.pdf |
| Synthesis               | What workforce archetypes are predicted to emerge in the agent-orchestrated enterprise, and how do their roles differ? | Consolidated.md                                                     |
| No-answer (adversarial) | What is the maximum token limit for GPT-4 when used in agentic workflows?                                              | N/A - not in docs                                                   |
| Vague / broad           | Explain transformers                                                                                                   | a_ai_ml_learning.md                                                 |
| Specific detail         | In the Agentic AI Stack, what is the embedding dimensionality for sentence-transformers versus Nomic Embed?            | Agentic_AI_Stack.md                                                 |
| Comparison              | How does the sequential multi-agent pattern differ from the parallel multi-agent pattern in terms of orchestration?    | Google_AI_Agents.pdf                                                |
| Process / how-to        | What are the five stages in the Claude decision framework for determining whether to build an agentic system?          | Decision-Tree.md                                                    |
| Inference               | Based on the AI Radar 2026 predictions, what challenges might organizations face when scaling AI agent deployments?    | ai-radar-2026-web-jan-2026-edit.pdf                                 |
| Edge case               | What happens when a multi-agent loop pattern fails to meet its exit condition?                                         | Google_AI_Agents.pdf                                                |

## Query Set 2: Test Scenarios

| Test Scenario                | Query Text                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Source Document                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Out-of-scope query           | What is the best pizza topping for a Friday night dinner party?                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | N/A - completely unrelated to docs                       |
| Multi-document synthesis     | Compare the guardrail and safety mechanisms recommended by AWS, Microsoft, and NVIDIA for production AI agent deployments.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | AWS_AI_Agents.pdf, Microsoft_AI_Agents.pdf, NVIDIAAn.pdf |
| Ambiguous query              | How do agents work?                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Multiple docs possible                                   |
| Very long query (100+ words) | I am currently working on implementing an enterprise-grade AI agent system for my organization and I need to understand the complete architectural considerations including but not limited to the various design patterns available such as sequential processing, parallel execution, hierarchical coordination, and swarm-based approaches. Additionally, I want to know how these patterns compare across different vendor recommendations from major cloud providers and AI research organizations. Furthermore, I need guidance on decision frameworks that can help me determine when to use simple workflows versus fully autonomous agents, taking into account factors like task complexity, error tolerance, and the need for human oversight in critical decision points. Can you provide a comprehensive overview? | Google_AI_Agents.pdf, Decision-Tree.md                   |
| Single-word query            | Guardrails                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | OpenAI_AI_Agents.pdf                                     |

---

## Copy-Pastable Excel Format (Tab-separated)

### Query Set 1
```
Query Type	Query Text
Factual lookup	What are the two key variations of the parallelization workflow pattern according to Anthropic?
Cross-document	How do Anthropic, OpenAI, and Google each define the distinction between workflows and agents?
Synthesis	What workforce archetypes are predicted to emerge in the agent-orchestrated enterprise, and how do their roles differ?
No-answer (adversarial)	What is the maximum token limit for GPT-4 when used in agentic workflows?
Vague / broad	Explain transformers
Specific detail	In the Agentic AI Stack, what is the embedding dimensionality for sentence-transformers versus Nomic Embed?
Comparison	How does the sequential multi-agent pattern differ from the parallel multi-agent pattern in terms of orchestration?
Process / how-to	What are the five stages in the Claude decision framework for determining whether to build an agentic system?
Inference	Based on the AI Radar 2026 predictions, what challenges might organizations face when scaling AI agent deployments?
Edge case	What happens when a multi-agent loop pattern fails to meet its exit condition?
```

### Query Set 2
```
Test Scenario	Query Text
Out-of-scope query	What is the best pizza topping for a Friday night dinner party?
Multi-document synthesis	Compare the guardrail and safety mechanisms recommended by AWS, Microsoft, and NVIDIA for production AI agent deployments.
Ambiguous query	How do agents work?
Very long query (100+ words)	I am currently working on implementing an enterprise-grade AI agent system for my organization and I need to understand the complete architectural considerations including but not limited to the various design patterns available such as sequential processing, parallel execution, hierarchical coordination, and swarm-based approaches. Additionally, I want to know how these patterns compare across different vendor recommendations from major cloud providers and AI research organizations. Furthermore, I need guidance on decision frameworks that can help me determine when to use simple workflows versus fully autonomous agents, taking into account factors like task complexity, error tolerance, and the need for human oversight in critical decision points. Can you provide a comprehensive overview?
Single-word query	Guardrails
```

---

## Query Rationale

| Query Type / Scenario | Why This Tests RAG Well |
|-----------------------|------------------------|
| Factual lookup | Direct retrieval: answer is "Sectioning" and "Voting" from Anthropic doc |
| Cross-document | Requires synthesizing definitions from 3 different vendor perspectives |
| Synthesis | Requires combining M-Shaped, T-Shaped, and AI-Augmented archetypes into coherent summary |
| No-answer (adversarial) | Tests hallucination resistance - GPT-4 token limits are not discussed |
| Vague / broad | Tests how system handles ambiguous queries needing clarification or scope |
| Specific detail | Precise number retrieval: 384-dim vs 768-dim |
| Comparison | Requires extracting and contrasting two pattern descriptions |
| Process / how-to | Tests multi-step procedural retrieval from decision tree |
| Inference | Requires reasoning beyond explicit text based on trends |
| Edge case | Tests retrieval of failure/boundary condition documentation |
| Out-of-scope query | Tests system's ability to recognize and handle completely irrelevant queries |
| Multi-document synthesis | Tests retrieval across 3 vendor docs and coherent synthesis of safety practices |
| Ambiguous query | Tests disambiguation - could refer to software agents, AI agents, or human agents |
| Very long query (100+ words) | Tests query parsing, key concept extraction, and handling of verbose input |
| Single-word query | Tests retrieval with minimal context - system must infer intent from one term |
