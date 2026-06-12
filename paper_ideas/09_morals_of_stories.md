# Recognizing the Moral of the Story: Narrative-Arc Machines Over Folk Tales

**Target venue:** speculative/ambitious — Computational Models of
Narrative venue (CMN/AIIDE narrative track); arXiv. The reach paper;
needs the most new work and is the most distinctive if it lands.

## Core claim

Story machines recognize clause structure; the same construction one
level up — machines whose alphabet is *frames* and whose states are
*arc positions* — can recognize narrative structure: setup, violation,
consequence, resolution. Propp's morphology of the folktale is
literally a finite-state grammar over narrative functions; we propose
implementing it as an accretion layer over the frame stream produced by
parsing, on a public-domain folk-tale corpus (Beacon Second Reader,
Fifty Famous Stories Retold — included in the repository). The target
output is the smallest honest version of "the moral": a frame relating
a character's choice to its outcome (persistence -> success in Bruce
and the Spider; humility violated -> rebuke in King Alfred), emitted
with provenance to the supporting story frames, weighted, and wrong
only legibly.

## What exists

The frame-producing parser for primer-register English; the corpus
(four tiers, narrative order preserved); the per-entity memory
machines (proposal 04) that arc recognition needs (who wanted what,
who did what to whom, what changed).

## Experiments needed

1. Extend the parser's grammar toward tier 3-4 coverage (the largest
   work item; LLM-as-annotator from proposal 07 is the intended lever).
2. Hand-author arc machines for 3-5 Proppian shapes; hand-validate
   against ~20 tales; measure arc detection and moral-frame extraction
   against human judgments.
3. The honest negative space: tales whose moral resists frame-relation
   form tell us where the representation stops.

## Related work

Propp; story grammars (Rumelhart) and their critiques (Black & Wilensky
— must be engaged seriously); Schank's TAUs/MOPs; modern narrative
schema induction (Chambers & Jurafsky); LLM moral/theme extraction as
the fluent-but-unauditable contrast.

## Risks

Highest of the set: story grammars have a contested history, and
"moral" is a strong word. The defensible claim is the auditable
pipeline (text -> frames -> arcs -> moral-frame with provenance), not
human-level theme understanding.
