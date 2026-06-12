# LLM Perspective: how the JavaScript subset was designed

Sixth in the series; ground rules in
`languages/arithmetic/PERSPECTIVE.md`.

## The design was forced, and that is the finding

The author chose this language for one feature: `/` as division vs
regex literal. Working the design, there turned out to be essentially
one architecture-compatible solution, and every piece of it was
already on the shelf:

* The disambiguation state is *literally* the minus story's
  expectation bit — the JS specification's own lexer rule ("a slash in
  expression position starts a regex") is the operand-done story told
  about a different token. Adding one state (in_regex) makes it a
  3-state machine.
* The new problem — story state determines token BOUNDARIES, not just
  token classes — forced retokenization: tokenize naively, narrate,
  then merge. Synthesized slots (pysub) and provenance edges (in the
  slot model since v2, never used) were exactly the needed mechanism.
  This is the second consecutive language where the new feature was
  implemented largely from parts built before it was conceived.
* Pipeline ORDER did the rest: slash story and retokenization run
  before the bracket tracker, so mis-lexed parens inside regex bodies
  never corrupt structure tracking. No defensive logic anywhere —
  just sequencing. (Layering as the architecture's answer to
  context-sensitivity is probably the generalizable lesson.)

## OPERAND_END: the story-event vocabulary arrives, and immediately
## exposes a debt

The slash story keys on an explicit OPERAND_END label emitted by the
adapter — the first tier-1 story event used by name (the three-tier
factoring from notes/story_machines.md). The retokenizer marks merged
REGEX slots OPERAND_END, and the slash story consumes that without
knowing what a regex is.

imp's imported minus story, designed before the event vocabulary
existed, keys on token classes (NUM/IDENT/RPAREN) — and therefore
cannot learn that REGEX completes an operand. `/a/ - 2` mislabels the
minus; the run goes invalid (pinned by test). The asymmetry within one
language — new story machine extensible by adapters, old one not — is
the cleanest possible argument for the event-vocabulary refactor, made
by a working counterexample rather than by design-document reasoning.
The refactor is recorded, deliberately not done here: it touches a
machine three languages share, and shared machinery should change in
its own commit with all three languages' suites as the gate.

## The differential oracle choice

Real JS (node) was considered and rejected: availability is
environmental, and the regex-free fragment of jssub is definitionally
imp — so the strongest *reliable* oracle is imp itself, same source
through both pipelines, outputs and environments equal. This makes the
differential a statement about the new machinery specifically: the
naive-lex + slash-story + retokenize path is observationally identical
to direct lexing wherever both are defined. The regex behavior rests
on golden tests, including the same-characters-opposite-tokenizations
pair (`x * 2 / 2` vs `/x*2/`), which is the language's whole point in
two lines.

## What went wrong

Nothing during implementation — all seven worked examples reproduced
on the first run, and the differential found no disagreements. By the
established pattern (JSON's PERSPECTIVE), this warrants suspicion
rather than celebration: the design was maximally constrained by
precedent, which is exactly when first-run success is least
informative. The one genuine unknown was whether retokenization would
compose with downstream machinery built for 1:1 token streams; it did,
because nothing downstream ever assumed slots were text (the slot
model's discipline paying off silently).

## The skeptic's ledger

Six languages; the weighted machinery is still idle, and the slash
"ambiguity" — like minus — dissolved under one bit of story state
(most apparent ambiguity is story-state poverty, again confirmed,
still never refuted). The formal series has now covered: expressions,
data, symbols, statements/scopes, layout, and context-sensitive
tokenization. The reuse curve across the series is the headline
metric: jssub imported six machine layers and wrote three new
components. If a seventh formal language is contemplated, the bar it
must clear is teaching something none of the six did — otherwise the
two standing experiments (competing stories with weights; the
regex_transformer probe) are strictly higher-value, and both have had
all prerequisites in place since pysub.
