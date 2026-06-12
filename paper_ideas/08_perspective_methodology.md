# Design Rationale From the Model's Mouth: An Audited Human-LLM Co-Design Method and Its Error Taxonomy

**Target venue:** arXiv (cs.SE/cs.HC); ICSE SEIP / CHI as a stretch.
The methodology paper; the public repository is itself the artifact.

## Core claim

This project was built in working sessions between a human author (who
owned the ideas and direction) and an LLM (which derived, implemented,
and documented under verification). Three methodological artifacts
made the collaboration auditable, and we propose them as a general
method: (1) **spec-first with hand-validated worked examples** — the
examples, computed token-by-token before any implementation, are the
acceptance suite, and caught every design error that fluent
specification prose hid; (2) **PERSPECTIVE documents** — per-component
design-rationale introspections written by the model under explicit
epistemic rules (rationale is reconstructable and checkable; mechanism
claims are not allowed), giving the extraction step itself provenance;
(3) an **error-species ledger** across eight components: every
model-introduced error fell into five species (positional;
quantification-over-paths; resource-budget constants inherited across
boundaries; ordering-budget constants likewise; rationale-coupled rule
deletion), none conceptual, none repeated after first encounter — a
falsifiable characterization of what kind of collaborator a code LLM
is: trust the architecture-level reasoning; mechanically verify
anything with an index, a bound, or a rank in it.

## What exists

Everything: the repo's commit history, eight PERSPECTIVE documents,
the ledger entries, the differential-test catches. The study is
retrospective and fully reproducible from the public record.

## Experiments needed

Framing and coding work, not new construction: systematize the error
ledger against commits; possibly replicate the method on a fresh
component with a second model to test generality.

## Related work

Design rationale capture (gIBIS, QOC); LLM pair-programming studies;
self-explanation faithfulness critiques (the PERSPECTIVE epistemic
header is a direct response to that literature); literate programming
as ancestor.

## Risks

Single-project, single-model case study; the contribution must be the
method and taxonomy, not a generalization claim.
