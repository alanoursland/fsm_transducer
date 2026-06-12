# Running the Python subset

Status: **implemented**, runner `fsm_parser.pysub_lang`, golden suite
`src/tests/test_pysub_lang.py`, differential against **real Python**:
the generated source is executed directly with
`exec(src, {"print": out.append})` — same text, two engines.

```python
from fsm_parser.pysub_lang import compile_program, run_program, execute

src = "x = 3\nif x > 1:\n    print(x)\n"
r = compile_program(src)
[str(i) for i in r.program]
# ['PUSH 3', 'STORE x', 'LOAD x', 'PUSH 1', 'GT',
#  'BRF', 'ENTER', 'LOAD x', 'PRINT', 'EXIT']
execute(src).outputs     # [3]
```

New in the label field: layout slots (kind `layout`, ids `layout:n`,
no source span) carrying NEWLINE / INDENT / DEDENT — inspect them with
`[s for s in r.state.tokens if s.kind == "layout"]`. Statement
completions land on NEWLINE slots; ENTER/EXIT on INDENT/DEDENT slots.

## Spec-to-code map

| spec feature | implementation |
|---|---|
| layout synthesis | `initialize()` — indent-stack algorithm, one slot per DEDENT pop |
| paren tracker | **imported from imp** (`build_bracket_tracker`; brace transitions dead) |
| minus story machine | **imported from imp** (`build_minus_story`, unchanged) |
| expression emitters | **imported from imp** (`_expression_emitters`, unchanged) |
| target marking | `build_target_marker()` — `<IDENT> <ASSIGN>` reflex, because Python announces bindings after the name |
| assignment checkers | `build_assign_checker(name)` — 2 states, input-indexed |
| statement emitters | NEWLINE-terminated; BRF on `:`, ENTER/EXIT on layout slots |
| VM | single environment; ENTER/EXIT are pure BRF-matching markers |

The headline: three of the four machine layers are imp's, imported
unchanged. The canonical pysub program compiles to the same
instruction sequence as the canonical imp program (test-asserted) —
the interlingua claim's first running instance.
