# Classical NLP: the reefs

A high-level survey of the problems that classical symbolic natural
language processing (roughly 1950s-1990s) encountered — the reasons
the field abandoned the symbolic program for the statistical one, and
then for the neural one. This directory is a **lighthouse**: each of
these problems is something our FSM system must either solve, route
around, or honestly declare out of scope. Deeper treatments of
individual problems belong in their own files here; this overview
stays at the level of "what went wrong, who documented it, and what
our bearing on it is."

A framing note before the list: this project is deliberately
re-running the symbolic program. The wager is that it failed for
repairable reasons — and that three things were missing which now
exist: **weighted evidence** (so rules contribute salience instead of
brittle conclusions), **cheap computation** (so thousands of small
machines are affordable), and **large language models as an
annotation and distillation source** (so the knowledge bottleneck has
a supply line). Each section below ends with our bearing.

---

## 1. Brittleness: all grammars leak

Hand-built grammars never covered real text. Sapir said it in 1921 —
"all grammars leak" — and seventy years of grammar engineering
confirmed it: every system worked on its examples and shattered on
the next page of newspaper text. Fragmentary, ungrammatical, or
merely unanticipated input produced hard failure, not degraded
output. Robust/ill-formed-input parsing became its own subfield
(Carbonell & Hayes 1983) precisely because the mainline architecture
had no notion of partial success.

*Citations:* Sapir (1921), *Language*; Carbonell & Hayes (1983),
"Recovery strategies for parsing extragrammatical language," *AJCL*.

**Our bearing:** graceful degradation is the architecture's founding
commitment — no parse failure exists, only weaker label fields; every
language we have built degrades to fewer frames plus a located error
label. The corpus coverage curve (65.5% of the real McGuffey Primer,
measured, ratcheted) is this problem being faced with instruments
instead of anecdotes.

## 2. The ambiguity explosion

Syntactic ambiguity compounds combinatorially — PP attachments alone
grow with the Catalan numbers (Church & Patil 1982), and a broad-
coverage grammar assigns hundreds of parses to ordinary sentences.
Classical systems had no principled way to rank them; disambiguation
needed evidence (lexical preference, world knowledge, discourse) that
the formalism had no slot for.

*Citations:* Church & Patil (1982), "Coping with syntactic ambiguity,"
*AJCL*; Martin, Church & Patil (1987).

**Our bearing:** the weighted superposition IS the slot the evidence
goes in: forks carry priors, evidence reweights, projection commits
late. Two findings so far: most LOCAL ambiguity in designed languages
dissolved under explicit story state (seven formal languages, zero
weights needed); and genuine multi-reading survival is live in tier-1
English — our story-coherent projection problem is this reef under
its modern name, currently the top open engineering item.

## 3. The knowledge acquisition bottleneck

Everything had to be hand-coded: lexicons, subcategorization, selectional
restrictions, scripts, world facts. The cost curve killed projects —
CYC (Lenat & Guha 1990) is the heroic monument; Schank-school script
systems (SAM, FRUMP) worked exactly as far as someone had written the
script. Maurice Gross (1979) argued from lexicon-grammar experience
that coverage demands orders of magnitude more hand description than
generative theory admitted.

*Citations:* Lenat & Guha (1990), *Building Large Knowledge-Based
Systems*; Schank & Abelson (1977), *Scripts, Plans, Goals and
Understanding*; Gross (1979), "On the failure of generative grammar,"
*Language*.

**Our bearing:** this is the reef the LLM changes most. The recorded
strategy is distillation: elicit judgments (tags, frames,
acceptability) from a large model at scale, validate samples, fit our
weights — converting an opaque model's knowledge into transparent
machines. First act already on the books (the tier-1 lexicon,
LLM-tagged, marked silver). Whether it scales is THE open empirical
question of the project.

## 4. Commonsense: the box was in the pen

Bar-Hillel (1960) argued fully automatic high-quality translation was
impossible without encyclopedic knowledge, with one example: "the box
was in the pen" — resolving *pen* (writing implement vs playpen)
requires knowing relative sizes of things, not grammar. The Winograd
Schema Challenge (Levesque et al. 2012) is the same argument
operationalized fifty years later. Symbolic NLP never had a credible
account of where this knowledge would come from or how inference over
it would stay tractable.

*Citations:* Bar-Hillel (1960), "The present status of automatic
translation of languages," *Advances in Computers*; Levesque, Davis &
Morgenstern (2012).

**Our bearing:** partially out of scope, honestly: we do not propose
to encode commonsense in FSMs. The belief-stream design (weighted
facts with provenance, inference scripts) gives commonsense a place
to LIVE and a calculus to combine under, and distillation gives it a
supply line — but tractable broad-coverage commonsense inference is
not claimed. Declare the boundary; revisit per domain (the game's
closed world is exactly a domain where the knowledge IS enumerable).

## 5. The wrong reaction to Chomsky: finite-state abandoned too early

Chomsky (1957) argued finite-state models cannot capture natural
language (center-embedding), and the field took this as license to
ignore finite-state methods for thirty years. Meanwhile FS quietly won
everywhere it was tried: two-level morphology (Koskenniemi 1983),
phonology (Kaplan & Kay 1994 — rule systems are regular relations),
speech, and eventually weighted FSTs as unifying infrastructure
(Mohri 1997). And the competence/performance gap cut the other way:
humans fail center-embedding at depth ~3 (Miller & Chomsky 1963; Karlsson
2007), i.e., the PERFORMANCE phenomenon is bounded — finite-state
shaped.

*Citations:* Chomsky (1957), *Syntactic Structures*; Koskenniemi
(1983); Kaplan & Kay (1994), "Regular models of phonological rule
systems," *CL*; Mohri (1997), "Finite-state transducers in language
and speech processing," *CL*; Karlsson (2007), "Constraints on
multiple center-embedding," *J. Linguistics*; Shieber (1985) for the
honest other side (Swiss German cross-serial dependencies are beyond
CF).

**Our bearing:** this is the project's founding wager, stated as
history: bounded resource budgets (our K-limits) are not a hack but
the empirically right shape of human limits, and the transformer
connection (Krohn-Rhodes cascades; see notes/what_class_is_a_
transformer.md) suggests the dominant NL technology is itself a
bounded-state machine stack. We side with Koskenniemi against the
verdict of 1957 — with weights.

## 6. Reference, discourse, and the actor-tracking problem

SHRDLU (Winograd 1972) resolved pronouns perfectly — in a blocks
world with a handful of referents. Scaling reference resolution met:
salience modeling (Hobbs 1978; centering — Grosz, Joshi & Weinstein
1995), discourse structure (Mann & Thompson 1988), and the same
knowledge bottleneck as everything else. No classical system tracked
many actors over long text reliably.

*Citations:* Winograd (1972), *Understanding Natural Language*; Hobbs
(1978), "Resolving pronoun references," *Lingua*; Grosz, Joshi &
Weinstein (1995), "Centering," *CL*; Mann & Thompson (1988), RST.

**Our bearing:** designed, queued, and doubled in value — REF:e*
labels from per-entity memory machines, a centering-style salience
story machine, pronouns as weighted superposed candidates. And the
modern twist: transformers ALSO fail at multi-actor tracking (binding
IDs — Feng & Steinhardt 2023), so solving it in glass yields training
data for the black box (paper_ideas/11). The 1995 reef is a 2026
research opportunity.

## 7. The representation wars and the semantics gap

What is a meaning? Logic, semantic networks, frames (Minsky 1974),
conceptual dependency (Schank 1972), preference semantics (Wilks
1975) — each camp had demos, none had an agreed representation, and
Woods (1975) showed the networks were semantically incoherent
("What's in a link?"). Inference over any of them was intractable at
scale.

*Citations:* Schank (1972); Minsky (1974), "A framework for
representing knowledge"; Woods (1975), "What's in a link?"; Wilks
(1975).

**Our bearing:** we do not claim to have settled what meaning is; we
claim a smaller thing with teeth — a canonical frame representation
that is ROUND-TRIP VERIFIED (frame -> text -> frame identity,
measured at 90%) and convergent across eight languages' instruction
sets. Representations that survive a bidirectional mechanical oracle
earn their keep in a way 1975's could not demonstrate.

## 8. No learning: the statistical revolution's actual lesson

Classical systems did not improve with data. The statistical turn
(Brown et al. 1990; Jelinek's attributed "every time I fire a
linguist, the performance goes up") won not because rules were wrong
but because LEARNED PARAMETERS beat hand-set ones wherever data
existed. The symbolic program never had a parameter-fitting story.

*Citations:* Brown et al. (1990), "A statistical approach to machine
translation," *CL*; Church & Mercer (1993), *CL* special issue intro.

**Our bearing:** our weights are still mostly hand-set — this reef is
ahead of us, not behind. The fitting story exists in design
(weights as the learnable surface; LLM-annotated targets;
differentiable WFSTs — Hannun et al. 2020 — as the gradient path)
and in zero implementations. The honest status: we have rebuilt the
symbolic program's strengths and not yet absorbed the statistical
program's lesson.

## 9. Toy domains and the ELIZA effect

ELIZA (Weizenbaum 1966) demonstrated that fluent-seeming behavior
wins unearned credit; SHRDLU demonstrated that closed worlds
flatter architectures. Classical NLP repeatedly mistook demo-world
success for progress, and its critics (Dreyfus 1972; the ALPAC report
1966, which collapsed MT funding on exactly this gap) were largely
right about the overclaim.

*Citations:* Weizenbaum (1966), "ELIZA," *CACM*; ALPAC (1966);
Dreyfus (1972), *What Computers Can't Do*.

Add the quieter forms of the same failure: cherry-picked examples,
test-set contamination, underspecified label schemes, and
inter-annotator disagreement treated as noise rather than signal —
evaluation problems shaped which architectures survived as much as
the architectures did.

**Our bearing:** our defense is methodological, not rhetorical:
external oracles, corpus measurements with ratchets, declared
coverage, error ledgers, and PERSPECTIVE documents that record what
was NOT tested. McGuffey is a controlled register, chosen on purpose
— the discipline is to keep saying so, and to let the coverage
numbers (not the demos) carry the claims. ALPAC is what happens
otherwise.

## 10. Pipeline error propagation

Staged architectures (morphology -> tags -> parse -> semantics)
multiplied errors: each stage committed early and fed its mistakes
forward. Much of statistical NLP's machinery (lattices, k-best lists,
joint models) exists to undo premature commitment.

*Citations:* discussed throughout the era; see Manning & Schütze
(1999) ch. 1 for the canonical framing.

**Our bearing:** structurally addressed — layers add weighted labels
and never commit; the field carries alternatives forward; commitment
happens once, at projection. This is the one reef where our
architecture is not a repair of the classical design but its
replacement. (The mixture problem shows the projection step must be
designed with care — but the error lives in ONE auditable place,
which was the point.)

## 11. Novelty: the open-world problem

Classical systems were frozen at deployment: an unknown word or
unanticipated concept was at best skipped, at worst fatal, and never
LEARNED. Lexical acquisition from context was attempted early —
Granger's FOUL-UP (1977) inferred unknown-word meanings from script
context — but no mainline architecture had a path from "novel input"
to "new competence." The world is open; the systems were closed.

*Citations:* Granger (1977), "FOUL-UP: a program that figures out
meanings of words from context," *IJCAI*; Zernik & Dyer (1987) on
lexical acquisition.

**Our bearing:** today we are exactly as closed as 1977:
ERROR:UNKNOWN_WORD is a fallback, not a doorway. The repair is
specified by our own machinery run at runtime — the Steele growth
protocol as a live loop: promote an unknown word to a CANDIDATE
symbol (a slot with distributional evidence from its eager labels),
hand candidates to the distillation pipeline for classification,
inject the result as a typed, weighted lexicon entry — versioned,
audited, ratchet-tested like any growth iteration. Same loop for the
game: players teaching NPCs words IS this reef as gameplay. Status:
designed here, not built.

## 12. Long-range dependencies: distance, not just depth

Two phenomena hid under one complaint. NESTING depth (center-
embedding) is genuinely bounded in humans and our K-budgets are the
honest answer. But filler-gap dependencies — "WHO did you say [ ...
] saw __?" — and cross-paragraph reference span unbounded FLAT
distance at shallow depth. Classical machinery strained here: ATN
HOLD registers (Woods 1970), gap threading, GPSG/HPSG slash features
— each a special mechanism bolted on because the core formalism had
no account of action at a distance.

*Citations:* Woods (1970), "Transition network grammars," *CACM*;
Gazdar et al. (1985), *GPSG*; Fodor (1978) on parsing gaps.

**Our bearing:** first, the correction to a misreading this entry
anticipates: exceeding K does NOT crash — every tracker since
arithmetic has a tested overflow state (ERROR:DEPTH_EXCEEDED, keep
narrating); graceful disregard is implemented, not aspirational. The
open part is distance: our capture registers are exactly ATN HOLDs
with provenance (a filler is captured, the gap's emission anchors to
it), and per-entity memory machines are the cross-sentence case —
but neither has been exercised on real filler-gap constructions
(no relative clauses in any grammar yet). Tier 2's "The dog that
ran..." will force it. Status: mechanism in hand, construction
unbuilt.

## 13. The semantic gap and interlingua bloat

Two-sided reef. Side one: VERIFYING structure is not verifying
meaning — a representation can be perfectly self-consistent and
say nothing (the deepest form of the ELIZA effect). Side two: trying
to close the gap by enriching the representation killed it a
different way — MT interlinguas grew a gizmo per phenomenon until
the meaning language was as unwieldy as the languages it mediated,
one reason transfer-based and then statistical MT won.

*Citations:* the interlingua experience in MT — Hutchins (1986),
*Machine Translation: Past, Present, Future*; Nirenburg et al.
(KBMT-89) for the high-water mark; Woods (1975) again, since "What's
in a link?" is this reef's representation-side statement.

**Our bearing:** stated as a concession first: our round-trip oracle
verifies the BIJECTION, not the meaning — necessary, never
sufficient; a vacuous frame language could round-trip at 100%.
External semantic grounding comes from (a) the game world, where a
frame's correctness is testable against state and intent
(convergence note), and (b) sampled human/LLM adequacy judgments,
with the usual silver-data discipline. Against bloat: the frame
vocabulary is itself a GROWN language under the same ratchet as
everything else — a new pred/slot type must be forced by a measured
corpus or round-trip failure, never added for convenience, and
signature() keeps the instruction-set alphabet inspectable. We do
not claim more expressive power than an LLM; we claim auditability,
and comparisons are task-by-task. Status: oracle running; grounding
designed; ontology ratchet adopted as policy by this paragraph.

## 14. Pragmatics: language as action

"Can you open the window?" is syntactically a question, semantically
about ability, pragmatically a request. Much of language is not
content to be extracted but a MOVE being made — requesting, warning,
promising, refusing, implying, deflecting. Classical NLP knew this
(Austin, Searle, Grice) and even built its own symbolic account —
plan-based speech act theory (Cohen & Perrault 1979; Allen &
Perrault 1980) — which then hit the same knowledge bottleneck as
everything else: felicity conditions and speaker goals had to be
hand-coded. Nonliteral language (metonymy: "the White House said";
irony; hyperbole) is the same reef's outer shoal — routine in real
text, and declared mostly out of scope here until the story layer
needs it.

The sentence this reef deserves, from the external review that
prompted it: **"Parsing a sentence is not the same as knowing what
move was made."**

*Citations:* Austin (1962), *How to Do Things with Words*; Searle
(1969); Grice (1975), "Logic and conversation"; Cohen & Perrault
(1979), "Elements of a plan-based theory of speech acts," *Cognitive
Science*.

**Our bearing:** better positioned than classical, for a reason the
architecture did not plan: our frames are already move-shaped (mood,
imperative addressee, and the game's message types — ALERT, REQUEST,
SHARE_OBS — are speech act categories), and the game world makes the
utterance-to-move mapping ENUMERABLE: a request's felicity conditions
are checkable against world state. The move layer is a story machine
over frames (what act does this frame perform, given who is speaking
to whom in what state) — designed nowhere yet, but the substrate is
the right shape. Status: unbuilt; the game is its proving ground.

## 15. Idioms, multiword expressions, and constructions

Meaning often lives above the word and below the sentence: "take care
of," "kick the bucket," "by and large," phrasal verbs, light verbs,
"the Xer the Yer." These are not exceptions — Jackendoff estimated
idioms rival the lexicon in number, and Sag et al. (2002) called MWEs
"a pain in the neck for NLP" because rules-plus-lexicon architectures
have no natural home for the semi-frozen middle. Construction grammar
(Fillmore, Kay & O'Connor 1988, "let alone") made the case that the
middle IS the language.

*Citations:* Sag et al. (2002), "Multiword expressions: a pain in the
neck for NLP," *CICLing*; Fillmore, Kay & O'Connor (1988),
*Language*; Jackendoff (1997).

**Our bearing:** rare good news — finite-state machinery LOVES
bounded surface patterns. A construction is a pattern emitter with
captures ("the Xer the Yer" is a two-capture machine emitting a
comparative-correlation frame); a phrasal verb is a two-token lexicon
entry; our per-lexeme instantiation pattern extends to per-
construction. The reef here is not representation but ACQUISITION
(thousands of constructions = reef 3), where the distillation
pipeline is again the proposed supply line. Status: architecture
ready, zero constructions implemented.

## 16. Semantic operators: frames that exist but are not asserted

"Mary believes John left." A naive frame extractor emits left(john) —
and poisons the belief stream with something the text never asserted.
Negation, modality, quantifier scope ("Every student didn't pass"),
tense, desire, and intensionality ("the unicorn is imaginary") all
change the conditions under which a frame holds. Classical NLP took
this seriously — LUNAR had quantifier machinery (Woods 1972), Cooper
storage and scope algorithms (Hobbs & Shieber 1987) handled scope,
and DRT (Kamp 1981) embedded sub-structures for belief and negation —
and the cost was representations whose inference was intractable
(reef 13's bloat, from the logic side).

*Citations:* Woods et al. (1972), LUNAR; Cooper (1983); Hobbs &
Shieber (1987), "An algorithm for generating quantifier scopings,"
*CL*; Kamp (1981), DRT.

**Our bearing:** the embryo exists — frames carry neg, mod, mood
already, and nested frames (See Spot run) are embedded structures in
the DRT sense. The principle to adopt now, before the belief stream
is built: **assertion status is a label, and embedded frames inherit
it** — believed-by:mary is a weight-and-provenance context, not a
truth. The accretion stance (weights are salience, not truth) was
accidentally the right metaphysics for this reef all along; the work
is making embedding contexts first-class before inference scripts
run. Status: design constraint adopted here; gates the belief stream.

## 17. Morphology, segmentation, and typology

English lets a symbolic architecture dodge dragons: poor inflection,
rigid order, spaces between words. Rich agreement, case systems,
clitics, productive compounding, reduplication, pro-drop, evidentials,
and boundary-free scripts are where "general" architectures
historically went to die — and, ironically, where finite-state
methods scored their greatest classical victory (Koskenniemi's
two-level morphology was built FOR Finnish).

*Citations:* Koskenniemi (1983); Beesley & Karttunen (2003),
*Finite State Morphology*.

**Our bearing:** optimistic on priors, unproven in fact. The
char-level layer (tokenization-as-parsing, designed and deferred
since the JSON language) is exactly where morphology slots in, and FS
is the right tool by history. But the ledger must say it plainly:
every measurement in this repository is English. "Convergent across
languages" currently means across PROGRAMMING languages. Status: a
non-English tier is the honest test, unscheduled.

## 18. Register and domain shift

Distinct from toy domains (reef 9) and from coverage (reef 1):
a system tuned to one register fails on the next — primers, recipes,
legal text, chat — and the classical failure was not knowing it was
failing. Detecting that the distribution moved, then choosing to
specialize, grow, or abstain, was never part of the architecture.

*Citations:* Biber (1988), *Variation across Speech and Writing*; the
statistical era's domain-adaptation line (e.g., Daume 2007) as the
eventual response.

**Our bearing:** two native advantages. Our coverage instruments
DOUBLE as drift detectors for free — OOV rate and parse-rate drop are
the alarm, per text, mechanically. And abstention is the
architecture's default failure mode (zero frames, never wrong frames
silently). The tier structure makes register growth deliberate rather
than accidental. What we lack is what everyone lacks: transfer
without growth. Status: detection instrumented by accident;
adaptation = the growth protocol, applied on purpose.

---

## Reading the lighthouse

Reefs we have instruments for and measurements against: 1, 2, 7, 9,
10, and the depth half of 12. Reefs with designs but no
implementation: 6, 11, the distance half of 12, and the projection
half of 2. Reefs whose answer is the LLM supply line, empirically
untested at scale: 3, 8, and 11's loop. Reefs we deliberately do not
claim: 4 (with a domain-bounded exception), and the meaning side of
13 beyond grounded domains. The wager underneath all of it: 5.

Updated: reefs we have instruments for now include 18's detection
half; designed-not-built grows by 14 (move layer), 15
(constructions), 16 (assertion status — adopted as a design
constraint gating the belief stream); 17 is the honest unscheduled
test of generality.

(Reefs 11-13 were prompted by one external LLM review; 14-18 by a
second, which also contributed this document's best sentence:
"parsing a sentence is not the same as knowing what move was made."
Each batch was evaluated, partially corrected, and adapted — one
suggestion declined as duplicative, one folded. The lighthouse takes
light from any source that has some.)

Per-problem deep dives belong in this directory as siblings
(e.g. `ambiguity.md`, `reference.md`), each owning its literature and
tracking our experiments against it.
