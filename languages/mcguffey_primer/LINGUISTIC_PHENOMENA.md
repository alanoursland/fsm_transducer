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

## Summary table

| Family | Codes | Level | Key classical source |
|---|---|---|---|
| Valency | `VAL:THEME_REQUIRED` `VAL:NO_THEME` `VAL:HAVE_NEEDS_COMPLEMENT` `VAL:DO_STRANDED` `VAL:PUT_NEEDS_LOCATION` | frame + surface | Tesnière, Fillmore, Levin, Chomsky 1957 |
| Selection | `SEL:ANIMATE_AGENT` `SEL:ANIMATE_THEME` | frame | Katz & Fodor, Wilks |
| Agreement / form | `AGR:3SG_NEEDS_SG_SUBJ` `AGR:SG_SUBJ_NEEDS_3SG` `AGR:COP_SG` `AGR:COP_PL` `VFORM:BASE_REQUIRED` `VFORM:PARTICIPLE_MATRIX` | frame | GPSG / HPSG |
| Case | `CASE:NOM_SUBJECT` `CASE:ACC_ECM_SUBJECT` `CASE:ACC_THEME` `CASE:ACC_POBJ` | frame | case theory, ECM |
| Complementation | `EMB:NOT_LICENSED` `EMB:BARE_INF_REQUIRED` `EMB>…` | frame | control / raising |
| Determination | `NP:BARE_COUNT_NOUN` `DET:A_BEFORE_VOWEL` `DET:AN_BEFORE_CONSONANT` `DET:NO_NOMINAL_HEAD` | surface | Quirk, Abney (DP), Koskenniemi |
| Predication | `PRED:COPULA_NO_ARGUMENTS` | surface | Fillmore (copula) |
| Mood | `MOOD:Q_NEEDS_INVERSION` | surface | Chomsky 1957 (do-support / inversion) |

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
