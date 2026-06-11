# Story Machines

A naming note. The architecture has been building the same kind of
machine in every language without giving it a name; the author's
framing — "an FSM of a story" — is the right name, and adopting it
reorganizes both the ambiguity roadmap and the path to natural
language.

## The observation that triggered this

Unary vs. binary minus (`x - 3` vs. `print(-3)`) looks like ambiguity
and is not: it needs exactly one bit of left context — *is there a
completed operand to my left?* An anchored tracker carrying an
expectation state {expect-operand, expect-operator} resolves every
minus deterministically and emits `MINUS:UNARY` / `MINUS:BINARY`
labels for the emitters to key off. No weights required.

The general lesson: **most apparent ambiguity is story-state
poverty.** A symbol looks ambiguous to a machine that has forgotten
where it is in the narrative. The first move on any "ambiguous"
construction is to ask what story state would disambiguate it; weights
are for what remains after that move.

## What the anchored trackers have actually been tracking

| language | tracker state | narrative reading |
|---|---|---|
| arithmetic | nesting depth | *where we are* |
| json | container-kind stack {O, A} | *what we're inside* |
| sexpr | expectation stack {head-pending, in-body} | *what comes next* |
| imp (scope) | declared-bit stack per identifier | *who has been introduced* |
| (minus, planned) | {expect-operand, expect-operator} | *what the last event was* |

Where-we-are, what-we're-inside, what-comes-next, who's-on-stage, what
just happened: these are the state variables of a **story**, not of a
phrase-structure grammar. The anchored machine is the reader's running
model of the discourse; the per-depth/per-name pattern emitters are
reflexes that consult it. The ENCL principle from the JSON design
("when a downstream machine needs context, have the upstream global
machine label it") is, in this vocabulary: *the story machine narrates;
everyone else reads the narration.*

This is not a new idea in cognitive science, which is reassuring
rather than deflating: Propp's morphology of folktales is a
finite-state grammar over narrative functions; Schank's scripts are
expectation structures; Rumelhart-era story grammars are literally
FSMs of stories. The architecture arrived at the same organization
from the engineering side — global expectation state, locally
consulted.

## Consequences

**1. A vocabulary correction.** "Anchored tracker" describes the
mechanism; "story machine" describes the role. Specs should say what
story a tracker is telling (its state variables in narrative terms),
because that is what a future language designer needs to know to
extend it.

**2. The ambiguity roadmap, rewritten.** True ambiguity — the thing
the weighted machinery exists for — is **two stories live at once**,
not two readings of a token. A garden-path sentence forks the story
machine: both narrative states persist as weighted paths (the engine
already supports nondeterministic anchored machines with semiring
merging), both emit their expectation labels into the shared bag, and
later evidence reweights or kills one. The long-promised first
ambiguity experiment should therefore be designed as *competing
narrative states with explicit fork and death points*, not as a
lexicon with ambiguous entries. Concretely, the minimal version:

* a story machine with a genuine fork (two states consistent with the
  prefix), emitting superposed expectation labels with weights;
* an input where the fork survives several tokens before one branch
  dies (so decay and reweighting are observable in the trace);
* a golden test asserting the label-field trajectory: superposition,
  then collapse, with the losing story's labels decaying rather than
  being retracted — the accretion thesis, finally exercised.

Garden-path arithmetic exists (`1 - - 2`, or C-style cast/multiply
puns), but natural-language fragments are the honest target; even a
five-word grammar with one attachment ambiguity would do.

**3. Minus goes back in.** Arithmetic v2 (or imp v2) should add unary
minus with an expectation-state story machine — not because it is hard
but because it is the cleanest worked example of "ambiguity dissolved
by story state," the control condition against which real ambiguity
experiments will be compared.

**4. The NL bridge gets more specific.** The plan's lexicalized
factoring (per-lexeme machines, after imp's per-identifier checkers)
covers the *reflex* layer. The story-machine layer is discourse state:
referents introduced (imp's scope checkers are literally a
who's-on-stage tracker), open expectations (a verb whose argument
hasn't arrived is sexpr's head-pending bit), embedding (depth). The
architecture's claim about NL, restated in this vocabulary: a sentence
is parsed by reflexes consulting a story, and *understanding degrades
gracefully because the story machine keeps narrating even when a
reflex finds nothing to fire on.*

## Caveat

The framing is generative but not free: story machines are still
finite. A story with unboundedly many simultaneously-open expectations
(center-embedding, again) exceeds any fixed machine — the K-budget
honesty from the language work carries over unchanged. The claim is
not that stories are regular; it is that a bounded story budget is the
right *shape* of bound (humans appear to have one too), and that the
budget should be spent on narrative state variables rather than on
phrase structure.

## Addendum: stories are syntax-invariant (the interlingua claim)

A second observation from the author sharpens the framing: **the
imperative and declarative can share the same story.**

```text
(print - 3)      ; sexpr
print(-3);       // imp
```

Different token order, different brackets, different grammar — same
story: *an action is being applied; its operand position just opened;
minus begins something.* Whereas, within one language:

```text
y = x - 3;       // a different story: a referent is being bound;
                 // an operand completed; minus continues something
print(x - 3);    // outer story = application (like print(-3));
                 // inner story = expression (like y = x - 3)
```

The third example shows stories *compose*: the narrative state is a
stack of frames (application, binding, expression), each with its own
expectation state. Which frame you are in and where you are within it
are separate coordinates.

### The evidence was already in the repo

The four languages' instruction sets converged without that being a
design goal: NEW_LIST / NEW_OBJ / NEW_ARR are all "a container opens";
APPEND / SETK / DECL are all "an element completes into its frame";
PUSH is "an entity enters the stage." The instruction streams were
never describing syntax — they were serializing the story. Convergence
that falls out rather than being designed in is the strongest kind of
evidence the abstraction is real.

### The three-tier factoring this implies

1. **Syntax adapters** (per language): lexicon + a thin tracker
   translating surface tokens into *story events* as labels —
   FRAME_OPEN:application, OPERAND_DONE, REFERENT_INTRODUCED,
   FRAME_CLOSE, ...
2. **One shared story machine**: consumes story-event labels,
   maintains the narrative stack (frame kind x expectation), emits
   story-state labels (EXPECT:OPERAND, IN:binding, ...). The same FSM
   for every language whose adapter speaks the event vocabulary.
3. **Shared semantic emitters**: written once against story-state
   labels. Unary-vs-binary minus becomes a single rule that works in
   imp and sexpr alike.

### The falsification experiment (cheap, sharp)

Implement unary minus in BOTH imp and sexpr with literally the same
story machine — one file, imported by both runners; only the adapters
differ. If each language turns out to need private story states, the
interlingua claim is wrong and the failure will show exactly where
syntax leaks into story. If it works, tier 2 is real and every future
language gets minus (and everything else written against story state)
for the price of an adapter.

### What this is and is not

It rhymes with "deep structure" but is not a tree — it is *process
state*, which places it nearer the psycholinguistics of situation
models (event-indexing: readers track time, space, causation,
protagonist; readers of a text and its translation converge on the
same situation model despite disjoint syntax). "The imperative and
declarative share the same story" is that finding, adopted as an
architecture decision.
