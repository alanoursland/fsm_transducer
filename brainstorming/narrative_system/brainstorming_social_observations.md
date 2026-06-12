```markdown
# brainstorming_social_state.md  
_Observations & social sensors for narrative and drama systems_

This document is a **brainstorm** of possible **social and narrative observations** we might want to expose through the sensor system.

- It’s intentionally **broad and redundant**.
- It’s not a spec; it’s a **menu**.
- Everything here is expressed as *observations* we could implement as sensors (e.g., `Z_*`), possibly parameterized by other agents.

Where I say “agent” I mean “the focal agent for whom we are computing sensors.”

---

## 0. Guiding idea

For narrative drama, an agent needs to be able to “perceive”:

- **Who** is around them  
- **What** they feel about those people  
- **What** has happened between them in the past  
- **What** roles everyone occupies in the community  
- **What** tensions and opportunities exist right now  

So social observations will draw from:

1. **Relationship graph**
2. **Emotions & mood**
3. **Memory & history**
4. **Contextual situation**
5. **Group / community state**
6. **Narrative arc progression**

---

## 1. Relationship-level Observations

These are about “me ↔ another agent”.

For a focal agent `A`, and some other agent `B`.

### 1.1 Basic relationship strength

- `Z_RELATIONSHIP_EXISTS(B)`  
- `Z_RELATIONSHIP_STRONG(B)`  
- `Z_RELATIONSHIP_WEAK(B)`  
- `Z_RELATIONSHIP_NEGATIVE(B)`  

Could map onto combined metrics of friendship, trust, rivalry.

### 1.2 Friendship / affection

- `Z_FRIEND(B)`  
- `Z_CLOSE_FRIEND(B)`  
- `Z_ACQUAINTANCE(B)`  
- `Z_LIKES(B)`  
- `Z_DISLIKES(B)`  

### 1.3 Romantic / intimate

- `Z_ROMANTIC_INTEREST(B)`  
- `Z_MUTUAL_ROMANTIC_INTEREST(B)`  
- `Z_CRUSH_ON(B)`  
- `Z_FORMER_PARTNER(B)`  
- `Z_POTENTIAL_PARTNER(B)`  

### 1.4 Trust & reliability

- `Z_TRUSTS(B)`  
- `Z_DISTRUSTS(B)`  
- `Z_HIGH_TRUST(B)`  
- `Z_LOW_TRUST(B)`  
- `Z_DEPENDS_ON(B)` (thinks B is essential for survival / work)  

### 1.5 Rivalry & conflict

- `Z_RIVAL(B)`  
- `Z_COMPETES_WITH(B)` (for same job, status, partner, resource)  
- `Z_HAS_GRUDGE_AGAINST(B)`  
- `Z_RECENT_CONFLICT(B)`  
- `Z_UNRESOLVED_CONFLICT(B)`  

### 1.6 Status & hierarchy

- `Z_SEES_AS_SUPERIOR(B)` (boss, leader, mentor)  
- `Z_SEES_AS_SUBORDINATE(B)` (apprentice, helper)  
- `Z_EQUAL_STATUS(B)`  
- `Z_FAMILY_MEMBER(B)`  
- `Z_ELDER(B)`  

---

## 2. Self-state Observations (Social / Emotional)

What the agent feels internally, socially and emotionally.

### 2.1 Social needs & drives

- `Z_LONELY`  
- `Z_SOCIAL_NEED_HIGH` (wants connection)  
- `Z_SOCIAL_SATIATED` (had enough social contact for now)  
- `Z_NEEDS_SUPPORT` (overwhelmed, wants help)  

### 2.2 Emotions (short-term)

- `Z_ANGRY`  
- `Z_HUMILIATED`  
- `Z_EMBARRASSED`  
- `Z_HAPPY`  
- `Z_PROUD`  
- `Z_ASHAMED`  
- `Z_ANXIOUS`  
- `Z_AFRAID`  
- `Z_RELIEVED`  

### 2.3 Longer-term moods & dispositions

- `Z_IN_A_BAD_MOOD`  
- `Z_IN_A_GOOD_MOOD`  
- `Z_DEPRESSED` (low long-term mood)  
- `Z_BURNED_OUT` (work + social exhaustion)  

### 2.4 Identity & roles (self-perception)

- `Z_SEES_SELF_AS_LEADER`  
- `Z_SEES_SELF_AS_OUTSIDER`  
- `Z_SEES_SELF_AS_HELPER`  
- `Z_SEES_SELF_AS_BURDEN`  

---

## 3. Memory & History Observations

Observations about **past events** and shared history.

### 3.1 Recent events with specific agents

For `(A, B)`:

- `Z_RECENT_HELP_FROM(B)`  
- `Z_RECENT_HELP_TO(B)`  
- `Z_RECENT_INSULT_FROM(B)`  
- `Z_RECENT_INSULT_TO(B)`  
- `Z_RECENT_COOPERATION_WITH(B)`  
- `Z_RECENT_BETRAYAL_BY(B)`  
- `Z_RECENT_BETRAYAL_OF(B)`  

### 3.2 Long-term relationship history

- `Z_HAS_HISTORY_OF_CONFLICT(B)`  
- `Z_HAS_HISTORY_OF_SUPPORT(B)`  
- `Z_LONG_TERM_FRIEND(B)`  
- `Z_HISTORY_OF_ROMANCE(B)`  

### 3.3 Open loops / unresolved threads

- `Z_UNUSED_FAVOR_OWED_BY(B)` (B owes A a favor)  
- `Z_UNUSED_FAVOR_OWED_TO(B)` (A owes B a favor)  
- `Z_UNFINISHED_ARGUMENT_WITH(B)`  
- `Z_UNCLOSED_PROMISE_WITH(B)`  

These are extremely useful for narrative arcs like “pay back a favor,” “resolve our fight,” etc.

---

## 4. Contextual / Situational Observations

What’s going on **right now** in the agent’s surroundings.

### 4.1 Presence & proximity of others

- `Z_ALONE`  
- `Z_WITH_OTHERS`  
- `Z_IN_SMALL_GROUP` (2–4)  
- `Z_IN_LARGE_GROUP`  
- `Z_IN_CROWD`  

Per-agent:

- `Z_NEAR(B)` (within some distance)  
- `Z_PRIVATE_MOMENT_WITH(B)` (only A and B nearby)  
- `Z_PUBLIC_SETTING` (others are in earshot)  

### 4.2 Location & setting

- `Z_AT_HOME`  
- `Z_AT_WORKPLACE`  
- `Z_AT_PUBLIC_SPACE` (market, tavern)  
- `Z_AT_MEETING_POINT`  

Narratively: some interactions only make sense in certain places.

### 4.3 Time / scheduling

- `Z_SOCIAL_HOUR` (evening / off work)  
- `Z_WORK_HOUR`  
- `Z_DAY_OF_FESTIVAL`  
- `Z_MORNING_ROUTINE_TIME`  

---

## 5. Group & Community Observations

About **groups** and collective state.

### 5.1 Focal agent’s group context

- `Z_MEMBER_OF_GROUP(G)` (family, work crew, faction)  
- `Z_IS_GROUP_LEADER(G)`  
- `Z_IS_LOW_STATUS_IN_GROUP(G)`  
- `Z_GROUP_COHESION_HIGH(G)`  
- `Z_GROUP_COHESION_LOW(G)`  
- `Z_GROUP_IN_CONFLICT(G)`  

### 5.2 Global community tensions

At a community level (town-wide):

- `Z_COMMUNITY_TENSE` (high aggregate conflict)  
- `Z_COMMUNITY_PROSPEROUS` (low economic stress)  
- `Z_COMMUNITY_SCARCITY` (food/wealth issues)  
- `Z_COMMUNITY_CELEBRATING` (festivals / rituals)  

These drive arcs like “crisis”, “festival”, “migration”, etc.

---

## 6. Narrative Arc / Story Beat Observations

Sensors tied directly into the narrative-arc FSMs.

### 6.1 Arc membership & phase

Per agent and arc:

- `Z_IN_ARC(arc_id)`  
- `Z_ARC_PHASE(arc_id, phase)`  
- `Z_ARC_NEEDS_PROGRESS(arc_id)` (time to move to next beat)  

### 6.2 Beat readiness

For specific beats within an arc:

- `Z_BEAT_CONDITIONS_MET(arc_id, beat_id)`  
- `Z_BEAT_ALREADY_COMPLETED(arc_id, beat_id)`  

### 6.3 Meta-narrative tension / pacing

- `Z_NEEDS_DRAMATIC_EVENT` (too quiet recently)  
- `Z_NEEDS_RESOLUTION` (too many unresolved arcs)  
- `Z_RECENT_DRAMATIC_SPIKE` (lots of conflict / intense events)  

These allow a narrative manager to throttle drama: more or less conflict, romance, or resolution.

---

## 7. Motivation & Goal Observations (Narrative-Flavored)

What the agent is **trying** to do at a narrative level.

### 7.1 Social goals

- `Z_WANTS_FRIENDSHIP`  
- `Z_WANTS_ROMANCE`  
- `Z_WANTS_FORGIVENESS`  
- `Z_WANTS_REVENGE`  
- `Z_WANTS_RECOGNITION` (status, praise)  

These can be derived from long-term traits, current moods, and unmet social needs.

### 7.2 Tradeoffs with other needs

Interplay between social and survival:

- `Z_SOCIAL_GOAL_OVERRIDES_WORK`  
- `Z_SOCIAL_GOAL_OVERRIDES_REST`  
- `Z_SURVIVAL_CRISIS_PREVENTS_SOCIAL_ACTION`  

---

## 8. Role & Identity Observations

Narrative often cares about **roles**, not just individuals.

### 8.1 Structural roles

- `Z_IS_LEADER_OF_GROUP(G)`  
- `Z_IS_HEALER`  
- `Z_IS_PROVIDER`  
- `Z_IS_OUTSIDER`  
- `Z_IS_NEWCOMER`  
- `Z_IS_ELDER`  

### 8.2 Story roles (from narrative arcs)

- `Z_STORY_ROLE_MENTOR`  
- `Z_STORY_ROLE_APPRENTICE`  
- `Z_STORY_ROLE_RIVAL`  
- `Z_STORY_ROLE_LOVE_INTEREST`  
- `Z_STORY_ROLE_ANTAGONIST`  
- `Z_STORY_ROLE_PROTAGONIST` (from the system’s POV, not player POV)  

These can change over time as arcs progress.

---

## 9. Economic + Social Cross-Observations

Because your world is fundamentally economic, many narrative dynamics should reflect economic conditions.

### 9.1 Economic stress on social state

- `Z_PERSONAL_FINANCIAL_STRESS_HIGH`  
- `Z_FAMILY_FINANCIAL_STRESS_HIGH`  
- `Z_GROUP_RESOURCE_SCARCITY`  
- `Z_JOB_COMPETITION_HIGH`  

### 9.2 Social interpretation of economic events

- `Z_BLAMES(B)_FOR_SCARCITY`  
- `Z_CREDITS(B)_FOR_PROSPERITY`  
- `Z_SEES_JOB_AS_STATUS_SYMBOL`  

---

## 10. Meta-Social Observations (System / Debug-Oriented)

Sensors that might be more for debugging or systemic meta-control:

- `Z_SOCIAL_GRAPH_DENSITY_HIGH` (too many tight relationships)  
- `Z_SOCIAL_ISOLATION_RISK(A)` (agent has too few ties)  
- `Z_SOCIAL_CONFLICT_CLUSTERING` (conflicts concentrated in a subgroup)  
- `Z_SOCIAL_BOTTLENECK_AGENT(A)` (everyone depends on this agent)  

These may never appear in narrative scripts but are useful for tuning.

---

## 11. Parameterization Considerations

Many of these observations are naturally **parameterized** by:

- `other_agent`  
- `group`  
- `arc_id`  
- `beat_id`

At the sensor-system level, that implies:

- either first-class **parameterized sensors**  
- or expanded tokens like `Z_FRIENDSHIP_STRONG_WITH:Bob` (not ideal)  
- or a smaller, generic set of sensors that take runtime parameters and are used by higher-level logic rather than raw FSM tokens.

This is a design question for the sensor DSL, but for brainstorming we can assume:

> “There exists some way to ask: _How do I feel about B?_”

---

## 12. Minimal Useful Subset (for v1)

If we had to pick a **small set** to start with for a first narrative prototype, it might be:

### Self / emotions
- `Z_LONELY`  
- `Z_IN_A_BAD_MOOD`  
- `Z_NEEDS_SUPPORT`  

### Relationship basics
- `Z_FRIEND(B)`  
- `Z_RIVAL(B)`  
- `Z_TRUSTS(B)`  
- `Z_RECENT_CONFLICT(B)`  

### Context
- `Z_NEAR(B)`  
- `Z_PRIVATE_MOMENT_WITH(B)`  
- `Z_PUBLIC_SETTING`  
- `Z_SOCIAL_HOUR`  

### Narrative hooks
- `Z_UNRESOLVED_CONFLICT(B)`  
- `Z_WANTS_FRIENDSHIP`  
- `Z_WANTS_REVENGE`  

You could already build:

- simple friendship-building arcs  
- rivalry / conflict arcs  
- reconciliation arcs  

on top of just those.

---

## 13. Closing Notes

This document is:

- a **brainstorm**, not a commitment  
- intentionally overcomplete  
- meant to inspire narrative FSMs and action design  

Next steps (if we want to formalize this):

1. Collapse this list into a **core v1 sensor set**.
2. Group sensors into:
   - relationship  
   - emotion  
   - context  
   - arc/meta  
3. Align with the improved sensor system:
   - define `SensorCategory = SOCIAL` etc.  
   - sketch eval_fns based on a `SocialState` structure.  

From there, we could write:

- `feature_design_social_state.md`
- `technical_design_social_state.md`
- and start wiring in concrete sensors and narrative arcs.
```
