# "Because She Kissed Mark": NPC Inference and Explanation as Provenance Traversal

**Target venue:** AIIDE/FDG (companion to 04, or merged with it); CHI
PLAY for the player-facing angle.

## Core claim

If an agent's beliefs are weighted labels acquired by parsing
utterances into semantic frames, and its inferences are made by
finite-state "scripts" pattern-matching over the belief stream (a
second stream in the same engine that parses text), then **explanation
is provenance traversal**: an inferred belief carries derived_from
edges to its source beliefs and to the script that fired, so the NPC's
answer to "why do you think that?" is a mechanical read of the
inference chain — truthful by construction, for learned (not authored)
beliefs. Player: "Jack is angry at Mary." Later: "Mary kissed Mark."
A jealousy script links them; the NPC can say "Jack is angry at Mary
because she kissed Mark" — and the *because* is data, not prose. None
of it need be true: belief weight = source confidence x trust x script
strength (a semiring), so misinformation, gossip, and being wrong for
legible reasons are emergent, and the audit trail shows which trusted
source poisoned which inference.

## What exists

The parser (early-reader English -> frames), multi-stream state with
slot provenance, the weighted machinery, and the inference-script
pattern (identical to the implemented label-pattern emitters). Missing:
the generation direction (frames -> English) and the belief-stream
wiring — both specified.

## Experiments needed

1. The end-to-end demo as a test: hear two sentences, infer, explain;
   assert the explanation against the provenance graph.
2. Deception study: player lies; trace the audit trail; measure
   belief-revision behavior under contradiction (superposed beliefs,
   decay).
3. Small user study: do players find provenance-grounded explanations
   more believable/manipulable (in the good, gameplay sense) than
   canned or LLM-generated ones?

## Related work

Schank (scripts, explanation); truth-maintenance systems (Doyle) — the
classical ancestor of belief provenance; epistemic logic in games;
generative-agent papers (memory + reflection via LLM) as contrast:
fluent but unauditable explanation vs mechanical but truthful.

## Why this might land

It converts a research-ethics property (auditability) into a gameplay
feature (NPCs that can be cross-examined). Reviewers at these venues
reward exactly that move.
