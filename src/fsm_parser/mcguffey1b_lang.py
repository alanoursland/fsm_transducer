"""mcguffey1b: tier-1 English with grammatical and semantic brakes.

Same dataset, same clause story machine, same lexicon as mcguffey1 —
the 'b' is a model revision, not a new tier (mcguffey2 is reserved for
the First Reader corpus). What's new is **a layer**.

Read the system as a symbolic transformer: the label bag is the
residual stream, each machine is a block that reads it and writes
back. mcguffey1 is the syntactic block — it accretes constituent
labels and projects a frame. mcguffey1b adds the NEXT block on top: a
SELECTIONAL/AGREEMENT layer that reads the projected frame (the place
the residual stream has reached) and writes a single bit — does this
reading survive the grammar of the world? In analysis that bit gates
(parse -> None on violation); in generation the SAME layer runs in the
forward direction and re-weights the next-token field so violations are
never sampled (ENCL: upstream narrates, the reflex reads). One layer,
both directions — exactly the parser/LM duality of mcguffey1, now with
a second block in the stack.

mcguffey1's recall was ratcheted; this block ratchets precision —
"Schoolhouse eat." and "Loves." parsed under mcguffey1 and must not
parse here, while corpus coverage must not drop.

The checks are the classical inventory, by name:

* **Valency / subcategorization** (Tesniere 1959 dependency valence;
  Fillmore 1968 case frames): transitive verbs demand a THEME
  ("Loves." dies), intransitives forbid one ("Come cap by way." dies).
* **Selectional restrictions** (Katz & Fodor 1963 semantic markers;
  checked in the spirit of Wilks 1975 preference semantics): agentive
  verbs demand +ANIMATE agents ("Schoolhouse eat." dies). Preferences
  are per-verb relaxable (agent_any), not a global hard type system.
* **Complementation classes**: bare-infinitive embedded clauses only
  under perception/causative licensors — see/hear/watch/let/made
  ("See Spot run" lives, "Think frog stand." dies).
* **Agreement + verb form** (feature checking in the GPSG/HPSG sense,
  done on frames rather than by unification): 3SG verbs need
  3SG-compatible subjects and vice versa ("Walks John watch." dies —
  an imperative must be base form), modals and do-support govern base
  form, participles cannot stand as finite matrix predicates
  ("Seen horse show." dies).

Features live in languages/mcguffey_primer/features.yaml (overlay;
lexicon.yaml untouched so mcguffey1 behaves exactly as before).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from fsm_parser.mcguffey1_lang import parse as _parse_m1

_FEAT_PATH = Path(__file__).parent.parent.parent / "languages" / "mcguffey_primer" / "features.yaml"

COPULAS = {"is", "are", "was", "were", "be", "been"}
SG_COPULAS = {"is", "was"}
PL_COPULAS = {"are", "were"}


@lru_cache(maxsize=1)
def features() -> dict:
    raw = yaml.safe_load(_FEAT_PATH.read_text())
    ent, vb = raw["entities"], raw["verbs"]
    return {
        "animate": set(ent["animate"]),
        "plural": set(ent["plural"]),
        "both_number": set(ent["both_number"]),
        "no_3sg": set(ent["no_3sg"]),
        "form_3sg": set(vb["form_3sg"]),
        "form_past": set(vb["form_past"]),
        "form_participle": set(vb["form_participle"]),
        "transitive": set(vb["transitive"]),
        "intransitive": set(vb["intransitive"]),
        "embedding": set(vb["embedding"]),
        "agent_any": set(vb["agent_any"]),
        "control": set(vb["control"]),
        "bare_ok": set(ent["bare_ok"]),
    }


def _num(value, f) -> str:
    """Number of an entity value: sg, pl, or b (either)."""
    if isinstance(value, list):
        return "pl"
    w = str(value)
    if w in f["both_number"]:
        return "b"
    return "pl" if w in f["plural"] else "sg"


def _animate(value, f) -> bool:
    if isinstance(value, list):
        return all(_animate(v, f) for v in value)
    return str(value) in f["animate"]


def _takes_3sg(value, f) -> bool:
    """Can this subject head a 3SG verb? (number sg AND person 3rd)"""
    if isinstance(value, list):
        return False
    w = str(value)
    if w in f["no_3sg"]:
        return False
    return _num(value, f) in ("sg", "b")


def _is_verbal(value) -> bool:
    """A frame value that is verb-tagged in the lexicon — the surface
    trace of an infinitive the parser mistook for an NP."""
    from fsm_parser.mcguffey1_lang import lexicon
    return isinstance(value, str) and "V" in lexicon().get(value, {})


def _vform(pred: str, f) -> str:
    if pred in f["form_3sg"]:
        return "3sg"
    if pred in f["form_past"]:
        return "past"
    if pred in f["form_participle"]:
        return "part"
    return "base"


def violations(frame: dict, *, finite: bool = True) -> list[str]:  # noqa: PLR0912 - one rulebook, one place
    """The critic: classical-NLP checks on a single projected frame.
    Returns violation codes; empty means the frame passes. Embedded
    (nonfinite) clauses skip agreement/finiteness checks."""
    f = features()
    pred = frame.get("pred")
    agent = frame.get("agent")
    theme = frame.get("theme")
    out: list[str] = []
    if pred is None or pred == "intro":
        return out

    if pred in COPULAS:  # copula agreement: is/was sg, are/were pl
        subj = agent if agent is not None else theme  # existential there
        if subj is not None:
            n = "pl" if isinstance(subj, list) else _num(subj, f)
            if pred in SG_COPULAS and n == "pl":
                out.append("AGR:COP_SG")
            if pred in PL_COPULAS and n == "sg" and not (
                    isinstance(subj, str) and subj in f["no_3sg"]):
                out.append("AGR:COP_PL")
        return out

    form = _vform(pred, f)
    has_mod = bool(frame.get("mod"))
    imperative = agent == "you" and frame.get("mood") != "q" and not has_mod

    # verb form: modals/do-support and imperatives govern BASE;
    # a participle cannot stand as the finite matrix verb
    if finite:
        if (has_mod or imperative) and form != "base":
            out.append("VFORM:BASE_REQUIRED")
        if form == "part" and not has_mod:
            out.append("VFORM:PARTICIPLE_MATRIX")

    # agreement (only finite, non-modal, non-imperative clauses;
    # past tense is number-neutral in English)
    if finite and agent is not None and not has_mod and not imperative:
        if form == "3sg" and not _takes_3sg(agent, f):
            out.append("AGR:3SG_NEEDS_SG_SUBJ")
        if form == "base" and _takes_3sg(agent, f):
            out.append("AGR:SG_SUBJ_NEEDS_3SG")

    # valency (Tesniere/Fillmore): t demands a theme, i forbids one.
    # The to-infinitive/preposition ambiguity (a classical chestnut):
    # mcguffey1 parses "likes to ride" as a PP with a V-tagged object,
    # so a 'to' complement that is verb-tagged satisfies transitives,
    # and a V-tagged "theme" of an intransitive is a purpose infinitive
    # ("went to the pond to fish"), not an object. Nonfinite clauses
    # skip the theme requirement: the parser cannot reliably attach
    # embedded objects yet.
    if finite and pred in f["transitive"] and theme is None \
            and not _is_verbal(frame.get("to")):
        out.append("VAL:THEME_REQUIRED")
    if pred in f["intransitive"] and theme is not None \
            and not _is_verbal(theme):
        out.append("VAL:NO_THEME")

    # complementation: clausal themes only under perception/causative
    # licensors ("See Spot run") or, subjectless, under control verbs
    # ("I like to see ...")
    if isinstance(theme, dict):
        subjectless = theme.get("agent") is None
        if not (pred in f["embedding"]
                or (subjectless and pred in f["control"])):
            out.append("EMB:NOT_LICENSED")
        out.extend(f"EMB>{v}" for v in violations(theme, finite=False))
        if _vform(theme.get("pred", ""), f) != "base":
            out.append("EMB:BARE_INF_REQUIRED")

    # selectional restriction (Katz-Fodor marker, Wilks preference):
    # agentive verbs want +ANIMATE agents
    if (agent is not None and pred not in f["agent_any"]
            and not _animate(agent, f)):
        out.append("SEL:ANIMATE_AGENT")
    return out


def critique(frames: list[dict]) -> list[str]:
    return [v for fr in frames for v in violations(fr)]


def bare_np_violations(text: str, frames: list[dict]) -> list[str]:
    """Singular count nouns need a determiner (Quirk et al.). Frames
    cannot see articles (projection absorbs them), so this one check
    reads the token surface: an entity-valued singular count noun must
    have a DET/POSS/NUM somewhere in its NP (left over any ADJs)."""
    from fsm_parser.mcguffey1_lang import _TOKEN, lexicon

    f = features()
    lex = lexicon()
    ent_vals: set[str] = set()

    def walk(v):  # entity positions only: agent/theme/prep objects
        if isinstance(v, dict):
            for k, x in v.items():
                if k not in ("pred", "attr", "mod", "neg", "mood", "wh"):
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        else:
            ent_vals.add(str(v))
    walk(frames)

    toks = [t.lower() for t in _TOKEN.findall(text)]
    out = []
    for i, w in enumerate(toks):
        if w not in ent_vals or "N" not in lex.get(w, {}):
            continue
        tags = lex[w]
        if ("NAME" in tags or "PRON" in tags or w in f["bare_ok"]
                or w in f["plural"] or w in f["both_number"]):
            continue
        # infinitive read as NP ("likes to ride"): not a count noun
        if i > 0 and toks[i - 1] == "to" and "V" in tags:
            continue
        # scan left over the NP: adjectives and compounding nouns;
        # a NAME licenses (surname compounds: "Nat Pond")
        j = i - 1
        licensors = {"DET", "POSS", "NUM", "WH", "NAME"}
        while j >= 0 and ({"ADJ", "N", "NAME"} & set(lex.get(toks[j], {}))):
            if licensors & set(lex.get(toks[j], {})):
                break
            j -= 1
        if j < 0 or not (licensors & set(lex.get(toks[j], {}))):
            out.append(f"NP:BARE_COUNT_NOUN:{w}")
    return out


def accept(text: str, frames: list[dict]) -> bool:
    """The LM gate: a sampled sentence passes only if its frames clear
    the critic and its NPs are properly determined."""
    return not (critique(frames) or bare_np_violations(text, frames))


_ENTITY_REGS = {"subj", "subj2", "obj", "obj2", "pobj1", "pobj2", "voc",
                "b_subj", "b_obj"}
_VERB_REGS = {"verb", "verb2", "b_verb"}


def _verb_subject_ok(verb: str, subj: str, *, has_mod: bool, f) -> bool:
    """Agreement + selection between a candidate verb and the subject
    the machine already captured — the brake checked at the verb step,
    where both ends of the dependency are finally visible."""
    form = _vform(verb, f)
    if has_mod:
        return form == "base"  # modal governs the bare infinitive
    if form == "3sg" and not _takes_3sg(subj, f):
        return False
    if form == "base" and _takes_3sg(subj, f):
        return False           # "the cat run" — needs "runs"
    if verb not in f["agent_any"] and not _animate(subj, f):
        return False           # selectional: agentive verb wants animacy
    return True


def reweight(prefix: list[str], dist: dict[str, float]) -> dict[str, float]:
    """ENCL in the generator: the critic steers the next-token field
    rather than only judging finished sentences. For each candidate we
    recover the register it would fill (from the transition's captures)
    and the subject already on the path, then drop candidates that would
    commit an agreement/selection/determination violation. A word kept
    on ANY frontier analysis survives — superposition is respected; only
    the provably-bad readings are pruned."""
    from fsm_parser.mcguffey1_lang import lexicon
    from fsm_parser.mcguffey1_lm import _frontier, _machine, _vocab, support

    f = features()
    lex = lexicon()
    m = _machine()
    has_mod = any("MOD" in lex.get(t, {}) for t in prefix)
    prev = prefix[-1] if prefix else None
    prev_tags = set(lex.get(prev, {})) if prev else set()
    np_open = bool(prev_tags & {"DET", "POSS", "NUM", "ADJ"})

    ok_any: dict[str, bool] = {}
    for path in _frontier(prefix):
        subj = None
        for reg in ("subj", "subj2", "b_subj"):
            cv = path.captures.get(reg)
            if cv is not None and cv.pos is not None and cv.pos < len(prefix):
                subj = prefix[cv.pos]
                break
        for tr in m.transitions_from(path.state):
            if tr.epsilon:
                continue
            roles = {c.name for c in tr.captures}
            for w in dist:
                if support(tr.condition, _vocab()[w]) <= 0.0:
                    continue
                ok = True
                if roles & _VERB_REGS and subj is not None:
                    ok = _verb_subject_ok(w, subj, has_mod=has_mod, f=f)
                if ok and (roles & _ENTITY_REGS):
                    tags = lex.get(w, {})
                    count_noun = ("N" in tags and "NAME" not in tags
                                  and "PRON" not in tags
                                  and w not in f["plural"]
                                  and w not in f["both_number"]
                                  and w not in f["bare_ok"])
                    if count_noun and not np_open:
                        ok = False     # bare singular count noun
                ok_any[w] = ok_any.get(w, False) or ok

    # the punctuation step is the strongest brake: only allow ending the
    # sentence when the completed frame passes the full critic. This
    # turns end-of-sentence valency/PP checks into a generation
    # constraint, so a sampled PUNCT is (almost) always accepted.
    for p in (".", "?"):
        if p in dist and prefix:
            text = " ".join(prefix) + p
            fr = _parse_m1(text)
            ok_any[p] = bool(fr) and not (
                critique(fr) or bare_np_violations(text, fr))

    out = {w: x for w, x in dist.items() if ok_any.get(w, True)}
    if out:
        return out
    # no clean candidate. Prefer to keep growing (drop punctuation) over
    # emitting a dirty ending; if even that is empty the only legal next
    # token is a dirty punct, so return nothing and let the sampler
    # reject this prefix outright — the brake never lets a violation out.
    return {w: x for w, x in dist.items() if w not in (".", "?", ",")}


def generate_lm(n_sentences: int = 5, **kw) -> str:
    """mcguffey1's autoregressive sampler with the brakes engaged: the
    critic both steers each step (reweight) and gates each finished
    sentence (accept). Same machine proposes; the grammar/semantics
    judge throughout."""
    from fsm_parser.mcguffey1_lm import generate_lm as _gen
    # the brakes make the target region small, so the sampler needs both
    # a generous try budget and exploration: at low temperature the field
    # collapses onto a few high-weight, often dead-end words and yield
    # craters, so keep temperature >= ~0.8 when the brakes are engaged.
    kw.setdefault("max_tries", 1500)
    return _gen(n_sentences, accept=accept, reweight=reweight,
                require_roundtrip=False, **kw)


def parse(text: str) -> list[dict] | None:
    """mcguffey1's parse, gated by the critic. None on any violation —
    precision is the product; mcguffey1 remains the recall surface."""
    frames = _parse_m1(text)
    if frames is None:
        return None
    if critique(frames) or bare_np_violations(text, frames):
        return None
    return frames
