# Running the primer language

Status: **implemented**, runner `fsm_parser.primer_lang`, hand-validated
golden suite `src/tests/test_primer_lang.py` (16 tests). No
differential — English has no oracle; see PERSPECTIVE.md.

```python
from fsm_parser.primer_lang import parse, compile_text

parse("See Spot run.")
# [{'pred': 'see', 'agent': 'you', 'theme': {'pred': 'run', 'agent': 'spot'}}]

r = compile_text("Play is fun.")
{l: round(w, 2) for l, w in r.state.get_slot("token:0").labels.items()
 if l.startswith("STORY")}
# {'STORY:IMP': 0.55, 'STORY:DECL': 0.45}  <- the superposition
```

Reading the field: STORY:*/ROLE:* labels are EAGER (every live story
emits them with its path weight as it consumes — including stories
that later die). EXEC.* labels are CONFIRMED (only emitted on the
sentence-final punctuation transition, capture-anchored back onto
constituent slots, by stories that survived). A token's eager labels
tell you what was considered; its EXEC labels tell you what the
sentence turned out to be.

## Spec-to-code map

| spec feature | implementation |
|---|---|
| weighted lexicon | `LEXICON` dict in `initialize()` — first weighted labels in a runner |
| the fork | two S0 transitions with prior weights 0.55/0.45 on V&N tokens — first nondeterministic weighted anchored machine |
| eager vs confirmed | transition emissions vs PUNCT-transition emissions with CaptureAnchors |
| per-sentence anchoring | `transduce(anchored=True, slot_filter=...)` — slot_filter's first use; dead sentences cannot strand the text |
| frame builder | `run_program()` — ENT/IMPYOU/EVT/AGENT/THEME/ATTR/GROUP/END; AGENT is polymorphic (subject-below for SV, entity-above for vocatives) |
| projection | per (slot, rank) max-weight; argmax WITHOUT the margin error (NL commits to the best story) |
