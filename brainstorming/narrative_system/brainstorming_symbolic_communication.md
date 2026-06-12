*Communication through symbols instead of natural language*

The core idea:

> **Agents exchange structured symbolic messages that represent meanings directly, not words.**

This is *not* “the agent said: ‘there is danger over the hill’”;
it’s **the agent sent a symbol structure** like:

```
(MSG
   type=DANGER_ALERT
   location=hill_south
   cause=wolf_pack
   certainty=0.7
)
```

Agents interpret these symbols through:

* trust
* belief confidence updating
* social context
* their own narrative FSMs
* their goals and emotional state
* their internal ontology of the world

---

# 1. Messages Are Symbol Structures

Each message is simply a **structured data object**.

Something like:

```python
Message:
    sender_id: str
    content: SymbolicContent
    timestamp: int
    context_tags: set[str]  # "private", "public", "urgent"
```

Where `SymbolicContent` is something like:

```python
class SymbolicContent:
    symbol: str   # e.g. OBSERVATION, BELIEF, INTENTION, REQUEST
    data: dict    # arbitrary structured key values
```

### Example messages:

#### 1. “Hank is angry”

```
{ symbol: "BELIEF_UPDATE",
  data: { target: "HANK", attribute: "ANGER", value: True, confidence: 0.6}}
```

#### 2. “Berries low in east grove”

```
{ symbol: "OBSERVATION",
  data: { resource: "berries", location: "east_grove", state: "low" }}
```

#### 3. “Request help”

```
{ symbol: "REQUEST",
  data: { need: "ASSIST_WORK", location: "farm_field" }}
```

#### 4. “Intent to romance Bob”

```
{ symbol: "INTENTION",
  data: { action: "SEEK_CLOSENESS", target: "BOB", strength: 0.9 }}
```

No words.
No grammar.
Just direct meaning.

---

# 2. Symbol Ontology

Agents must share a **common ontology** of:

* object types (`AGENT`, `RESOURCE`, `LOCATION`, `EVENT`)
* attribute types (`anger`, `trust`, `scarcity`)
* event types (`conflict`, `gift`, `cooperation`)
* narrative roles (`rival`, `ally`, `love_interest`)
* action types
* story arc identifiers

This ontology is part of the **global knowledge space**.

### Why this works:

Because our entire simulation is built on **symbolic internal state**:

* sensors return symbolic state
* actions are symbolic
* social graphs are symbolic
* beliefs are symbolic
* FSM conditions test symbols

**There is no need for natural language in the internal communication pipeline.**

---

# 3. Symbolic Belief Updates

When an agent receives a symbolic belief message:

```
{ symbol: "BELIEF_UPDATE",
  data: { target: "CARLA", attribute: "ANGER", value: True, confidence: 0.4}}
```

The receiver updates its internal `beliefs` table:

* add new belief or modify existing one
* store the source (`sender_id`)
* weight by trust

This is exactly how we designed the belief system earlier — but now it is explicit and symbol-based.

---

# 4. Structured Messages Enable Rich Social Dynamics

### 4.1 Gossip

```
{ symbol: "GOSSIP",
  data: { topic: "ROMANCE", agents: ["ALICE","BOB"], confidence: 0.3 }}
```

### 4.2 Warning

```
{ symbol: "ALERT",
  data: { type: "DANGER", location: "north_forest", cause: "bandits" }}
```

### 4.3 Social negotiation

```
{ symbol: "NEGOTIATION",
  data: { request: "WORK_EXCHANGE", offer: "LABOR:2H", in_return: "BERRIES:5" }}
```

### 4.4 Emotional self-report (symbolic emotion sharing)

```
{ symbol: "SELF_STATE",
  data: { emotion: "SAD", cause: "LOSS_OF_ITEM", intensity: 0.7 }}
```

Narratives can depend heavily on **symbolic emotional communication**.

---

# 5. Agents Interpret Symbols Based on Internal Models

Meaning is not universal.
Two agents might interpret the same symbol differently.

Example:

```
{ symbol: "ALERT", data: { type: "DANGER", cause: "WOLF" }}
```

A brave agent:

* increases vigilance slightly
* does not avoid the forest

A cowardly agent:

* treats confidence 0.3 as 0.9
* refuses to work near forest

A rival who distrusts sender:

* treats confidence as half
* disregards message entirely

This leads to **asymmetric knowledge** and naturally emergent misunderstandings.

---

# 6. Messages Influence Social State

Messages update:

* trust (how reliable sender seems)
* closeness (sharing personal info increases intimacy)
* rivalry (lying decreases trust)
* respect (warnings may increase respect)
* resentment (nagging may lower respect)

Symbolic communication plays directly into:

* relationship graph
* emotions
* narrative arcs
* cooperation
* conflict

---

# 7. Higher-Level Symbolic Structures

Agents may eventually exchange:

* **sets** of beliefs
* **graphs** (subgraphs of the relationship network)
* **sequences** (timelines, if memory recitation is implemented)
* **schemas** (e.g., a plan)

### Example complex message: A Plan

```
{ symbol: "PLAN",
  data: { steps: [
          {action:"GATHER_RESOURCES", location:"grove"},
          {action:"BUILD_SHELTER", target:"hill_top"}
        ],
        purpose: "STORM_PREPARATION",
        urgency: 0.8 }
}
```

Now agents can coordinate to:

* plan defenses
* execute cooperative work
* perform rituals
* negotiate complex exchanges
* trigger group narratives

---

# 8. Sensor Integration

Agents may have sensors:

* `Z_RECEIVED_ALERT(type="DANGER")`
* `Z_RECEIVED_GOSSIP(confidence>0.3)`
* `Z_MESSAGE_FROM(agent="BOB")`
* `Z_COMMUNICATION_RECENT`
* `Z_SHARED_BELIEF(target, attribute)`

Which feed into FSM transitions.

This ties perfectly into the improved sensor system.

---

# 9. No Natural Language Required

Benefits:

* deterministic
* easy to debug
* fast
* aligned with internal ontologies
* directly interpretable by FSMs
* safe: no ambiguity

If you ever want to surface natural language for the *player*, a translation layer can convert:

```
symbolic_message → human-readable text
```

But agents never need to see words.

---

# 10. Minimal V1 Symbolic Communication System

To start:

### 1. Message object

* `symbol`
* `data`
* `source`
* `confidence`

### 2. Two core message types

* `OBSERVATION`
* `BELIEF_UPDATE`

### 3. Basic communication actions

* `A_TELL_FACT`
* `A_WARN`
* `A_SHARE_SOCIAL_INFO`

### 4. Belief update rules

trust × sender-confidence

### 5. Knowledge sensors

* `Z_BELIEF_*`
* `Z_RECEIVED_*`

This is enough to generate:

* basic gossip
* misunderstandings
* cooperation
* emotional interactions

