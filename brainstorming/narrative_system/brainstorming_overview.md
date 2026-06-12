Below is a **brainstormed narrative system architecture** that fits naturally into your improved **sensor system**, **action system**, and **FSM runtime**. This is not a finished design — it’s an exploration of how to graft a **dramatic narrative engine** onto your emerging agent-behavior framework.

I’ll structure this into:

1. **High-level concept**
2. **Narrative FSMs**
3. **Narrative sensors**
4. **Narrative actions**
5. **Narrative “beats” & story arcs**
6. **Integration with the existing economic/action/sensor systems**
7. **Examples of narrative-driven agent behavior**
8. **Optional emergent drama layer**

---

# ⭐ 1. High-Level Concept: A “Narrative Behavior Layer”

The idea is to add a **second behavioral layer** on top of economic/survival behaviors:

* **Base Layer (existing):** Agents act to satisfy needs, perform work, trade, eat, sleep, etc.
* **Narrative Layer (new):** Agents participate in *story arcs*, *dramatic beats*, *relationships*, and *long-form interactions*.

This narrative layer:

* Runs slower (e.g., daily instead of hourly)
* Coexists with survival behaviors
* Uses **FSM mini-dramas** to guide agents through story arcs
* Uses the same structured **ActionType**, **SensorType**, and **Registry** systems

Think of it like a lightweight version of *The Sims* aspiration + drama engine.

---

# ⭐ 2. Narrative FSMs (Story Machines)

Your existing **FSM runtime** is ideal for narrative content.

You can introduce **Narrative FSMs**:

* Each FSM is a *story arc*
* States represent **narrative beats**
* Transitions depend on **narrative sensors**
* Actions correspond to **dramatic actions**

Example narrative FSM: “Reconciliation Arc”

```
State: RESENTMENT
    If Z_FORGIVENESS_POSSIBLE → State: INITIATE_CONVERSATION

State: INITIATE_CONVERSATION
    Action: A_START_TALK
    If Z_CONVERSATION_SUCCESS → State: APOLOGY

State: APOLOGY
    Action: A_APOLOGIZE
    If Z_RESOLUTION → State: RESOLVED
```

This is exactly how your economic FSMs work — same runtime, different domain.

### Characteristics of Narrative FSMs

* They are **opt-in**: agents only instantiate arcs if conditions are met
* They can run concurrently with economic FSMs
* They can override or influence behavior (e.g., interrupt work to confront someone)
* They may have longer timescales (one state per half-day, not per hour)

---

# ⭐ 3. Narrative Sensors

Using the improved sensor system, narrative sensors can be added easily.

Examples:

### Relationship sensors

* `Z_RELATIONSHIP_STRONG`
* `Z_RELATIONSHIP_WEAK`
* `Z_CONFLICT_EXISTS`
* `Z_ROMANTIC_INTEREST`
* `Z_FRIENDSHIP_GROWING`
* `Z_NEEDS_RESOLUTION`

### Emotional/psychological sensors

* `Z_ANGER`
* `Z_LONELINESS`
* `Z_JEALOUSY`
* `Z_CONFIDENCE`
* `Z_STRESS`

### Situational narrative sensors

* `Z_TWO_AGENTS_ALONE`
* `Z_PUBLIC_EVENT_HAPPENING`
* `Z_SOCIAL_OPPORTUNITY`
* `Z_SECRET_REVEALED`

Each sensor is just another entry in the sensor registry.

---

# ⭐ 4. Narrative Actions

Build narrative-relevant actions using the new **ActionType** design:

### Interpersonal dramatic actions

* `A_CONFRONT`
* `A_APOLOGIZE`
* `A_CONFESS`
* `A_FLIRT`
* `A_SHARE_SECRET`
* `A_ASK_FOR_HELP`
* `A_DEFUSE_TENSION`
* `A_REMINISCE`
* `A_TELL_STORY`

### Group dramatic actions

* `A_RALLY_GROUP`
* `A_GIVE_SPEECH`
* `A_CALL_MEETING`

Each action contains:

* Preconditions (e.g., must be near target)
* Parameter resolution (choose *which* agent to confront)
* Effects (update relationship scores, create events, update arcs)

---

# ⭐ 5. Narrative “Story Beats” and Arcs

We could introduce **Narrative Arc Definitions**:

A **story arc** is a container made up of:

* A narrative FSM
* Initial trigger conditions
* Expected participants
* Priority relative to economic goals

Examples of arcs:

### Personal arcs

* **Ambition Arc** (find meaning, pursue career)
* **Jealousy Arc** (resolve romantic tension)
* **Friendship Arc**
* **Rivalry Arc**
* **Mentorship Arc**

### Social arcs

* **Festival Arc**
* **Small Community Conflict Arc**
* **Leadership Crisis Arc**
* **Group Decision Arc**

### Economic-narrative crossover arcs

* **Resource Scarcity Arc**
* **Unionization Arc**
* **Family Financial Hardship Arc**

Each arc is just a **higher-level wrapper** around a narrative FSM.

---

# ⭐ 6. Integration with Existing Frameworks

### How narrative FSMs plug in:

You already have:

* Sensor system
* Action system
* FSM runtime
* Controllers per-agent per-hour

We introduce:

### ✔ Narrative Manager (new subsystem)

Runs at a coarser timestep (once per day or once per 6 hours):

1. Checks narrative triggers
2. Instantiates arcs for relevant agents
3. Advances narrative FSMs
4. Outputs desired narrative **ActionInstances**
5. These actions are fed into the improved action pipeline

### ✔ Controllers support two “channels”

* **Economic channel** (existing)
* **Narrative channel** (new)

Controller decides which channel’s action “wins”:

* Narrative beats often override economic behavior
* But can be deprioritized during emergencies

### ✔ Logging

Every narrative FSM progression is logged:

```
{
  "agent": "Alice",
  "arc": "Reconciliation",
  "old_state": "RESENTMENT",
  "new_state": "INITIATE_CONVERSATION",
  "reason": "Z_FORGIVENESS_POSSIBLE activated"
}
```

### ✔ Sensors unify everything

Narrative arcs simply rely on narrative sensors just like economic behavior relies on economic sensors.

---

# ⭐ 7. Examples of Narrative-Driven Agent Behaviors

### Example 1: Rivalry Arc

* Bob and Hank both want the same job
* `Z_COMPETITIVE_TENSION` activates
* Narrative FSM progresses → confrontation action:

```
A_CONFRONT(target=Hank)
```

* Relationship decreases
* Economic behaviors adjust:

  * Agents may sabotage each other
  * Agents take different actions based on stress/anger

### Example 2: Romance Arc

* Alice and Sam share cooperative actions
* Relationship grows
* Narrative FSM triggers:

  * `A_INVITE_TO_WALK`
  * `A_FLIRT`
* Economic system doesn’t interfere unless needs are urgent

### Example 3: Community Crisis Arc

If the town loses too many fish:

* `Z_RESOURCE_SCARCITY` active
* Narrative arc triggers:

  * Stakeholder meeting among agents
  * Actions like:

    * `A_DEBATE`
    * `A_PROPOSE_POLICY`
    * `A_COORDINATE_WORK`

---

# ⭐ 8. Optional: Emergent Drama Layer

Once the structured systems are fully in place:

You can add a **drama manager** — a subsystem that ensures narrative richness by influencing:

* frequency of conflicts
* romantic opportunities
* reconciliation events
* secrets
* unexpected events

This is how *Left 4 Dead*, *The Sims 4*, and *RimWorld* maintain drama.

It works perfectly with your structured sensor/action system.

---

# ⭐ Summary

Your existing architecture is already the perfect foundation for a narrative system:

* FSM runtime → story machines
* Sensor system → narrative conditions
* Action system → dramatic actions
* Logging → narrative data
* Controllers → combine economic + narrative decisions

The new, structured design makes narrative content:

* easy to define
* easy to run
* data-driven
* extensible
* introspectable

