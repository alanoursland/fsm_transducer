# Linguistic phenomena handled by mcguffey1b

A complete catalog of the grammatical and semantic problems the
`mcguffey1b` layer solves, with the classical-NLP account of each, the
construction it rejects, and how the solution is implemented.

This is the *reference*; the narrative of how these were discovered
(through generated-text audits and corpus round-trips) is in
`MCGUFFEY1B.md`, and the rule data lives in `features.yaml`.

## How to read this

`mcguffey1b` is a single declarative layer over the `mcguffey1`
syntactic parser. It reads the projected **frame** (a predicate-argument
structure: `pred`, `agent`, `theme`, `attr`, `mod`, `neg`, `mood`, `wh`,
and surface-preposition keys) and emits **violation codes**; any code
means the parse is rejected (`parse() -> None`) and, in generation, the
candidate is vetoed. Every check is one of two kinds:

- **Frame-level** (`violations()` / `critique()`): reads only the frame.
- **Surface-level** (`*_violations(text, frames)`): also reads the token
  stream, needed when the parser *absorbs* a function word (articles,
  do-support) so the distinction is invisible in the frame.

All checks are verified to leave real-corpus coverage at **140/144** of
what `mcguffey1` parses (the four it drops are upstream parser quirks,
not rule failures — see the ledger in `MCGUFFEY1B.md`).

Rule data (`features.yaml`) is an overlay; `lexicon.yaml` is untouched,
so `mcguffey1` parses byte-for-byte as before.

---

## 1. Valency / subcategorization

**Classical account.** Tesnière (1959) — verbs have a *valence*, a fixed
number of obligatory arguments. Fillmore (1968) — case frames specify
which roles a predicate requires. Levin (1993) — verb classes with
shared argument structure.

| Construction rejected | Code | Rule |
|---|---|---|
| `Loves.` — transitive with no object | `VAL:THEME_REQUIRED` | verbs in `transitive` require a `theme` (finite clauses) |
| `Schoolhouse eat` given a theme; `Snow sheep` | `VAL:NO_THEME` | verbs in `intransitive` forbid a `theme` |
| `Made Dick have?` — main-verb *have* with no complement | `VAL:HAVE_NEEDS_COMPLEMENT` | *have/has/had* needs a following participle (perfect aux) or NP (object); **surface-checked**, because perfect-*have* and possessive-*have* collapse at frame level |
| `Did of Nat on slates?` — stranded auxiliary | `VAL:DO_STRANDED` | do-support (Chomsky 1957): *do/does/did* surfacing as the predicate means it failed to attach to a lexical verb; needs a theme to be a main-verb *do* |
| `Put God.` — missing locative | `VAL:PUT_NEEDS_LOCATION` | put-class verbs (Levin 9.1) obligatorily take a directional/locative PP |
| `Snow sheep in eggs.` | (via `intransitive`) | weather verbs are **avalent** (Tesnière): no thematic agent or object |

Notes: the to-infinitive/preposition ambiguity is a known chestnut — a
V-tagged `to`-complement satisfies a transitive ("likes to ride"), and a
V-tagged "theme" of an intransitive is read as a purpose infinitive, so
those do not false-fire. Embedded (nonfinite) clauses skip
`THEME_REQUIRED` because the parser cannot reliably attach embedded
objects yet.

## 2. Selectional restrictions

**Classical account.** Katz & Fodor (1963) — semantic markers (`+ANIMATE`
etc.) that predicates require of their arguments. Wilks (1975) —
*preference* semantics: restrictions are soft, relaxable per predicate,
not a hard type system.

| Construction rejected | Code | Rule |
|---|---|---|
| `Schoolhouse eat.` — inanimate agent of an agentive verb | `SEL:ANIMATE_AGENT` | agentive verbs (those *not* in `agent_any`) require a `+ANIMATE` agent |
| `Drown eyes for hands.` — non-living patient | `SEL:ANIMATE_THEME` | `theme_animate` verbs (drown/kill/feed/pet/save — Levin verbs of killing/caring) require a `+ANIMATE` theme |

Relaxations are per-verb (`agent_any` for weather/unaccusative/stative
predicates like *fall, snow, have*), Wilks-style preference rather than
Montague-style typing.

## 3. Agreement and verb form

**Classical account.** GPSG / HPSG feature checking — subject and verb
must unify on person/number features. Done here on the projected frame
rather than by unification.

| Construction rejected | Code | Rule |
|---|---|---|
| `They runs` — 3sg verb, non-3sg subject | `AGR:3SG_NEEDS_SG_SUBJ` | a `form_3sg` verb needs a 3rd-person-singular subject |
| `The cat run` — base verb, 3sg subject | `AGR:SG_SUBJ_NEEDS_3SG` | a `base` verb forbids a 3sg subject (finite, non-imperative) |
| `is` with a plural subject | `AGR:COP_SG` | *is/was* require a singular subject |
| `are` with a singular subject | `AGR:COP_PL` | *are/were* require a plural subject |
| `Walks John watch.` — non-base imperative | `VFORM:BASE_REQUIRED` | modals/do-support and imperatives govern the base form |
| `Seen horse show.` — participle as matrix verb | `VFORM:PARTICIPLE_MATRIX` | a participle cannot stand as the finite matrix predicate (without a perfect auxiliary) |

Person vs. number: `no_3sg` (*I, you, we, they, who*…) take the base
form despite being singular-ish — this is person, not number.

## 4. Case (nominative / accusative)

**Classical account.** Morphological case; structural case assignment.
A matrix subject is nominative; objects and prepositional objects are
accusative; the subject of an ECM complement is accusative, assigned by
the higher verb (**exceptional case marking**).

| Construction rejected | Code | Rule |
|---|---|---|
| `Me ran.` — accusative matrix subject | `CASE:NOM_SUBJECT` | a finite-clause `agent` must not be an accusative-only pronoun |
| `Let they drown.` — nominative ECM subject | `CASE:ACC_ECM_SUBJECT` | an embedded (ECM) `agent` must not be nominative — "let *them* drown" |
| `I see he.` — nominative theme | `CASE:ACC_THEME` | a `theme` must not be a nominative-only pronoun |
| `Ran at he?` — nominative prep-object | `CASE:ACC_POBJ:<prep>` | a prepositional object must not be nominative |

The agent rule **flips with finiteness**: nominative in a matrix clause,
accusative in an ECM complement — the discriminator surfaced from the
corpus sentence *"They will not let them drown."* `you, it, that, this,
one, all` are case-neutral and pass everywhere.

## 5. Complementation (clausal embedding)

**Classical account.** Control / raising; perception-verb complements
take a bare infinitive ("I saw him *run*").

| Construction rejected | Code | Rule |
|---|---|---|
| `Think frog stand.` — clause under a non-licensor | `EMB:NOT_LICENSED` | a clausal `theme` is licensed only under perception/causative verbs (`embedding`: see/hear/watch/let/made) or, subjectless, under a control verb |
| embedded predicate not in base form | `EMB:BARE_INF_REQUIRED` | perception/causative complements take the bare infinitive |
| any violation inside the embedded clause | `EMB>...` | the critic recurses into the complement with finiteness off |

## 6. Determination and the determiner phrase

**Classical account.** Quirk et al. — singular count nouns need a
determiner. Abney (1987), the DP hypothesis — the determiner is a head
selecting a nominal complement. Morphophonemic allomorphy (Koskenniemi
1983, two-level morphology) — *a*/*an* is conditioned by the following
onset.

| Construction rejected | Code | Rule |
|---|---|---|
| `Come like neck.` — bare singular count noun | `NP:BARE_COUNT_NOUN` | a singular count noun must have a DET/POSS/NUM in its NP (surface, scanning left over adjectives; NAME/PRON/mass/plural exempt) |
| `An cow.` — article/onset mismatch | `DET:AN_BEFORE_CONSONANT` | *an* only before a vowel-onset word |
| `A owl.` | `DET:A_BEFORE_VOWEL` | *a* only before a consonant-onset word |
| `Please the for goats.` — headless article | `DET:NO_NOMINAL_HEAD` | *the/a/an* must reach a nominal head over intervening adjectives |

Restriction that matters: the head-saturation check covers **only the
true articles** (the/a/an). Demonstratives and quantifiers (*this, that,
all, more, her*) are DET-tagged but double as pronouns and stand alone,
so they are not stranded when headless — discovered when the first cut
over-fired on real corpus sentences like *"that is Kate."*

## 7. Predication (the copula)

**Classical account.** BE is a two-place predicate linking a subject to
a predicative complement (predicate nominal / adjective / PP) — Fillmore
case frame for copular clauses.

| Construction rejected | Code | Rule |
|---|---|---|
| `Is in you to birds?` — copula with only adjunct PPs | `PRED:COPULA_NO_ARGUMENTS` | a copula frame must have a subject (`agent`) or a predicate (`theme`/`attr`) |

Existential exemption: *"there are five of them in a nest"* projects an
argument-less frame because the pivot may not surface, so existential
*there* is exempted on the surface.

## 8. Mood (interrogative licensing)

**Classical account.** Subject-auxiliary inversion / do-support
(Chomsky 1957). A yes/no question is formed by fronting an auxiliary,
modal, copula, or wh-word — not by intonation alone in this register.

| Construction rejected | Code | Rule |
|---|---|---|
| `Ran?` — bare clause + "?" | `MOOD:Q_NEEDS_INVERSION` | `mood == "q"` must be licensed by a modal, do-support aux, copula, or wh-word (surface, because do-support is absorbed into the frame) |

Why it earns its place: without it, the critic was stricter on statements
than questions (a subjectless past-tense clause is a bad imperative but a
fine "question"), so the generator used "?" as an escape hatch and came
out ~57% questions. With the licenser it is ~8% — see `MCGUFFEY1B.md`.

---

## 9. Verb-specific PP subcategorization

**Classical account.** Subcategorization frames apply to oblique
arguments too: a verb does not simply take "any PP". Case grammar and
early lexicalist grammars treat prepositions as selected complements or
licensed adjunct classes.

| Construction rejected | Code | Rule |
|---|---|---|
| `Roll by the Spot.` | `PP:BAD_PREP:roll:by` | *roll* licenses locative/source PPs (`on/in/from`), not agentive *by* |
| `Know by dolls.` / `Mean from sea.` | `PP:BAD_PREP:<verb>:<prep>` plus valency | cognitive/content verbs do not license arbitrary PPs as argument substitutes |
| `Like Sally with wreaths.` | `PP:BAD_PREP:like:with` | *like* takes a theme, not a stray instrumental/comitative PP |
| `Save Puff at Rab.` | `PP:BAD_PREP:save:at` | *save* licenses source *from*, not locative *at/on* |
| `Let Bess from Spot.` / `Pet Nell in Ned.` | `PP:BAD_PREP:<verb>:<prep>` | causative/perception-like and caring verbs do not accept random locative PPs in this tier |

Implementation: `features.yaml` now has `prep_licenses`, a per-verb
map. The critic checks surface preposition keys in the projected frame.
Generation also applies the same table at the `prep1/prep2` transition,
before the bad PP is sampled.

## 10. Semantic class selection beyond animacy

**Classical account.** Katz-Fodor semantic markers are not limited to
`+ANIMATE`; old-school selectional restrictions routinely use classes
such as `PERSON`, `ANIMAL`, `PLACE`, `ARTIFACT`, `SOUND`, and
`ABSTRACT`.

| Construction rejected | Code | Rule |
|---|---|---|
| `John should eat Rab.` | `SEL:INANIMATE_THEME` | *eat* takes food/substance themes in this register, not named/animal patients |
| `Hand cows.` | `SEL:TRANSFER_THEME_OBJECT` | transfer verbs require a manipulable object as theme, not an animate recipient misread as the thing transferred |
| `How a they show noise.` | `SEL:SHOWABLE_THEME` | *show* requires a visible/showable theme; sounds are heard, not shown |
| `Ride in birds.` / `Come in men.` | `SEL:LOCATIVE_POBJ:<prep>` | locative PPs under motion/location verbs require a place-like object, not an animate object |
| `Sing for noise.` | `SEL:BENEFICIARY_POBJ` | benefactive *for* under *sing* wants an animate beneficiary |

Implementation: `features.yaml` now has shallow semantic classes
(`person`, `animal`, `place`, `artifact`, `substance`, `vehicle`,
`sound`, `abstract`). These are deliberately silver markers: broad
enough to block the observed category errors, narrow enough not to turn
the primer into a world-knowledge database.

## 11. Transfer and recipient frames

**Classical account.** Fillmore case frames distinguish THEME from
GOAL/RECIPIENT. A transfer verb such as *hand* needs a transferred
object and optionally a recipient; an animate NP by itself should not be
silently reinterpreted as the transferred thing.

| Construction rejected | Code | Rule |
|---|---|---|
| `Hand on hands.` | `VAL:THEME_REQUIRED` | *hand* is transitive and cannot be satisfied by a PP alone |
| `Hand cows.` | `SEL:TRANSFER_THEME_OBJECT` | animate theme is rejected for the transfer-object slot |
| `Tell slates for noise.` | `SEL:ANIMATE_THEME` or `PP:BAD_PREP:tell:for` | primer *tell* frames are recipient-like (`tell me`, `tells her`) and do not license *for noise* |

This is not a general theory of ditransitives yet. It is the tier-1
repair: prevent recipient nouns, transferred objects, and stray PPs from
collapsing into one undifferentiated `theme`.

## 12. Coordination type compatibility

**Classical account.** Conjunction imposes a parallelism constraint:
coordinated NPs normally share a semantic type when they fill one
argument slot. This is the selectional analogue of syntactic category
matching.

| Construction rejected | Code | Rule |
|---|---|---|
| `James and ice.` | `COORD:TYPE_MISMATCH` | coordinated intro subjects must share at least one coarse semantic marker |

`Dick and Jane` survives because both are `person`; the rule is
intentionally conservative.

## 13. Stronger question templates

**Classical account.** Subject-aux inversion is a left-edge phenomenon:
the auxiliary/modal/copula/wh licenser must appear at the front of the
question template, not merely somewhere in the clause.

| Construction rejected | Code | Rule |
|---|---|---|
| `Jane did things?` | `MOOD:Q_BAD_INVERSION` | an auxiliary inside an otherwise declarative clause does not license question mood |
| `How a they show noise.` | `MOOD:WH_NEEDS_QUESTION` | a wh-marked frame must be a question in this tier |

The older `MOOD:Q_NEEDS_INVERSION` rule caught bare `?` endings; this
new rule catches pseudo-inversion where a licenser is present but not
fronted.

---

## Summary table

| Family | Codes | Level | Key classical source |
|---|---|---|---|
| Valency | `VAL:THEME_REQUIRED` `VAL:NO_THEME` `VAL:HAVE_NEEDS_COMPLEMENT` `VAL:DO_STRANDED` `VAL:PUT_NEEDS_LOCATION` | frame + surface | Tesnière, Fillmore, Levin, Chomsky 1957 |
| Selection | `SEL:ANIMATE_AGENT` `SEL:ANIMATE_THEME` `SEL:INANIMATE_THEME` `SEL:TRANSFER_THEME_OBJECT` `SEL:SHOWABLE_THEME` `SEL:LOCATIVE_POBJ` `SEL:BENEFICIARY_POBJ` | frame | Katz & Fodor, Wilks |
| PP subcategorization | `PP:BAD_PREP` | frame + generation reweight | Fillmore, lexicalist subcategorization |
| Coordination | `COORD:TYPE_MISMATCH` | frame | semantic parallelism |
| Agreement / form | `AGR:3SG_NEEDS_SG_SUBJ` `AGR:SG_SUBJ_NEEDS_3SG` `AGR:COP_SG` `AGR:COP_PL` `VFORM:BASE_REQUIRED` `VFORM:PARTICIPLE_MATRIX` | frame | GPSG / HPSG |
| Case | `CASE:NOM_SUBJECT` `CASE:ACC_ECM_SUBJECT` `CASE:ACC_THEME` `CASE:ACC_POBJ` | frame | case theory, ECM |
| Complementation | `EMB:NOT_LICENSED` `EMB:BARE_INF_REQUIRED` `EMB>…` | frame | control / raising |
| Determination | `NP:BARE_COUNT_NOUN` `DET:A_BEFORE_VOWEL` `DET:AN_BEFORE_CONSONANT` `DET:NO_NOMINAL_HEAD` | surface | Quirk, Abney (DP), Koskenniemi |
| Predication | `PRED:COPULA_NO_ARGUMENTS` `PRED:COPULA_NO_SUBJECT` | surface | Fillmore (copula) |
| Mood | `MOOD:Q_NEEDS_INVERSION` `MOOD:Q_BAD_INVERSION` `MOOD:WH_NEEDS_QUESTION` | surface + frame | Chomsky 1957 (do-support / inversion) |

## Known limitations (recorded, not yet solved)

- **`Been town?`** — a bare past-participle copula heading a clause slips
  through; `VFORM:PARTICIPLE_MATRIX` is checked for main verbs but not
  extended to copulas.
- **Embedded transitive object drop** — `Let God kill.` / `Watch men
  save.` pass; embedded transitives are not required to have objects
  (the parser cannot reliably attach them, and indefinite null
  complements — Fillmore 1986 — make some genuinely acceptable).
- **Pragmatics** — every check here is grammatical or selectional, never
  about world knowledge or discourse. `Cool as dolls.` is well-formed
  and means nothing. That layer is the queued REF/centering story
  machine, which would re-weight the same field rather than add a veto.
