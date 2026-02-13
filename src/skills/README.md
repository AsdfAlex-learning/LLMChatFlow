# Skills Module

This module provides **deterministic, controllable capability units** ("Skills") used by the `ExpressionOrchestrator` to generate specific parts of the agent's response.

## Core Concepts
- **Atomic Capabilities**: Each skill handles a specific aspect of expression (Text strategy, Body movement, Voice tone).
- **Configuration over Generation**: Skills often return configuration dictionaries (e.g., prompt instructions) rather than final text, allowing the Orchestrator/LLM to handle the final assembly.

## Directory Structure

### 1. Text Skills (`src/skills/text/`)
Define strategies for text generation. They return a dictionary containing `style_instruction`, `temperature`, `max_tokens`, etc.
- `short_reply.py`: For brief, concise interactions.
- `long_reply.py`: For deep, emotional, or detailed responses.
- `comfort.py`: Specialized strategy for comforting users.

### 2. Body Language Skills (`src/skills/body_language/`)
Define physical actions or gestures. They return an action string (e.g., "nod_once", "tilt_head_left").
- `idle.py`
- `nod.py`
- `shy.py`
- `tilt_head.py`
- `wave.py`

### 3. Voice Skills (`src/skills/voice/`)
Define vocal parameters (pitch, speed, tone).
- `whisper.py`

## Usage
Skills are typically invoked by the `ExpressionOrchestrator` based on the `ExpressionPlan` from the `EmpathyPlanner`.

```python
# Example: Using a Text Skill
from src.skills.text.short_reply import short_reply_strategy
config = short_reply_strategy(user_input)
# config -> {'style_instruction': '...', 'temperature': 0.7}

# Example: Using a Body Skill
from src.skills.body_language.nod import nod_action
action = nod_action()
# action -> "nod_once"
```
