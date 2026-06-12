"""Tier-1 early-reader English: the McGuffey Primer language.

GROWN from `primer_lang` (Steele-style: the seed language plus
definitions over what already exists; growth never removes). New over
the seed: NP-internal structure (DET/ADJ/POSS/NUM skipped to heads),
prepositional phrases (two deep), modals and do-support, negation,
yes/no and wh-questions via inversion that funnels back into the
declarative spine, NP fragments ("A cat and a rat."), predicate
nominals, existential 'there', clause coordination ("Ann sat, and Nat
ran."), and object coordination — the latter two distinguished by an
NFA fork resolved structurally.

Two engineering notes:

* **Absent-register drop**: accept transitions carry the SUPERSET of
  role emissions; a CaptureAnchor whose register was never written
  resolves to nothing and the emission silently drops. Optional
  constituents therefore cost no states.
* **Modifier ops are lenient** in the VM (MOD/NEG/WH/MOOD no-op when
  no frame is on top) so token-order edge cases degrade instead of
  failing; role ops stay strict.

Lexicon: languages/mcguffey_primer/lexicon.yaml — all 288 tier-1 words
plus the primer seed vocabulary, tagged by LLM-as-annotator (silver;
see the oracle-cliff discussion).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from fsm_parser.fsm import (
    FSM,
    And,
    Capture,
    CaptureAnchor,
    Emission,
    FSMBuilder,
    FSMScanner,
    HasLabel,
    Not,
    Or,
)
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import Slot, SourceSpan
from fsm_parser.tokens import ParserState

_LEX_PATH = Path(__file__).parent.parent.parent / "languages" / "mcguffey_primer" / "lexicon.yaml"
_TOKEN = re.compile(r"[A-Za-z]+(?:'[a-z]+)?|[.!?,;]")

P_IMP, P_SUBJ = 0.55, 0.45  # sentence-initial N/V fork priors (seed's)


@lru_cache(maxsize=1)
def lexicon() -> dict[str, dict[str, float]]:
    return yaml.safe_load(_LEX_PATH.read_text())["entries"]


# --- Layer 0: tokenization + lexicon ------------------------------------------


def initialize(text: str) -> ParserState:
    state = ParserState()
    lex = lexicon()
    cursor = 0
    for i, raw in enumerate(_TOKEN.findall(text)):
        idx = text.find(raw, cursor)
        cursor = idx + len(raw)
        slot = Slot(
            id=f"token:{i}", kind="token", stream="token", order=float(i),
            text=raw, source_span=SourceSpan(idx, idx + len(raw)),
        )
        word = raw.lower()
        slot.labels.add(f"TEXT:{raw}", 1.0)
        if word in lex:
            for lab, w in lex[word].items():
                slot.labels.add(lab, float(w))
            slot.labels.add(f"VAL:{word}", 1.0)
        elif raw == ",":
            slot.labels.add("COMMA", 1.0)
        elif raw == ";":
            slot.labels.add("CONJ", 1.0)   # semicolon coordinates clauses
            slot.labels.add(f"VAL:{raw}", 1.0)
        elif raw in ".!?":
            slot.labels.add("PUNCT", 1.0)
            if raw == "?":
                slot.labels.add("QMARK", 1.0)
        else:
            slot.labels.add("ERROR:UNKNOWN_WORD", 1.0)
        state.add_slot("token", slot)
    return state


# --- The clause story machine --------------------------------------------------


REGS = ("subj", "subj2", "verb", "verb2", "obj", "obj2", "mod", "neg",
        "adj", "prep1", "pobj1", "prep2", "pobj2", "voc", "wh", "cnj",
        "b_subj", "b_verb", "b_obj", "b_adj")


def _at(label: str, reg: str) -> Emission:
    return Emission(label, 1.0, anchor=CaptureAnchor(reg))


def _role_sets() -> dict[str, list[Emission]]:
    """Accept-emission supersets. Registers never written drop out."""
    core = [
        _at("EXEC.0:ENT(!{VAL})", "subj"),
        _at("EXEC.0:ENT(!{VAL})", "subj2"),
        _at("EXEC.1:GROUP", "subj2"),
        _at("EXEC.1:EVT(!{VAL})", "verb"),
        _at("EXEC.2:AGENT", "verb"),
        _at("EXEC.4:AGENTI", "subj"),   # inversion: subj after verb
        _at("EXEC.3:ATTR(!{VAL})", "adj"),
        _at("EXEC.0:ENT(!{VAL})", "pobj1"),
        _at("EXEC.3:PREP(!{VAL@{prep1}})", "pobj1"),
        _at("EXEC.0:ENT(!{VAL})", "pobj2"),
        _at("EXEC.3:PREP(!{VAL@{prep2}})", "pobj2"),
    ]
    emb = [
        _at("EXEC.1:EVT(!{VAL})", "verb2"),
        _at("EXEC.2:AGENT", "verb2"),
        _at("EXEC.3:THEME", "verb2"),
    ]
    # obj's role depends on what follows: matrix theme (decl_a) or
    # embedded agent (decl_c) — the one place the superset trick splits
    decl_a = core + [_at("EXEC.0:ENT(!{VAL})", "obj"),
                     _at("EXEC.3:THEME", "obj")]
    decl_c = core + [_at("EXEC.0:ENT(!{VAL})", "obj")] + emb
    decl_b = core + [_at("EXEC.0:ENT(!{VAL})", "obj"),
                     _at("EXEC.0:ENT(!{VAL})", "obj2"),
                     _at("EXEC.1:GROUP", "obj2"),
                     _at("EXEC.3:THEME", "obj2")]
    imp_base = [
        _at("EXEC.0:IMPYOU", "verb"),
        _at("EXEC.1:EVT(!{VAL})", "verb"),
        _at("EXEC.2:AGENT", "verb"),
        _at("EXEC.0:ENT(!{VAL})", "obj"),
        _at("EXEC.0:ENT(!{VAL})", "pobj1"),
        _at("EXEC.3:PREP(!{VAL@{prep1}})", "pobj1"),
        _at("EXEC.0:ENT(!{VAL})", "pobj2"),
        _at("EXEC.3:PREP(!{VAL@{prep2}})", "pobj2"),
    ]
    imp_a = imp_base + [_at("EXEC.3:THEME", "obj")]
    imp_b = imp_base + emb
    voc = [
        _at("EXEC.1:EVT(!{VAL})", "verb"),
        _at("EXEC.0:ENT(!{VAL})", "voc"),
        _at("EXEC.2:AGENT", "voc"),
    ]
    intro = [
        _at("EXEC.0:ENT(!{VAL})", "subj"),
        _at("EXEC.0:ENT(!{VAL})", "subj2"),
        _at("EXEC.1:GROUP", "subj2"),
    ]
    clause_b = [
        _at("EXEC.0:ENT(!{VAL})", "b_subj"),
        _at("EXEC.4:AGENTI", "b_subj"),
        _at("EXEC.1:EVT(!{VAL})", "b_verb"),
        _at("EXEC.2:AGENT", "b_verb"),
        _at("EXEC.0:ENT(!{VAL})", "b_obj"),
        _at("EXEC.3:THEME", "b_obj"),
        _at("EXEC.3:ATTR(!{VAL})", "b_adj"),
    ]
    return {"decl_a": decl_a, "decl_b": decl_b, "decl_c": decl_c,
            "imp_a": imp_a, "imp_b": imp_b, "voc": voc,
            "intro": intro, "clause_b": clause_b}


def build_clause_story() -> FSM:  # noqa: PLR0915 - one grammar, one place
    b = FSMBuilder("mcguffey1_clause")
    names = ("S0 S0D FRAGV FRAGN FRAGD SUBJ_AND FRAG2 MODAL VP OBJ OBJ_AND OBJ2 EMB "
             "PP1 PP1O PP2 PP2O COPS COPX IMP IMPO IMPEMB IMPPP IMPPPO "
             "VOC VOC2 VOC3 IMPV2 QA QS WHQ WHN CC C2S C2SN C2F C2V C2O DOIMP APP SPP SPPO DONE").split()
    st = {n: b.state(n) for n in names}
    b.start(st["S0"])
    b.accept(st["DONE"])

    V, N = HasLabel("V"), HasLabel("N")
    name_l, adv = HasLabel("NAME"), HasLabel("ADV")
    cop, mod_l, aux = HasLabel("COP"), HasLabel("MOD"), HasLabel("AUX")
    neg, to, prep = HasLabel("NEG"), HasLabel("TO"), HasLabel("PREP")
    adj, conj, comma = HasLabel("ADJ"), HasLabel("CONJ"), HasLabel("COMMA")
    wh, interj = HasLabel("WH"), HasLabel("INTERJ")
    punct, qmark = HasLabel("PUNCT"), HasLabel("QMARK")
    p_dot = And((punct, Not(qmark)))
    np_in = Or((HasLabel("DET"), adj, HasLabel("POSS"), HasLabel("NUM")))
    n_only, v_only = And((N, Not(V))), And((V, Not(N)))
    v_and_n = And((V, N))

    cap = {r: Capture(r, kind="slot_id") for r in REGS}
    sets = _role_sets()

    def accept(src: str, role_set: str, *, mood_anchor: str = "punct",
               second: bool = False) -> None:
        """Two accept transitions: '.'/'!' and '?' (adds mood q)."""
        ems = list(sets[role_set])
        mods = [Emission("EXEC.5:MOD(!{VAL@{mod}})", 1.0, offset=0),
                Emission("EXEC.6:WH(!{VAL@{wh}})", 1.0, offset=0),
                Emission("EXEC.7:NEGSET(!{VAL@{neg}})", 1.0, offset=0)]
        if role_set == "intro":
            mods = [Emission("EXEC.4:INTRO", 1.0, offset=0),
                    Emission("EXEC.7:AGENT", 1.0, offset=0)]
        if second:
            # clause A's modifiers and END land on the conjunction slot
            ems += [_at("EXEC.5:MOD(!{VAL@{mod}})", "cnj"),
                    _at("EXEC.9:END", "cnj")] + sets["clause_b"]
        end = [Emission("EXEC.9:END", 1.0, offset=0)]
        b.transition(st[src], p_dot, st["DONE"], emissions=ems + mods + end)
        b.transition(st[src], qmark, st["DONE"],
                     emissions=ems + mods +
                     [Emission("EXEC.8:MOODQ", 1.0, offset=0)] + end)

    def loop(s: str, cond) -> None:
        b.transition(st[s], cond, st[s])

    def go(src: str, cond, dst: str, reg: str | None = None,
           w: float = 1.0, eager: str | None = None) -> None:
        b.transition(st[src], cond, st[dst], weight=w,
                     captures=[cap[reg]] if reg else [],
                     emissions=[Emission(eager, w, offset=0)] if eager else [])

    # ---- sentence start --------------------------------------------------
    for c in (interj, comma, adv):
        loop("S0", c)
    # det/adj material routes through S0D so fragment-hood is knowable:
    # FRAGD (det-introduced) may be a caption fragment; FRAGN (bare noun)
    # may host an appositive; FRAGV (possibly-verbal word) may do neither
    # — plausibility encoded in state structure (interim until
    # story-coherent projection; see GROWTH.md).
    go("S0", np_in, "S0D")
    loop("S0D", np_in)
    go("S0D", N, "FRAGD", "subj", 1.0, "STORY:DECL")
    go("S0", n_only, "FRAGN", "subj", 1.0, "STORY:DECL")
    go("S0", v_and_n, "FRAGV", "subj", P_SUBJ, "STORY:DECL")
    go("S0", v_only, "IMP", "verb", 1.0, "STORY:IMP")
    go("S0", v_and_n, "IMP", "verb", P_IMP, "STORY:IMP")
    go("S0", cop, "COPS", "verb", 1.0, "STORY:DECL")   # existential 'There is...'
    go("S0", aux, "QA", "verb", 0.6, "STORY:Q")
    go("S0", mod_l, "QA", "mod", 1.0, "STORY:Q")
    go("S0", wh, "WHQ", "wh", 1.0, "STORY:Q")

    # ---- subject area (shared exits for all FRAG variants) ----------------
    for f in ("FRAGV", "FRAGN", "FRAGD"):
        go(f, V, "VP", "verb")
        go(f, cop, "COPS", "verb")
        go(f, mod_l, "MODAL", "mod")
        go(f, aux, "MODAL", "mod")
        go(f, conj, "SUBJ_AND")
    accept("FRAGD", "intro")               # fragments need a determiner...
    loop("SUBJ_AND", np_in)
    go("SUBJ_AND", N, "FRAG2", "subj2")
    go("FRAG2", V, "VP", "verb")
    go("FRAG2", cop, "COPS", "verb")
    go("FRAG2", mod_l, "MODAL", "mod")
    accept("FRAG2", "intro")

    go("MODAL", neg, "MODAL", "neg")
    go("MODAL", V, "VP", "verb")
    go("MODAL", cop, "COPS", "verb")

    # ---- verb phrase spine ------------------------------------------------
    for c in (adv, np_in, to):
        loop("VP", c)
    go("VP", neg, "VP", "neg")
    go("VP", N, "OBJ", "obj")
    go("VP", prep, "PP1", "prep1")
    go("VP", v_only, "EMB", "verb2")
    go("VP", comma, "CC")
    go("VP", conj, "C2S", "cnj")
    accept("VP", "decl_a")

    loop("OBJ", adv)
    loop("OBJ", to)
    go("OBJ", V, "EMB", "verb2")
    go("OBJ", prep, "PP1", "prep1")
    go("OBJ", comma, "CC")
    go("OBJ", conj, "C2S", "cnj", 0.5)        # clause coordination...
    go("OBJ", conj, "OBJ_AND", None, 0.5)     # ...or object coordination
    accept("OBJ", "decl_a")
    loop("OBJ_AND", np_in)
    go("OBJ_AND", N, "OBJ2", "obj2")
    accept("OBJ2", "decl_b")

    go("EMB", prep, "PP1", "prep1")
    accept("EMB", "decl_c")

    loop("PP1", np_in)
    go("PP1", N, "PP1O", "pobj1")
    loop("PP1O", adv)
    go("PP1O", prep, "PP2", "prep2")
    go("PP1O", comma, "CC")
    go("PP1O", conj, "C2S", "cnj")
    accept("PP1O", "decl_a")
    loop("PP2", np_in)
    go("PP2", N, "PP2O", "pobj2")
    accept("PP2O", "decl_a")

    # ---- copula ----------------------------------------------------------
    go("COPS", neg, "COPS", "neg")
    loop("COPS", np_in)
    go("COPS", adj, "COPX", "adj")
    go("COPS", And((adv, Not(adj))), "COPX", "adj")   # "is here" -> attr
    go("COPS", And((N, Not(V), Not(adj))), "COPX", "obj")         # predicate nominal -> theme
    go("COPS", prep, "PP1", "prep1")
    loop("COPX", adv)
    go("COPX", prep, "PP1", "prep1")
    go("COPX", comma, "CC")
    go("COPX", conj, "C2S", "cnj")
    accept("COPX", "decl_a")

    # ---- imperatives -------------------------------------------------------
    for c in (adv, np_in, to):
        loop("IMP", c)
    go("IMP", neg, "IMP", "neg")
    go("IMP", N, "IMPO", "obj")
    go("IMP", prep, "IMPPP", "prep1")
    go("IMP", comma, "VOC")
    accept("IMP", "imp_a")
    loop("IMPO", adv)
    go("IMPO", V, "IMPEMB", "verb2")
    go("IMPO", prep, "IMPPP", "prep1")
    accept("IMPO", "imp_a")
    accept("IMPEMB", "imp_b")
    loop("IMPPP", np_in)
    go("IMPPP", N, "IMPPPO", "pobj1")
    accept("IMPPPO", "imp_a")

    go("VOC", name_l, "VOC2", "voc")
    accept("VOC2", "voc")
    go("VOC2", comma, "VOC3")
    go("VOC3", V, "IMPV2")
    accept("IMPV2", "voc")

    # ---- questions funnel back into the spine -------------------------------
    loop("QA", np_in)
    go("QA", N, "QS", "subj")
    go("QA", prep, "PP1", "prep1")            # "What is in the nest?"
    go("QS", V, "VP", "verb")                 # "Can Ann fan the lad?"
    loop("QS", np_in)
    go("QS", N, "OBJ", "obj")                 # "Has Ann a hat?"
    go("QS", adj, "COPX", "adj")              # "Is the cat black?"
    go("QS", adv, "COPX", "adj")
    go("QS", prep, "PP1", "prep1")            # "Is the cat on the mat?"
    go("QS", neg, "QS", "neg")
    go("WHQ", Or((cop, aux)), "QA", "verb")
    go("WHQ", mod_l, "QA", "mod")

    # ---- second clause ------------------------------------------------------
    go("CC", conj, "C2S", "cnj")
    go("C2S", np_in, "C2SN")
    loop("C2SN", np_in)
    loop("C2S", adv)
    go("C2S", N, "C2F", "b_subj")
    go("C2SN", N, "C2F", "b_subj")
    go("C2F", V, "C2V", "b_verb")
    go("C2F", cop, "C2V", "b_verb")
    loop("C2V", np_in)
    loop("C2V", adv)
    go("C2V", N, "C2O", "b_obj")
    go("C2V", adj, "C2O", "b_adj")
    accept("C2V", "decl_a", second=True)
    accept("C2O", "decl_a", second=True)

    # ---- growth iteration 2 (failure-driven) -----------------------------
    # do-imperative: "Do not rob the nest."
    go("S0", aux, "DOIMP", "mod", 0.4)
    go("DOIMP", neg, "DOIMP", "neg")
    go("DOIMP", V, "IMP", "verb")
    # predicate possessive: "The lamp is Nat's."
    go("COPS", HasLabel("POSS"), "COPX", "adj")
    # noun-noun compounds: re-capture the head ("a pet bird")
    nn = And((N, Not(V), Not(HasLabel("PRON"))))
    go("FRAGN", nn, "FRAGN", "subj")
    go("FRAGD", nn, "FRAGD", "subj")
    go("OBJ", nn, "OBJ", "obj")
    go("COPX", nn, "COPX", "obj")
    go("IMPO", nn, "IMPO", "obj")
    go("PP1O", nn, "PP1O", "pobj1")
    # appositive: "Nat's dog, Rab, can not catch the rat." — only from
    # subjects that cannot be verbs (else "Run, Spot, run!" is swallowed)
    go("FRAGN", comma, "APP")
    go("FRAGD", comma, "APP")
    go("APP", name_l, "APP", "subj")        # re-capture the head
    go("APP", comma, "FRAGN")               # close of appositive
    # wh-NP questions: "What bird is this?"
    loop("WHQ", np_in)
    go("WHQ", N, "WHN", "subj")
    go("WHN", Or((cop, V)), "VP", "verb")
    # subject-sharing second VP: "Nell sees the ducks, and will feed them."
    loop("C2S", mod_l)
    loop("C2S", neg)
    go("C2S", V, "C2V", "b_verb")
    go("C2S", cop, "C2V", "b_verb")

    # ---- growth iteration 3 (failure-driven) -----------------------------
    loop("C2V", neg)                       # "his dog is not fat"
    loop("EMB", np_in)                     # "let the cat get her five eggs"
    b.transition(st["EMB"], N, st["EMB"])  # consume embedded object (uncaptured)
    loop("S0", conj)                       # "Yes; there are five of them."
    # sentence-initial PP: "At night they come to the barn."
    go("S0", prep, "SPP", "prep2")
    loop("SPP", np_in)
    go("SPP", N, "SPPO", "pobj2")
    loop("SPPO", comma)
    go("SPPO", N, "FRAGN", "subj")
    return b.build()


@lru_cache(maxsize=1)
def _machine() -> FSM:
    return build_clause_story()


# --- Compile + projection (primer's pattern, cross-slot operands) ----------------


@dataclass
class Instruction:
    op: str
    operand: Any = None
    slot_id: str = ""
    rank: int = 0
    weight: float = 1.0

    def __str__(self) -> str:
        return f"{self.op} {self.operand}" if self.operand is not None else self.op


@dataclass
class CompileResult:
    state: ParserState
    program: list[Instruction]
    errors: list[str]


_EXEC = re.compile(r"EXEC\.(\d+):([A-Z_]+)(?:\((.*)\))?$")
_REF = re.compile(r"!\{(\w+)(?:@([\w:]+))?\}$")


def _resolve_operand(state: ParserState, slot: Slot, ref: str) -> Any:
    m = _REF.match(ref)
    if not m or m.group(1) != "VAL":
        # an uninterpolated template ({reg} never captured) is an
        # absent-constituent reference: drop, like an empty anchor
        return None
    target = state.get_slot(m.group(2)) if m.group(2) else slot
    if target is None:
        return None
    vals = sorted(
        ((w, lab) for lab, w in target.labels.items() if lab.startswith("VAL:")),
        reverse=True,
    )
    if not vals:
        return None
    return vals[0][1].split(":", 1)[1]


def compile_text(text: str) -> CompileResult:
    state = initialize(text)
    scanner = FSMScanner()
    machine = _machine()

    slots = state.tokens
    sentence: list[Slot] = []
    for slot in slots:
        sentence.append(slot)
        if "PUNCT" in slot.labels:
            ids = {s.id for s in sentence}
            deltas = scanner.transduce(
                machine, state, anchored=True,
                slot_filter=lambda s, ids=ids: s.id in ids,
            )
            apply_deltas(state, deltas)
            sentence = []

    program: list[Instruction] = []
    for slot in slots:
        per_rank: dict[int, tuple[float, str, str | None]] = {}
        for lab, w in slot.labels.items():
            match = _EXEC.match(lab)
            if not match:
                continue
            rank, op, arg = int(match.group(1)), match.group(2), match.group(3)
            if rank not in per_rank or w > per_rank[rank][0]:
                per_rank[rank] = (w, op, arg)
        for rank in sorted(per_rank):
            w, op, arg = per_rank[rank]
            operand = _resolve_operand(state, slot, arg) if arg else None
            if arg and operand is None:
                continue  # cross-slot ref into an unwritten register
            program.append(Instruction(op=op, operand=operand,
                                       slot_id=slot.id, rank=rank, weight=w))

    errors = sorted({lab for s in slots for lab in s.labels.weights
                     if lab.startswith("ERROR:")})
    return CompileResult(state=state, program=program, errors=errors)


# --- Frame-builder VM (primer's, grown) ---------------------------------------------


@dataclass
class RunResult:
    frames: list[dict]
    valid: bool = True


def run_program(program: list[Instruction]) -> RunResult:
    stack: list[Any] = []
    frames: list[dict] = []

    def fail() -> RunResult:
        return RunResult(frames=frames, valid=False)

    def top_frame() -> dict | None:
        return stack[-1] if stack and isinstance(stack[-1], dict) else None

    for ins in program:
        if ins.op == "ENT":
            stack.append(ins.operand)
        elif ins.op == "IMPYOU":
            stack.append("you")
        elif ins.op in ("EVT", "INTRO"):
            stack.append({"pred": ins.operand if ins.op == "EVT" else "intro"})
        elif ins.op == "AGENT":
            if not stack:
                return fail()
            top = stack.pop()
            if isinstance(top, dict):
                if stack and not isinstance(stack[-1], dict):
                    top["agent"] = stack.pop()
                stack.append(top)   # subjectless (existential): no-op
            else:
                if not stack or not isinstance(stack[-1], dict):
                    return fail()
                stack[-1]["agent"] = top
        elif ins.op == "THEME":
            if len(stack) < 2 or not isinstance(stack[-2], dict):
                return fail()
            v = stack.pop()
            stack[-1]["theme"] = v
        elif ins.op == "ATTR":
            f = top_frame()
            if f is None:
                return fail()
            f["attr"] = ins.operand
        elif ins.op == "GROUP":
            if len(stack) < 2:
                return fail()
            e2, e1 = stack.pop(), stack.pop()
            stack.append([e1, e2])
        elif ins.op == "PREP":
            if len(stack) < 2 or not isinstance(stack[-2], dict):
                return fail()
            v = stack.pop()
            stack[-1][ins.operand] = v
        elif ins.op == "AGENTI":
            # inverted-order agent attach: entity on top of a frame;
            # no-op otherwise (the verb-anchored AGENT handled it)
            if (len(stack) >= 2 and not isinstance(stack[-1], dict)
                    and isinstance(stack[-2], dict)
                    and "agent" not in stack[-2]):
                val = stack.pop()
                stack[-1]["agent"] = val
        # lenient modifiers: degrade rather than fail on order edge cases
        elif ins.op == "MOD":
            f = top_frame()
            if f is not None and ins.operand:
                f["mod"] = ins.operand
        elif ins.op == "NEGSET":
            f = top_frame()
            if f is not None:
                f["neg"] = True
        elif ins.op == "WH":
            f = top_frame()
            if f is not None and ins.operand:
                f["wh"] = ins.operand
        elif ins.op == "MOODQ":
            f = top_frame()
            if f is not None:
                f["mood"] = "q"
        elif ins.op == "END":
            if not stack or not isinstance(stack[-1], dict):
                return fail()
            frames.append(stack.pop())
        else:
            raise ValueError(f"unknown instruction {ins.op}")
    return RunResult(frames=frames, valid=not stack)


def parse(text: str) -> list[dict] | None:
    result = compile_text(text)
    if result.errors:
        return None
    res = run_program(result.program)
    return res.frames if res.valid else None
