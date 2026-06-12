# brainstorming_symbolic_fsm_communication.md  
_A unified model for agent communication using token strings, finite-state protocols, beliefs, and narrative integration_

This document explores and consolidates all ideas about **symbolic, token-based communication** where agents exchange **finite-state-interpretable token sequences** rather than natural language. Agents already use:

- **tokens** (sensor/action IDs),
- **FSMs** (behaviors, evaluators),
- **symbolic world models** (beliefs, social state),
- **structured observations** (via improved sensor system).

So this document imagines a communication system built from the **same primitives**—FSMs operating on token strings.

This is a *brainstorm*, not a spec.

---

# 1. Why Symbolic Communication?

Agents do not need natural language.  
They live in a symbolic world:

- Their sensors generate **Z\_TOKENS**  
- Their actions are **A\_TOKENS**  
- Their narrative triggers operate on **symbolic conditions**  
- Their beliefs and social state are symbolic structures  

So communication can simply be:

> **A sequence of tokens that another FSM can understand.**

Benefits:

- deterministic  
- unambiguous  
- easy to debug  
- easy to evolve  
- resilient  
- easy to log  
- easy to store in belief structures  
- compatible with existing FSM runtime  
- no parsing trees, no probabilistic NLP  

The communication system becomes an **extension of the FSM architecture**, not another subsystem.

---

# 2. Messages Are Token Streams

A message is simply a **linear sequence of tokens**:

```

MSG_START ALERT Z_DANGER_WOLF LOCATION_NORTH_GROVE CONFIDENCE_MED MSG_END

````

Important things to note:

- It's **just a token sequence**.  
- No structure other than order.  
- Meaning comes from the FSM that reads it.

Agents can both:

- **emit** token sequences (expression FSMs)
- **interpret** token sequences (interpretation FSMs)

---

# 3. Communication Protocols Are FSMs

You define a mini-language (a protocol) as a **finite-state machine**.

### 3.1 Example: Alert Protocol

Tokens:
- `MSG_START`
- `ALERT`
- `Z_*` observation token  
- `LOCATION_*`
- `CAUSE_*`
- `CONFIDENCE_LOW`, `CONFIDENCE_MED`, `CONFIDENCE_HIGH`
- `MSG_END`

FSM states:
- `S_START`
- `S_TYPE`
- `S_PAYLOAD`
- `S_CONF`
- `S_DONE`

When the FSM consumes a valid sequence, it outputs:

- a `BeliefUpdate`
- or triggers a narrative event
- or updates social trust

All **meaning** lives in what the FSM *does*.

---

# 4. Internal Knowledge Is Updated Symbolically

When the agent receives a message:

1. It feeds tokens into the protocol FSM.
2. The FSM reaches one of:
   - **ACCEPT**: message recognized  
   - **REJECT**: malformed message  
3. On ACCEPT, the FSM produces an **InterpretationResult**, e.g.:

```python
Belief(content="wolf_danger_at_north_grove",
       source=sender_id,
       confidence=0.5 * trust(receiver, sender),
       timestamp=current_hour)
````

**Trust** modulates incoming confidence:

```
effective_confidence = msg_confidence * trust(receiver, sender)
```

Knowledge now includes:

* the belief itself
* its source
* the derived confidence

This produces emergent misinformation and selective trust.

---

# 5. Types of Symbolic Messages

These are not fixed, just brainstormed categories.

### 5.1 Observation sharing

```
MSG_START SHARE_OBS Z_RESOURCE_LOW_EAST CONFIDENCE_HIGH MSG_END
```

### 5.2 Belief updates

```
MSG_START BELIEF_UPDATE TARGET_BOB STATE_ANGRY CONF_MED MSG_END
```

### 5.3 Requests

```
MSG_START REQUEST HELP LOCATION_FARM CONF_HIGH MSG_END
```

### 5.4 Warnings

```
MSG_START ALERT Z_DANGER_WOLF LOCATION_NORTH_GROVE CONF_LOW MSG_END
```

### 5.5 Gossip (social narrative)

```
MSG_START GOSSIP RELATION_ALICE_BOB_ROMANCE CONF_LOW MSG_END
```

### 5.6 Plans (multi-token sequences)

```
MSG_START PLAN STEP_GATHER_WOOD STEP_BUILD_HUT PURPOSE_SHELTER MSG_END
```

These could be broken into sublanguages, each with its own FSM.

---

# 6. Encoding Structured Meaning into Tokens

Because tokens can reference:

* `Z_*` sensor IDs
* `A_*` action IDs
* `AGENT_*` agents
* `RESOURCE_*` resources
* `LOCATION_*` identifiers
* `STATE_*` emotional states
* `SOCIAL_*` relationship states

The entire agent-internal ontology becomes communicable.

You can represent:

* emotions
* locations
* resource levels
* narrative arc stages
* plans
* threat types

…all as **token symbols**.

Token vocabulary grows naturally with the world model.

---

# 7. Belief Confidence, Time Decay, and Trust

Because communication is symbolic, agents store:

* `belief`
* `source`
* `original_confidence_from_message`
* `trust_weighted_confidence`
* `timestamp_last_updated`

Confidence decays over time:

```
belief.confidence *= 0.995 per hour
```

New information—directly observed or received—adjusts confidence.

Trust affects interpretation:

* trusted senders boost incoming message confidence
* rivals / disliked agents reduce it
* repeated contradictions reduce trust

This creates emergent gossip dynamics and misinformation patterns.

---

# 8. Message Noise and Mutation

Optionally:
Simulate imperfect communication without language ambiguity using **token-level perturbations**:

* random token drop
* random token duplication
* low-probability substitution (especially in multi-agent relays)
* truncation before `MSG_END`
* forced default confidence if `CONF_*` missing

This creates a “telephone game” without human language.

---

# 9. Expression FSMs: Generating Messages

Outgoing messages can be generated by FSMs:

* The agent has an **intended meaning** (e.g., “warn about wolf danger”).
* It chooses which protocol to use (“Alert protocol”).
* Runs an **expression FSM**, which outputs a valid token stream.

This mirrors human “utterance generation,” but symbolic.

Different agents can have:

* different expression FSMs
* different token preferences
* different ambiguity patterns

This produces **cultural drift** and “dialects.”

---

# 10. Integration with Social System

Communication tokens integrate seamlessly with **social state**:

### Example:

If an agent receives:

```
MSG_START BELIEF_UPDATE TARGET_BOB STATE_ANGRY CONF_HIGH MSG_END
```

Then:

1. They update a **belief**: “Bob is angry.”
2. That belief feeds **social sensors** like:

   * `Z_BELIEF_AGENT_IS_ANGRY(Bob)`
3. Narrative FSMs might react:

   * “If I believe Bob is angry and we have an unresolved conflict, initiate confrontation.”

Similarly:

* sharing personal emotional state boosts intimacy
* repeated lying reduces trust
* coordinated plans change group cohesion

Agents **learn about each other** via symbolic messages.

---

# 11. Integration with Narrative FSMs

Narrative arcs depend on:

* beliefs
* emotional state
* social state
* interaction opportunities
* misunderstandings

Messages produce beliefs → beliefs feed **Narrative Sensors** → sensors drive **Narrative FSMs** → FSMs generate actions → actions produce events → events produce messages → loop continues.

This creates emergent social drama:

* rumors initiate conflicts
* misunderstandings escalate
* alliances form
* reconciliation arcs complete
* community panic cascades

All driven by **symbolic communication tokens + FSM interpretation**.

---

# 12. Global or Local Protocols

Approaches to protocol design:

### 12.1 A Universal Message Grammar

* All agents use one large FSM
* Simple to manage
* Deterministic communication

### 12.2 Multiple Protocols

* “Alert protocol”
* “Gossip protocol”
* “Negotiation protocol”
* “Romance disclosure protocol”
* “Trade protocol”

Each is an FSM with its own token grammar.

### 12.3 Cultural Protocol Divergence (advanced)

Groups can diverge:

* token synonyms
* omitted mandatory tokens
* different ordering
* different confidence levels defaults

This produces **cultural drift** in communication styles.

---

# 13. Token-Level Compression for Efficiency

We can compress repeated symbol structures into single tokens:

Instead of:

```
RELATION_ALICE_BOB_ROMANCE
```

Use:

```
RELATION ROMANCE AGENT_ALICE AGENT_BOB
```

Or compress numeric values:

* `CONF_HIGH`, `CONF_MED`, `CONF_LOW`
* `INTENSITY_0_1`, `INTENSITY_0_5`, etc.

Tokens are flexible—you can tune their granularity.

---

# 14. Agent Knowledge Stores

Each agent has:

```
knowledge.beliefs     # belief objects derived from observation or messages
knowledge.messages    # optional buffer of recent messages
knowledge.conflicts   # contradictory beliefs for debugging/narrative
knowledge.inferences  # derived or inferred beliefs
```

Beliefs have:

* `content`
* `source`
* `confidence`
* `timestamp`

Optional:

* `belief_graph`: causal network of beliefs
* `belief_explanation`: where a belief came from (“heard from Bob”)

This is the symbolic analogue of a knowledge base.

---

# 15. Minimal Viable System (v1)

To keep it simple, a functional v1 could include:

### Tokens:

* `MSG_START`, `MSG_END`
* `ALERT`, `SHARE_OBS`
* `Z_*` sensor tokens
* `LOCATION_*`
* `CONF_LOW`, `CONF_MED`, `CONF_HIGH`

### FSMs:

* `AlertInterpreterFSM`
* `AlertExpressionFSM`
* `ObservationShareFSM`

### Belief system:

* belief store
* trust-modulated confidence
* time-based decay

### Actions:

* `A_COMMUNICATE_ALERT`
* `A_SHARE_OBSERVATION`

With just these, you get:

* basic info sharing
* emergent misinformation
* emergent trust/distrust
* misunderstandings
* narrative arcs involving danger, rumor, resource scarcity

Everything else can layer on top.

---

# 16. Long-Term Potential

The symbolic token + FSM communication layer can grow into:

* cultural languages
* diplomatic protocols
* ritual structures
* negotiation systems
* planning languages
* mathematical concepts (if desired)
* narrative exposition
* hierarchical message structures (by nesting FSM calls)

Because it is *formal*, it also remains:

* testable
* debuggable
* deterministic or intentionally noisy
* compatible with logging
* safe from arbitrary language injection

It is the ideal communication substrate for an FSM-driven simulation world.

---

# 17. Closing Thoughts

This approach harmonizes:

* the **FSM architecture**
* the **token-based sensor/action systems**
* the **social state**
* the **belief system**
* and the **narrative engine**

Agents do not need natural language.
They need **meaningful, symbolic, structured communication**.

FSM-interpreted token strings give you:

* structure
* composability
* learnability
* improvisation
* social dynamics
* narrative depth
* emergent behavior

…all without requiring a full syntax/semantics natural language generator.

