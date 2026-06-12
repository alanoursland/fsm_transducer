"""Tier-1 generation: frames -> McGuffey-register English.

The author's framing, implemented literally: **tokens are just labels.**
A generative FSM is a transducer whose OUTPUT alphabet is the token
vocabulary — it consumes a stream of frame-element slots and emits
weighted TOKEN.* labels onto them; projection argmaxes the field to
text. The field itself holds a distribution over surface forms (e.g.
TOKEN.0:the 0.7 / TOKEN.0:a 0.3 on an article position) — a language
model in the most literal sense, with the choice auditable in the bag.

Pipeline (the parser's, reversed):

1. **Plan** (code): linearize a frame into element slots in surface
   order — mood/voice decides order (q -> aux/cop fronting; imperative
   agent 'you' -> dropped; intro -> entity list). Element slots carry
   EL:<kind>, VAL:<word>, and the word's lexical class labels (NAME,
   PRON, N...) pulled from the SAME lexicon the parser uses.
2. **Spell** (FSM): the token-emission machine transduces element
   slots, deciding articles (common nouns get weighted the/a; names
   and pronouns none) and emitting TOKEN.* labels.
3. **Render** (projection): argmax TOKEN labels per slot/rank ->
   words; capitalize sentence-start and names; attach mood
   punctuation.

I/O alphabets are DECLARED (the closed-alphabet discipline; see
analysis.signature): inputs = the EL:* element kinds + lexical
classes; outputs = TOKEN.* over the tier-1 vocabulary + TOKEN_SELF.

The round-trip oracle this finally enables: frame -> text -> parse ->
frame must be the identity. Articles are NP-internal and skipped by
the parser, so the round trip holds at FRAME level even where surface
text differs from the corpus original ('a cat' regenerated as 'the
cat' still parses to the same frame).
"""

from __future__ import annotations

import re
from functools import lru_cache

from fsm_parser.fsm import (
    FSM,
    And,
    Emission,
    FSMBuilder,
    FSMScanner,
    HasLabel,
    Not,
    Or,
)
from fsm_parser.mcguffey1_lang import lexicon
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import Slot
from fsm_parser.tokens import ParserState

# kinds of frame-element slots the planner produces (input alphabet)
EL_KINDS = ("ENT", "PRED", "ATTR", "MOD", "NEG", "PREPW", "LIT")


# --- 1. Plan: frame -> element stream (linear order = surface order) -----------


def _ent_elements(value) -> list[tuple[str, str]]:
    if isinstance(value, list):  # group: "dick and jane"
        out = _ent_elements(value[0])
        for v in value[1:]:
            out.append(("LIT", "and"))
            out.extend(_ent_elements(v))
        return out
    return [("ENT", str(value))]


def plan(frame: dict) -> list[tuple[str, str]] | None:
    """Linearize a frame; None if the shape is out of the generator's
    declared coverage (wh-questions, unsupported keys)."""
    known = {"pred", "agent", "theme", "attr", "mod", "neg", "mood"}
    preps = {k: v for k, v in frame.items() if k not in known and k != "wh"}
    if "wh" in frame or not all(isinstance(v, str) for v in preps.values()):
        return None
    els: list[tuple[str, str]] = []
    pred = frame.get("pred")
    agent = frame.get("agent")
    theme = frame.get("theme")
    mood_q = frame.get("mood") == "q"

    if agent is None and pred not in ("is", "are", "was", "were", "intro"):
        return None
    if pred == "intro":
        if agent is None:
            return None
        return _ent_elements(agent)

    if isinstance(theme, dict):  # embedded: "See Spot run."
        if mood_q or frame.get("mod") or theme.get("theme") is not None:
            return None
        if agent == "you":
            els.append(("PRED", pred))
        else:
            els.extend(_ent_elements(agent))
            els.append(("PRED", pred))
        els.extend(_ent_elements(theme.get("agent")))
        els.append(("PRED", theme["pred"]))
        return els

    fronted = frame.get("mod") or (pred if mood_q else None)
    if mood_q and fronted:  # inversion: "Can Ann fan the lad?"
        els.append(("MOD", frame["mod"]) if frame.get("mod") else ("PRED", pred))
        if agent is not None:
            els.extend(_ent_elements(agent))
        if frame.get("neg"):
            els.append(("NEG", "not"))
        if frame.get("mod"):
            els.append(("PRED", pred))
    else:
        if agent == "you" and not mood_q:  # imperative: drop the agent
            pass
        elif agent is not None:
            els.extend(_ent_elements(agent))
        if frame.get("mod"):
            els.append(("MOD", frame["mod"]))
        if frame.get("neg"):
            els.append(("NEG", "not"))
        els.append(("PRED", pred))
    if theme is not None and not isinstance(theme, dict):
        els.extend(_ent_elements(theme))
    if frame.get("attr"):
        els.append(("ATTR", frame["attr"]))
    for p, v in preps.items():
        els.append(("PREPW", p))
        els.extend(_ent_elements(v))
    return els


def element_stream(els: list[tuple[str, str]]) -> ParserState:
    state = ParserState()
    lex = lexicon()
    for i, (kind, word) in enumerate(els):
        slot = Slot(id=f"el:{i}", kind="el", stream="el", order=float(i), text=word)
        slot.labels.add(f"EL:{kind}", 1.0)
        slot.labels.add(f"VAL:{word}", 1.0)
        for lab, w in lex.get(word, {}).items():  # lexical classes for the FSM
            slot.labels.add(lab, float(w))
        state.add_slot("el", slot)
    return state


# --- 2. Spell: the token-emission FSM -------------------------------------------


def build_token_emitter() -> FSM:
    """One-state transducer: element slots in, TOKEN.* labels out.

    The output alphabet is the tier-1 token vocabulary (via TOKEN_SELF,
    'this slot's VAL is the token') plus the closed-class words it
    inserts itself (articles). Weighted articles put a genuine
    distribution over surface forms into the field.
    """
    b = FSMBuilder("token_emitter")
    s = b.state("emit")
    b.start(s)
    b.accept(s)
    ent = HasLabel("EL:ENT")
    bare = Or((HasLabel("NAME"), HasLabel("PRON")))
    b.transition(s, And((ent, Not(bare))), s, emissions=[
        Emission("TOKEN.0:the", 0.7, offset=0),
        Emission("TOKEN.0:a", 0.3, offset=0),     # the field holds both
        Emission("TOKEN.1:SELF", 1.0, offset=0),
    ])
    b.transition(s, And((ent, bare)), s,
                 emissions=[Emission("TOKEN.1:SELF", 1.0, offset=0)])
    b.transition(s, Not(ent), s,
                 emissions=[Emission("TOKEN.1:SELF", 1.0, offset=0)])
    return b.build()


@lru_cache(maxsize=1)
def _emitter() -> FSM:
    return build_token_emitter()


# --- 3. Render: argmax the field to text ------------------------------------------


_TOKEN_LABEL = re.compile(r"TOKEN\.(\d+):(.+)$")


def generate(frame: dict) -> str | None:
    els = plan(frame)
    if els is None or not els:
        return None
    state = element_stream(els)
    deltas = FSMScanner().transduce(_emitter(), state, stream="el", anchored=True)
    apply_deltas(state, deltas)

    lex = lexicon()
    words: list[tuple[str, bool]] = []   # (word, is_entity_position)
    for slot in state.stream("el"):
        is_ent = "EL:ENT" in slot.labels
        per_rank: dict[int, tuple[float, str]] = {}
        for lab, w in slot.labels.items():
            m = _TOKEN_LABEL.match(lab)
            if m:
                rank, tok = int(m.group(1)), m.group(2)
                if rank not in per_rank or w > per_rank[rank][0]:
                    per_rank[rank] = (w, tok)
        for rank in sorted(per_rank):
            tok = per_rank[rank][1]
            words.append((slot.text, is_ent) if tok == "SELF" else (tok, False))

    out = []
    for i, (w, is_ent) in enumerate(words):
        # names capitalize only in entity positions (rob the verb vs Rob)
        if i == 0 or (is_ent and "NAME" in lex.get(w, {})) or w == "i":
            w = w.capitalize() if w != "i" else "I"
        out.append(w)
    punct = "?" if frame.get("mood") == "q" else "."
    return " ".join(out) + punct
