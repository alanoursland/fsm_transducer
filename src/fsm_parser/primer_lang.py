"""Runner for the early-reader English language (languages/primer/).

The first natural language and the first weighted machinery in use:

* the lexicon emits WEIGHTED labels (play: V 0.55 / N 0.45);
* the clause story machine is NONDETERMINISTIC: at sentence start an
  N/V-ambiguous word forks it into an imperative story and a
  subject story, both carried as weighted paths by the engine's
  semiring frontier (built in v2, idle for seven languages);
* eager emissions (STORY:*, ROLE:*) fire with path weight as each
  story consumes — the superposition record, never retracted;
* confirmed emissions (the EXEC frame ops) fire only on the
  sentence-final PUNCT transition, capture-anchored back onto the
  constituent slots — dead stories never reach them.

The machine runs anchored PER SENTENCE (transduce's slot_filter —
also never used until now), so an unparseable sentence leaves only
its eager labels and zero frames without stranding later sentences.

Output: semantic frames. 'See Spot run.' compiles to
IMPYOU; EVT see; AGENT; ENT spot; EVT run; AGENT; THEME; END
=> {pred: see, agent: you, theme: {pred: run, agent: spot}}.

There is no external oracle for English; goldens are hand-validated
(see PERSPECTIVE.md for why that is the permanent condition of the
domain and what the recorded path to scale is).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

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
)
from fsm_parser.normalization import apply_deltas
from fsm_parser.slots import Slot, SourceSpan
from fsm_parser.tokens import ParserState

LEXICON: dict[str, dict[str, float]] = {
    "spot": {"N": 1.0, "NAME": 1.0}, "dick": {"N": 1.0, "NAME": 1.0},
    "jane": {"N": 1.0, "NAME": 1.0}, "sally": {"N": 1.0, "NAME": 1.0},
    "puff": {"N": 1.0, "NAME": 1.0},
    "ball": {"N": 1.0}, "boat": {"N": 1.0}, "cat": {"N": 1.0}, "dog": {"N": 1.0},
    "play": {"V": 0.55, "N": 0.45},
    "run": {"V": 0.7, "N": 0.3},
    "look": {"V": 0.8, "N": 0.2},
    "see": {"V": 1.0}, "sees": {"V": 1.0}, "runs": {"V": 1.0},
    "plays": {"V": 1.0}, "looks": {"V": 1.0}, "go": {"V": 1.0},
    "jump": {"V": 1.0}, "jumps": {"V": 1.0},
    "is": {"COP": 1.0}, "are": {"COP": 1.0},
    "the": {"DET": 1.0}, "a": {"DET": 1.0},
    "red": {"ADJ": 1.0}, "big": {"ADJ": 1.0}, "little": {"ADJ": 1.0},
    "fun": {"ADJ": 1.0},
    "and": {"CONJ": 1.0},
    "i": {"PRON": 1.0, "N": 1.0}, "you": {"PRON": 1.0, "N": 1.0},
    "we": {"PRON": 1.0, "N": 1.0},
}

_TOKEN = re.compile(r"[A-Za-z]+|[.!?,]")

# fork priors per ambiguity class (static transition weights; reading
# them from the lexicon labels is the recorded engine extension)
P_IMP, P_SUBJ = 0.55, 0.45


# --- Layer 0: tokenization + weighted lexicon -----------------------------------


def initialize(text: str) -> ParserState:
    state = ParserState()
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
        if word in LEXICON:
            for lab, w in LEXICON[word].items():
                slot.labels.add(lab, w)
            slot.labels.add(f"VAL:{word}", 1.0)
        elif raw == ",":
            slot.labels.add("COMMA", 1.0)
        elif raw in ".!?":
            slot.labels.add("PUNCT", 1.0)
        else:
            slot.labels.add("ERROR:UNKNOWN_WORD", 1.0)
        state.add_slot("token", slot)
    return state


# --- Layer 1: the clause story machine -------------------------------------------


def _ex(label: str, anchor_reg: str | None = None) -> Emission:
    if anchor_reg is None:
        return Emission(label, 1.0, offset=0)
    return Emission(label, 1.0, anchor=CaptureAnchor(anchor_reg))


def build_clause_story() -> FSM:
    """One sentence's worth of clause grammar, weighted and forked.

    Run anchored per sentence. Eager STORY/ROLE labels on consuming
    transitions; the full EXEC set on the PUNCT (accept) transition,
    anchored at captured constituent slots.
    """
    b = FSMBuilder("clause_story")
    (s0, imp, imp_det, imp_obj, imp_emb, voc, voc2, voc3, imp_v2,
     subj_det, subj, subj_and, subj2, vp, vp_g, obj_det, obj, emb,
     copula, cop_adj, done) = [
        b.state(n) for n in (
            "S0", "IMP", "IMP_DET", "IMP_OBJ", "IMP_EMB", "VOC", "VOC2",
            "VOC3", "IMP_V2", "SUBJ_DET", "SUBJ", "SUBJ_AND", "SUBJ2",
            "VP", "VP_G", "OBJ_DET", "OBJ", "EMB", "COPULA", "COP_ADJ",
            "DONE",
        )
    ]
    b.start(s0)
    b.accept(done)

    V, N = HasLabel("V"), HasLabel("N")
    name, det = HasLabel("NAME"), HasLabel("DET")
    cop, adj = HasLabel("COP"), HasLabel("ADJ")
    conj, comma, punct = HasLabel("CONJ"), HasLabel("COMMA"), HasLabel("PUNCT")
    v_only, n_only = And((V, Not(N))), And((N, Not(V)))
    v_and_n = And((V, N))

    cap = {r: Capture(r, kind="index") for r in
           ("subj", "subj2", "verb", "obj", "verb2", "voc", "adj")}

    # ---- sentence start: the fork ------------------------------------
    for cond, w in ((v_only, 1.0), (v_and_n, P_IMP)):
        b.transition(s0, cond, imp, weight=w, captures=[cap["verb"]],
                     emissions=[_ex("STORY:IMP")])
    for cond, w in ((n_only, 1.0), (v_and_n, P_SUBJ)):
        b.transition(s0, cond, subj, weight=w, captures=[cap["subj"]],
                     emissions=[_ex("STORY:DECL")])
    b.transition(s0, det, subj_det, emissions=[_ex("STORY:DECL")])
    b.transition(subj_det, N, subj, captures=[cap["subj"]],
                 emissions=[_ex("ROLE:SUBJ")])

    # ---- declaratives -------------------------------------------------
    b.transition(subj, V, vp, captures=[cap["verb"]], emissions=[_ex("ROLE:VERB")])
    b.transition(subj, cop, copula, captures=[cap["verb"]], emissions=[_ex("ROLE:COP")])
    b.transition(subj, conj, subj_and)
    b.transition(subj_and, N, subj2, captures=[cap["subj2"]],
                 emissions=[_ex("ROLE:SUBJ")])
    b.transition(subj2, V, vp_g, captures=[cap["verb"]], emissions=[_ex("ROLE:VERB")])

    b.transition(vp, det, obj_det)
    b.transition(vp, N, obj, captures=[cap["obj"]], emissions=[_ex("ROLE:OBJ")])
    b.transition(obj_det, N, obj, captures=[cap["obj"]], emissions=[_ex("ROLE:OBJ")])
    b.transition(obj, V, emb, captures=[cap["verb2"]], emissions=[_ex("ROLE:VERB2")])

    decl_core = [_ex("EXEC.0:ENT(!{VAL})", "subj"),
                 _ex("EXEC.1:EVT(!{VAL})", "verb"),
                 _ex("EXEC.2:AGENT", "verb")]
    b.transition(vp, punct, done,
                 emissions=decl_core + [_ex("EXEC.0:END")])
    b.transition(obj, punct, done,
                 emissions=decl_core + [_ex("EXEC.0:ENT(!{VAL})", "obj"),
                                        _ex("EXEC.3:THEME", "obj"),
                                        _ex("EXEC.0:END")])
    b.transition(emb, punct, done,
                 emissions=decl_core + [_ex("EXEC.0:ENT(!{VAL})", "obj"),
                                        _ex("EXEC.1:EVT(!{VAL})", "verb2"),
                                        _ex("EXEC.2:AGENT", "verb2"),
                                        _ex("EXEC.3:THEME", "verb2"),
                                        _ex("EXEC.0:END")])
    b.transition(vp_g, punct, done,
                 emissions=[_ex("EXEC.0:ENT(!{VAL})", "subj"),
                            _ex("EXEC.0:ENT(!{VAL})", "subj2"),
                            _ex("EXEC.1:GROUP", "subj2"),
                            _ex("EXEC.1:EVT(!{VAL})", "verb"),
                            _ex("EXEC.2:AGENT", "verb"),
                            _ex("EXEC.0:END")])

    # ---- copula --------------------------------------------------------
    b.transition(copula, adj, cop_adj, captures=[cap["adj"]],
                 emissions=[_ex("ROLE:ATTR")])
    b.transition(cop_adj, punct, done,
                 emissions=[_ex("EXEC.0:ENT(!{VAL})", "subj"),
                            _ex("EXEC.1:EVT(!{VAL})", "verb"),
                            _ex("EXEC.2:AGENT", "verb"),
                            _ex("EXEC.2:ATTR(!{VAL})", "adj"),
                            _ex("EXEC.0:END")])

    # ---- imperatives -----------------------------------------------------
    imp_core = [_ex("EXEC.0:IMPYOU", "verb"),
                _ex("EXEC.1:EVT(!{VAL})", "verb"),
                _ex("EXEC.2:AGENT", "verb")]
    b.transition(imp, n_only, imp_obj, captures=[cap["obj"]],
                 emissions=[_ex("ROLE:OBJ")])
    b.transition(imp, det, imp_det)
    b.transition(imp_det, N, imp_obj, captures=[cap["obj"]],
                 emissions=[_ex("ROLE:OBJ")])
    b.transition(imp, punct, done, emissions=imp_core + [_ex("EXEC.0:END")])
    b.transition(imp_obj, V, imp_emb, captures=[cap["verb2"]],
                 emissions=[_ex("ROLE:VERB2")])
    b.transition(imp_obj, punct, done,
                 emissions=imp_core + [_ex("EXEC.0:ENT(!{VAL})", "obj"),
                                       _ex("EXEC.3:THEME", "obj"),
                                       _ex("EXEC.0:END")])
    b.transition(imp_emb, punct, done,
                 emissions=imp_core + [_ex("EXEC.0:ENT(!{VAL})", "obj"),
                                       _ex("EXEC.1:EVT(!{VAL})", "verb2"),
                                       _ex("EXEC.2:AGENT", "verb2"),
                                       _ex("EXEC.3:THEME", "verb2"),
                                       _ex("EXEC.0:END")])

    # ---- vocative imperative: "Run, Spot, run!" -----------------------------
    b.transition(imp, comma, voc)
    b.transition(voc, name, voc2, captures=[cap["voc"]],
                 emissions=[_ex("ROLE:VOC")])
    b.transition(voc2, comma, voc3)
    b.transition(voc3, V, imp_v2)
    b.transition(imp_v2, punct, done,
                 emissions=[_ex("EXEC.1:EVT(!{VAL})", "verb"),
                            _ex("EXEC.0:ENT(!{VAL})", "voc"),
                            _ex("EXEC.2:AGENT", "voc"),
                            _ex("EXEC.0:END")])
    return b.build()


@lru_cache(maxsize=1)
def _machine() -> FSM:
    return build_clause_story()


# --- Compile -----------------------------------------------------------------------


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


def _resolve_operand(slot: Slot, ref: str) -> Any:
    if ref != "!{VAL}":
        raise ValueError(f"unsupported operand reference: {ref!r}")
    vals = sorted(
        ((w, lab) for lab, w in slot.labels.items() if lab.startswith("VAL:")),
        reverse=True,
    )
    if not vals:
        raise ValueError(f"no VAL label on {slot.id}")
    # NL projection: argmax WITHOUT a margin error — commit to the best
    return vals[0][1].split(":", 1)[1]


def compile_text(text: str) -> CompileResult:
    state = initialize(text)
    scanner = FSMScanner()
    machine = _machine()

    # one anchored run per sentence (slot_filter keeps stories from one
    # sentence from leaking into the next, and a dead sentence cannot
    # strand the rest of the text)
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
            # collision rule: max weight wins (two confirmed stories)
            if rank not in per_rank or w > per_rank[rank][0]:
                per_rank[rank] = (w, op, arg)
        for rank in sorted(per_rank):
            w, op, arg = per_rank[rank]
            operand = _resolve_operand(slot, arg) if arg else None
            program.append(Instruction(op=op, operand=operand,
                                       slot_id=slot.id, rank=rank, weight=w))

    errors = sorted({lab for s in slots for lab in s.labels.weights
                     if lab.startswith("ERROR:")})
    return CompileResult(state=state, program=program, errors=errors)


# --- The frame-builder VM --------------------------------------------------------------


@dataclass
class RunResult:
    frames: list[dict]
    valid: bool = True


def run_program(program: list[Instruction]) -> RunResult:
    stack: list[Any] = []
    frames: list[dict] = []

    def fail() -> RunResult:
        return RunResult(frames=frames, valid=False)

    for ins in program:
        if ins.op == "ENT":
            stack.append(ins.operand)
        elif ins.op == "IMPYOU":
            stack.append("you")
        elif ins.op == "EVT":
            stack.append({"pred": ins.operand})
        elif ins.op == "AGENT":
            # polymorphic: frame-on-top (subject below, English SV) or
            # entity-on-top (vocative names the addressee after the verb)
            if not stack:
                return fail()
            top = stack.pop()
            if isinstance(top, dict):
                if not stack:
                    return fail()
                top["agent"] = stack.pop()
                stack.append(top)
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
            if not stack or not isinstance(stack[-1], dict):
                return fail()
            stack[-1]["attr"] = ins.operand
        elif ins.op == "GROUP":
            if len(stack) < 2:
                return fail()
            e2, e1 = stack.pop(), stack.pop()
            stack.append([e1, e2])
        elif ins.op == "END":
            if not stack or not isinstance(stack[-1], dict):
                return fail()
            frames.append(stack.pop())
        else:
            raise ValueError(f"unknown instruction {ins.op}")
    return RunResult(frames=frames, valid=not stack)


def parse(text: str) -> list[dict] | None:
    """Frames for the text; None only on unknown words (everything else
    degrades to fewer frames, never to an exception)."""
    result = compile_text(text)
    if result.errors:
        return None
    res = run_program(result.program)
    return res.frames if res.valid else None
