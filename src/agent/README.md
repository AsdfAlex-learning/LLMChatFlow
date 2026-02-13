# Agent Core Module

The `src/agent` module implements the cognitive and expressive core of the chatbot, moving beyond simple LLM calls to a structured, rule-guided, and personality-driven architecture.

## Components

### 1. EmpathyPlanner (`empathy_planner.py`)
The decision-making engine. It does **not** use LLMs. Instead, it uses rule-based logic to determine *how* the agent should respond based on the user's input and the agent's current state.
- **Inputs**: User message, `PersonaState`.
- **Outputs**: `ExpressionPlan` (Mood, TextStrategy, BodyAction).
- **Responsibilities**:
  - Determining if a reply is needed (`should_reply`).
  - Selecting the emotional tone (`mood`).
  - Choosing a reply strategy (e.g., `COMFORT`, `SHORT_REPLY`, `LONG_EMOTIONAL`).
  - Deciding on body language.

### 2. ExpressionOrchestrator (`orchestrator.py`)
The conductor that executes the plan. It bridges the gap between the abstract `ExpressionPlan` and the concrete `AgentResponse`.
- **Inputs**: `ExpressionPlan`.
- **Outputs**: `AgentResponse` (Final text, action string, voice parameters).
- **Responsibilities**:
  - Dispatching tasks to specific **Skills** (Text Skills, Body Skills).
  - Calling the `LLMClient` to generate the final text based on the strategy's instructions.
  - Assembling the multi-modal response.

### 3. PersonaState (`state.py`)
A dataclass that holds the agent's internal psychological state.
- **Attributes**:
  - `current_emotion`: The current mood.
  - `relationship_stage`: STRANGER -> FRIEND -> PARTNER.
  - `is_trusted`: Boolean flag.
- **Persistence**: Currently in-memory (per session), managed by `ChatService`.

### 4. Skills (`src/skills/`)
Reusable capabilities used by the Orchestrator.
- **Text Skills**: Return generation configuration (Prompt instructions, temperature, max tokens).
  - `short_reply`
  - `comfort`
  - `long_emotional`
- **Body Language Skills**: Return action descriptions.
  - `nod`, `wave`, `shy`, `idle`

## Integration Flow

1. **User Input** -> `ChatService`
2. `ChatService` retrieves `PersonaState`.
3. `ChatService` calls `Orchestrator.orchestrate_response(input, state, context, memory)`.
4. `Orchestrator` calls `Planner.plan_response(input, state)`.
5. `Planner` returns `ExpressionPlan`.
6. `Orchestrator` executes skills & calls LLM.
7. `Orchestrator` returns `AgentResponse`.
8. `ChatService` returns response to `InteractionManager`.
9. `InteractionManager` plays action & sends text.
