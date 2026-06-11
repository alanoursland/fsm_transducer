# Language definition: S-expressions (Lisp subset)

Third language in the format of `languages/arithmetic/` and
`languages/json/` (conventions inherited; read those first).

Scope: symbols, integers, lists, nesting to **K = 3**, multiple
top-level forms. No quote sugar, strings, or evaluation (see
exclusions).

## What this language tests

* **Recursive symbolic structure with trivial tokenization.** Atoms are
  any run of non-paren, non-whitespace characters; there are exactly
  three token classes. All the difficulty is structural, none lexical —
  the complement of JSON.
* **Positional roles.** A list's first element is its HEAD; the rest
  are ARGs. The anchored tracker must know whether the *next* element
  at each level is in head position, so its stack alphabet is
  expectation states — completing a progression across the three
  languages:

  | language | tracker stack alphabet | states (K=3) |
  |---|---|---|
  | arithmetic | unary (depth only) | 5 |
  | json | container type {O, A} | 15 + overflow |
  | sexpr | expectation {head-pending, in-body} | 15 + overflow |

  `ROLE:HEAD:d` / `ROLE:ARG:d` are the first *grammatical relation*
  labels in the project — the structural analog of predicate/argument
  marking, which is the direction natural language lies in.
* **Multiple top-level forms.** The output contract generalizes: the VM
  stack ends holding the *sequence* of top-level forms, not one
  document. Validity condition 1 becomes "stack nonempty and every
  entry a completed form".

## Files

| file | contents |
|---|---|
| `lexicon.yaml` | three token classes |
| `layers.yaml` | shape/role tracker + emitter schemas |
| `instructions.yaml` | three-op builder instruction set |
| `examples.md` | hand-validated worked examples |
| `RUNNING.md` | runner usage and interpretation |
| `PERSPECTIVE.md` | LLM design-rationale introspection |

Runner: `fsm_parser.sexpr_lang`. Tests: `src/tests/test_sexpr_lang.py`
(golden + round-trip differential: random structures rendered and
re-parsed must equal themselves).

## Deliberate exclusions

* `'x` quote sugar — pure reader macro; one extra emitter when wanted;
* strings, floats, rationals — lexical detail for the char-level layer;
* evaluation — this parser builds structure; `(+ 1 2)` compiles to a
  list whose head is the symbol `+`, full stop. Evaluation is a
  downstream consumer of the field (and arithmetic already covers the
  compile-to-execution story);
* arity/special-form checking (`define`, `lambda`) — would be the first
  *semantic* layer reading ROLE labels; noted as the natural v2.
