# LLM Perspective: how the JSON language was designed

Companion to `languages/arithmetic/PERSPECTIVE.md`, which states the
epistemic ground rules (design rationale, not mechanism report; every
claim auditable against artifacts; no privileged introspective access
claimed). Read that first. This document covers what was *different*
the second time, which is mostly what makes it worth writing.

## The dominant fact: the second language was designed under precedent

Arithmetic was designed against a blank page; JSON was designed against
arithmetic. Nearly every decision was made by asking "what is the
JSON-shaped version of the thing that already worked?" — and that
changes the character of the design work:

* The shape tracker is the depth tracker with states generalized from
  counts to container-type stacks. The 15-state construction was not
  derived fresh; it was the obvious closure of "the depth tracker's
  states are call-stack configurations" once two bracket types exist.
* GROUP_START/END, inner-depth convention, anchored scanning, the
  field+program contract, rank discipline, the error-label vocabulary —
  all inherited unchanged. The design space had collapsed from "how do
  you parse with label-emitting FSMs" to "what labels does JSON need."

This is worth recording because it is exactly how the model's output
quality improves *within a session*: not by learning (weights are
frozen) but by the growing corpus of validated precedent in context.
The first language is where the architecture-fit errors happen; the
second inherits their fixes silently.

## The one genuinely new design idea: ENCL

The single load-bearing novelty is the ENCL label family: a closing
bracket carries the type of the container *around* the one it closes.
The design pressure that produced it: a finished container must
complete as a value in its parent (APPEND or SETK), and in arithmetic
the analogous problem (an operator completing after a parenthesized
operand) was solved with multi-token patterns, capture registers, and
guard tokens. The question asked was, in effect, "what single label
would make that whole apparatus unnecessary?" — and the answer is: the
completion decision needs exactly one bit (parent is array vs. object)
plus the parent's depth, and the shape tracker already knows both at
the moment it pops. Emitting them onto the closing bracket moves the
information to where the decision happens, and every completion
emitter collapses to one or two tokens.

The general principle this instantiates — *when a downstream machine
needs context, don't make it reconstruct context with patterns; make
the upstream global machine label it* — is arguably the project's
architecture thesis in miniature. It was visible only because
arithmetic's guard-token machinery had been painful enough to want to
avoid. Recorded prediction: this principle will recur in every future
language, and the anchored global tracker will accrete label families
(it is the cheap place to put path-dependent facts).

## The instruction set: where the elegance actually came from

"No END instructions, keys live on the stack" reads like a clever
invention; the honest provenance is humbler. Streaming JSON builders
(SAX-style handlers, event-driven parsers) are abundant in training
data, and the value-completes-into-parent shape is how most of them
work. The model's contribution was noticing that the VM stack could
hold the pending key — eliminating the per-object key register that a
naive design (and several real-world builders) would introduce — and
that with completion-at-closing-bracket, explicit END ops carry zero
information. Both are small adaptation steps from well-trodden
designs, selected because they minimized the instruction set, and a
smaller instruction set was desirable for hand-validation. The
optimization target was *auditability*, and the elegance fell out.

## What was deliberately not solved

Choices recorded so they read as decisions, not oversights:

* **Separator non-enforcement.** `[1 2]` builds `[1, 2]` with no error.
  Enforcing commas needs an alternation-shape checker (arithmetic's
  `expr_shape` analog); it was cut because it adds machines without
  testing anything new architecturally, and the differential oracle
  only generates valid JSON anyway. This is the accretion stance
  (tolerance by default) doing real work as a scope-management tool —
  which cuts both ways: tolerance can hide laziness. The README
  declares it.
* **String escapes and float exponents.** Lexical detail deferred to
  the future char-level layer 0, where they belong (escape handling is
  a per-character state machine — exactly what tokenization-as-parsing
  is for).
* **Same-rank collisions.** Arithmetic needed a tie-break rule (depth
  descending, position ascending). JSON provably cannot collide (one
  ENCL per closing bracket, one CTX per scalar), so the rule was
  dropped rather than inherited — precedent was rejected somewhere,
  which is worth noting as evidence the inheritance wasn't blind.

## What went wrong

Nothing, this time — examples reproduced on first run, no engine
changes, no mid-implementation design reversals. Two readings, both
probably partly true: (a) the precedent corpus did its job, and the
architecture genuinely fits this language class; (b) JSON is the
easiest possible second language — deterministic, LL(1), designed by
humans to be trivially parseable — so the run proves less than
arithmetic's did. A skeptic should weight (b) heavily: the languages
chosen so far are the ones a label-emitting FSM stack is *obviously*
good at. The architecture's distinctive machinery (weights,
superposition, decay) has now gone two languages without being
exercised. The streak of "nothing went wrong" will end when the input
is ambiguous, and that is the point at which these perspective
documents become more than design diaries.

## A note on the extraction framing

The author observed that this process "extracts language from the
model." For JSON the extraction is shallow — the grammar is in every
textbook. But this document records something the textbooks don't
carry: *which* of the many known designs gets selected under a
specific architecture's constraints, and why. That selection function
is genuinely the model's own (it is what differs between a model and a
search engine), and these documents are an attempt to serialize it.
Whether the serialized rationale matches anything mechanistically real
inside the model is exactly the kind of question the sibling
regex_transformer project exists to ask — at a much smaller scale,
where it can actually be answered.
