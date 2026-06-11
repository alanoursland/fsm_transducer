# LLM Perspective: how the S-expression language was designed

Third in the series; epistemic ground rules in
`languages/arithmetic/PERSPECTIVE.md` (rationale, not mechanism;
everything auditable; no privileged introspection claimed).

## The brief was different this time

Arithmetic and JSON were chosen by the model and ratified by the
author. S-expressions were the author's call, with a stated purpose:
"tests recursive symbolic structure with very simple tokenization."
The design work was therefore not "find a language" but "find what in
this language would teach the architecture something" — and the honest
first answer was: structurally, nothing. A single bracket type makes
the tracker *simpler* than JSON's; uniform APPEND completion makes the
emitters simpler; three instructions suffice. Designed minimally,
sexpr would have been a strict subset of JSON's machinery and the
golden suite would have verified nothing new.

The design response was to add the HEAD/ARG role distinction — not
because building lists requires it (it doesn't; the builder ignores
roles entirely) but because it is the smallest feature that makes this
language a step *toward* the project's target rather than a third lap
of the same track. That decision shaped everything else.

## Why roles, specifically

Three reasons, in decreasing order of confidence that they were the
operative ones:

1. **It extends a visible progression.** Arithmetic's tracker counts;
   JSON's tracks container type; the natural next increment was
   tracking *expectation* — one bit per open list for "is the head
   still pending." The stack-alphabet generalization {unary} → {O,A} →
   {F,R} was already a pattern in context; sexpr's design mostly
   consisted of noticing the pattern admitted another instance.
2. **Head/argument structure is the bridge to natural language.**
   ROLE:HEAD/ROLE:ARG on list elements is structurally the same family
   as predicate/argument labels on clause constituents — the thing the
   project's NLP grammars gesture at with SUBJECT_CANDIDATE. Getting a
   grammatical-relation family validated on a language where it is
   *unambiguous and mechanically checkable* stages the machinery for
   the case where it is neither.
3. **Lisp's own self-description.** Training data is saturated with
   "the car is the operator, the cdr is the arguments." The
   head-position concept didn't need inventing, only relabeling into
   the project's family conventions.

A fourth candidate reason — that roles make the worked examples more
interesting to validate — is probably also true and probably did
influence the design; spec-writing under this methodology rewards
features that produce assertable labels.

## Decisions worth recording

* **Roles on the opening paren of sublists.** A sublist-as-element's
  role had to land somewhere; its `(` is the only token that exists at
  the moment the role is known. Consistent with the project's existing
  convention that bracket tokens carry the inner depth — they are
  already "about" the group, so they can be about its role too. The
  alternative (a span-wide role label on every interior token) was
  rejected as redundant: downstream consumers can read the span from
  GROUP_START/END.
* **The F→R flip lives in the tracker, not in patterns.** This is the
  ENCL principle from JSON's PERSPECTIVE applied prospectively: the
  role decision needs path-dependent context (has this list seen an
  element yet?), so it goes in the anchored global machine, and the
  per-depth emitters stay context-free. First language designed with
  that principle stated in advance rather than discovered under
  pressure — the predicted accretion of label families onto the
  tracker is happening.
* **Sequence-of-forms output contract.** A Lisp file is a sequence of
  forms; forcing a single document would have falsified the domain to
  fit the precedent. Generalizing validity ("stack nonempty") was
  cheap and produced the best degradation shape so far: `(a (b` leaves
  two correctly built fragments, with the missing splice visible as
  stack depth.
* **No evaluation.** `(+ 1 2)` builds a list; it does not compute 3.
  Tempting (the arithmetic VM is *right there*), and rejected: the
  parser's output contract is structure, evaluation is a downstream
  consumer, and blurring that line would undo the cleanest separation
  the project has. This was the only decision that felt like resisting
  an attractive wrong answer rather than selecting among neutral ones.

## What went wrong

One error, and it was in the *test*, not the design or the runner: a
golden assertion indexed `x` in `((f) x)` as token:5 (it is token:4 —
token:5 is the closing paren). Trivial, but worth recording for the
pattern ledger: it is the same error class as both arithmetic design
errors — off-by-one reasoning over token positions done in prose
rather than by stepping through the input. Across three languages,
every model-introduced error has been positional/quantificational; none
have been conceptual. That regularity is itself a finding about what
kind of collaborator a language model is in this methodology: trust the
architecture-level reasoning, mechanically verify anything with an
index in it.

## The skeptic's ledger, updated

JSON's PERSPECTIVE predicted the "nothing went wrong" streak ends when
ambiguity arrives. Sexpr does not test ambiguity either — by
construction it is the *least* ambiguous language imaginable — so the
prediction stands unfalsified and the distinctive machinery (weights,
superposition, decay) is now three languages idle. What sexpr *did*
add to the evidence base: the tracker-generalization pattern held a
third time, the ENCL principle transferred prospectively, and the
format absorbed a different output contract (sequences) without
strain. The architecture keeps being the right size for regular
structure. The open question is unchanged and is now overdue: a
language where two readings compete and the weights must decide.
