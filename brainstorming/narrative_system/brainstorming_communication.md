Here is a **deep brainstorming document** describing a communication system in which agents **tell each other about observations**, form **beliefs**, maintain **confidence levels**, and propagate **imperfect knowledge** throughout the world.

This is purely conceptual—no implementation constraints yet.

---

# brainstorming_communication_and_knowledge_system.md

*Agents sharing information, forming beliefs, and reasoning under uncertainty*

This document explores how a communication system might work inside the agent architecture, especially alongside:

* **Sensors** (true local observations)
* **Narrative / social state**
* **Action system**
* **FSMs**

The goal:
Agents should maintain **knowledge** about the world that comes from:

1. **Direct observation** (high confidence)
2. **Communication from others** (lower, source-dependent confidence)
3. **Inference** (derived conclusions)

This enables social dynamics such as:

* rumors propagating
* trust/distrust affecting knowledge formation
* agents making bad decisions based on bad intel
* emergent gossip networks
* coordinated planning (“I heard food is low in the south fields”)
* deception and manipulation
* misunderstandings and conflict
* shared knowledge (“everyone knows that Bob is angry”)

---

# 1. Core Concepts: Beliefs, Sources, and Confidence

Agents do not store “facts.” They store **beliefs**, each with metadata:

### 1.1 Belief structure

A belief could be modeled as:

```python
Belief:
    content: any  # structured fact: "resource:berries:low", "Alice:is_angry", etc
    source: "self" | agent_id | "inferred"
    confidence: float  # 0.0–1.0
    timestamp: hour/day
```

### 1.2 Confidence tiers

* **Direct Observation** → confidence 1.0
* **Inference** → confidence ~0.7 (depends on complexity)
* **Information from trusted agent** → ~0.6
* **Information from untrusted agent** → ~0.3
* **Rumors / chain-of-communication** → decreasing confidence each hop

This creates a **belief decay network** resembling real gossip dynamics.

---

# 2. Knowledge Categories

Beliefs can exist across multiple domains:

### 2.1 Environmental knowledge

* “Berries in region X are plentiful.”
* “A storm is coming.”
* “The well is contaminated.”

### 2.2 Social knowledge

* “Alice likes Bob.”
* “Hank is angry at the mayor.”
* “Dana and Miguel had a fight.”

### 2.3 Economic knowledge

* “The tool maker is out of axes.”
* “Wheat yields are bad this year.”

### 2.4 Narrative & emotional knowledge

* “Sam apologized to Carla.”
* “There is unresolved conflict between Tim and Rosa.”

This pairs naturally with the **social state** and **observation tokens** we just brainstormed.

---

# 3. Communication as Actions

Communication should be implemented as **explicit actions**:

* `A_TELL(agent, fact)`
* `A_WARN(agent, danger_type)`
* `A_SHARE_GOSSIP(agent, topic)`
* `A_ASK(question)`
* `A_REPLY(answer)`
* `A_SPREAD_RUMOR`
* `A_SEEK_INFORMATION`

Each action results in:

* **Message creation**
* **Transmission**
* **Reception interpretation**
* **Belief update**

Messages are events that an agent interprets using their own:

* trust level
* current mood
* social context
* relationship with sender

Example:

> If Bob tells Alice “Hank is angry,” Alice interprets it with confidence
> `= trust(Alice, Bob) × base_message_reliability`.

---

# 4. Belief Updating

When new information arrives, the agent:

1. **Looks up existing beliefs** about the same topic.

2. **Compares timestamps** (a newer message might override older info).

3. **Combines confidences**:

   * If new info aligns with existing info: reinforce confidence.
   * If new info contradicts existing info:

     * choose higher-confidence source
     * OR maintain multiple hypotheses (“maybe…”, “maybe not…”)

4. **Adjusts beliefs gradually**, unless the source is extremely trusted.

### 4.1 Example: contradiction

* Alice’s belief: “Hank is calm” (confidence 0.8)
* Bob says: “Hank is furious” (confidence from Bob: 0.4)

Alice might create:

* belief “Hank is angry” with 0.4
  AND/OR
* reduce confidence in “Hank is calm” to 0.7

If Carla later says “Hank is indeed angry” (confidence 0.7):

→ Alice’s belief “Hank is angry” might rise to 0.8 and override the calm hypothesis.

This models **social triangulation**.

---

# 5. Knowledge Decay Over Time

Beliefs decay, representing:

* forgetting
* outdated info
* rumors fading
* environmental changes

Confidence decreases gradually unless refreshed.

Example decay function:

```
confidence = confidence * 0.995 per hour
```

Or more domain-specific:

* Emotions decay fast.
* Facts about geography decay slowly.
* Economic knowledge updates seasonally.

---

# 6. Rumors and Gossip Dynamics

Rumors arise when:

* Agents share low-confidence information.
* Agents infer incorrectly.
* Information is incomplete.

Rumor propagation patterns:

* High-trust networks amplify truth faster.
* Low-trust, high-social-energy agents spread rumors more.
* Rivalries distort messages (maliciously or unintentionally).

Optional:
Each message can mutate slightly at each hop → “telephone effect.”

---

# 7. Lie Detection and Truth Evaluation

Agents may use:

* **Cross-checking** (“Have others said the same?”)
* **Internal sensors** (“Does this contradict what I saw?”)
* **Trust levels**

If repeated contradictions occur from the same agent:

* trust decreases
* future messages have lower weight

This produces emergent dynamics:

* chronic liars
* unreliable gossips
* sages and trusted elders

---

# 8. Collective Knowledge & Emergence

If agents communicate enough, they form **shared beliefs**:

* “Everyone knows the storm is coming.”
* “Everyone knows Hank is dangerous.”
* “Everyone knows the well is poisoned.”

This can drive:

* collective action
* panic
* mass cooperation
* scapegoating
* faction formation

The knowledge system becomes a **distributed consensus algorithm** with noise and gossip.

---

# 9. Integration with Sensors and Actions

### 9.1 Observations → Beliefs

When an agent sees something:

* They create a 1.0-confidence belief.

### 9.2 Beliefs → Narrative Sensors

Narrative FSMs can operate on:

* direct observation sensors (e.g., “I see Bob nearby”)
* belief-based sensors (“I believe Bob is angry”)

Some examples:

* `Z_BELIEF_AGENT_IS_ANGRY(B)`
* `Z_BELIEF_RESOURCE_SCARCE(X)`
* `Z_BELIEF_FRIENDSHIP_HIGH(B)`
* `Z_BELIEF_AGENT_TRUSTWORTHY(B)`

FSMs combine direct perception + beliefs for richer decisions.

### 9.3 Beliefs → Actions

Agents act differently based on what they **think** is true:

* avoid someone they believe is angry
* prepare for famine based on rumors
* attack based on mistaken beliefs
* apologize based on what they were told

This yields emergent drama.

---

# 10. Advanced Extensions

### 10.1 Different communication styles

Some agents:

* overshare
* withhold
* manipulate
* mislead
* embellish
* communicate strategically

Traits (e.g. “gossip-prone”, “secretive”, “diplomatic”) can modulate:

* what they choose to tell
* how much
* to whom
* with what spin

### 10.2 Multimodal messages

Messages could contain:

* raw observations
* beliefs
* emotions
* requests
* intentions

### 10.3 Multi-agent “stories”

Agents might retell:

* what they saw
* how they felt
* what someone else said

Creating rich, nested narratives.

---

# 11. Minimal V1 System

A small but powerful initial system might include:

### 1. Belief objects with:

* content
* confidence
* source
* timestamp

### 2. Communication actions:

* tell, warn, share, ask, reply

### 3. Trust-weighted confidence updates

### 4. Belief decay

### 5. Basic sensors:

* `Z_BELIEF_AGENT_TRUSTWORTHY(B)`
* `Z_BELIEF_RESOURCE_SCARCE(X)`
* `Z_BELIEF_AGENT_IS_ANGRY(B)`

### 6. A simple rumor propagation model

This is enough for:

* emergent misinformation
* social misunderstandings
* coordinated planning
* basic dramatic arcs
* factionalization

