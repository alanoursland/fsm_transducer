The second you say things like **rivalry arc**, **romance arc**, **apology**, **confrontation**, you’ve implicitly assumed:

* agents **remember** each other
* they have **opinions** about each other
* they have **history** together
* they can be in different **relationship states** (friends, rivals, mentor/mentee, etc.)

That’s a *social state*.

---

## 1. Social State as a First-Class Subsystem

Right now, an `Agent` has things like:

* biology state
* inventory
* money
* skills
* preferences

We’d add:

```python
agent.social_state
```

as a structured object, not just a couple of numbers.

Conceptually, **social state** breaks down into:

1. **Relationships (graph edges)**
2. **Traits & dispositions (per-agent)**
3. **Short-term state (mood, current emotions)**
4. **Memory snippets / events**

Each of these feeds sensors and narrative FSMs, and is mutated by narrative actions.

---

## 2. Relationships: the social graph

At minimum: a weighted graph between agents.

Per pair `(A, B)` you might track:

* `friendship` (−1.0 … +1.0)
* `trust`
* `romantic_interest`
* `respect`
* `resentment` or `grudge`
* `history_flags` (e.g., “saved my life”, “betrayed me”, “stole from me”)

So something like:

```python
class Relationship:
    friendship: float
    trust: float
    romantic_interest: float
    rivalry: float
    tags: set[str]  # "mentor", "family", "boss", "ex_partner", ...
```

And a `SocialState` object might hold:

```python
class SocialState:
    relationships: dict[AgentId, Relationship]
```

### How this ties to narrative FSMs

Narrative sensors like:

* `Z_RELATIONSHIP_STRONG`
* `Z_CONFLICT_EXISTS`
* `Z_ROMANTIC_INTEREST`

…just read these relationship fields and threshold them.

Narrative actions like `A_APOLOGIZE` or `A_BETRAY` update them.

---

## 3. Traits & Dispositions

Some drama depends not just on “what happened” but on “who they are.”

Per-agent traits might include:

* `agreeableness`, `neuroticism`, `extroversion`-like sliders
* `conflict_avoidant`, `vengeful`, `loyal`, `ambitious`, `jealous` tags
* “script preferences” (who is likely to initiate romance? who starts fights?)

These live in something like:

```python
class SocialTraits:
    agreeableness: float
    assertiveness: float
    jealousy: float
    forgiveness: float
    tags: set[str]  # "leader", "introvert", "stoic", ...
```

Traits affect:

* probability of certain actions (e.g., confront vs withdraw)
* thresholds for sensors (what counts as “Z_ANGER” or “Z_HUMILIATED”)
* which narrative arcs an agent is eligible for

---

## 4. Short-Term State: Moods & Emotions

You don’t want relationships changing wildly every tick; instead:

* instantaneous **events** → affect **emotions/mood**
* sustained patterns → slowly adjust **relationship metrics**

Per-agent ephemeral state might be:

* `mood` (happy/sad/anxious/angry)
* `stress`
* `loneliness`
* `social_satiation`

Which:

* feeds sensors like `Z_LONELY`, `Z_ANGRY`, `Z_SOCIAL_NEED_HIGH`
* influences whether an agent seeks out narrative interactions vs just working

This parallels biology: short-term fatigue vs long-term health.

---

## 5. Memories / Social Events

For richer drama, you eventually want:

* a log of important events:

  * “Hank betrayed Alice during the fishing dispute on day 12”
  * “Sam helped Bob survive during the storm”

You don’t need full replay; just **labeled events** that can be referenced:

* sensors like `Z_RECENT_BETRAYAL`, `Z_UNRESOLVED_INSULT`
* narrative arcs like “Revenge”, “Reconciliation”, “Gratitude”

This could be as simple as:

```python
@dataclass
class SocialEvent:
    kind: str          # "betrayal", "gift", "rescue"
    other_id: AgentId
    day: int
    magnitude: float
```

And `SocialState` might keep a capped list per relationship.

---

## 6. How It Fits the Existing Frameworks

### Sensors

Social state → **social sensors**:

* `Z_RELATIONSHIP_STRONG(A,B)`
* `Z_TWO_AGENTS_ALONE(A,B)`
* `Z_UNRESOLVED_CONFLICT(A,B)`
* `Z_LONELY(A)`
* `Z_SOCIAL_OVERSATIATED(A)`

These are just more entries in the sensor registry, with eval_fns that read `agent.social_state`.

### Actions

Narrative actions read and write social state:

* `A_CONFRONT(target)` lowers trust, raises rivalry
* `A_APOLOGIZE(target)` nudges friendship/trust up if accepted
* `A_SHARE_MEAL` affects both biology and relationship
* `A_HELP_WITH_WORK` raises respect and cohesion

From the action system’s POV, it’s just another effect domain, like inventory or biology.

### FSMs

Narrative FSMs consume these sensors:

* “If Z_CONFLICT_EXISTS and Z_LONELY and Z_OPPORTUNE_MOMENT → A_START_TALK”
* “If Z_TRUST_HIGH and Z_PRIVATE_MOMENT → A_CONFESS_SECRET”

And produce actions that mutate social state.

### Controllers

Controllers can now treat social state as another need dimension:

* Economic needs: hunger, energy, money
* Social needs: loneliness, belonging, status, affection

They might choose:

* “Work another hour” vs “Seek social interaction”
* “Avoid rival” vs “Confront rival”

---

## 7. What You Get From a Social State Layer

Once social state exists as a first-class thing:

* Narrative arcs have concrete, inspectable state to drive them.
* You can visualize the town as a **social graph** evolving over time.
* You can analyze logs:

  * “Which arcs happen most?”
  * “Which relationships are most stable?”
  * “Do scarcity crises increase conflict edges?”

And because your whole architecture is already registry + structured state + FSM, this fits in beautifully as:

* another state block on the agent
* more sensors
* more actions
* more FSMs

No new engine type required — just more **content** in the same engine.

