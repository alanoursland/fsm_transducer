# Parsing as Accretion

A note on the conceptual stance behind this parser, written down because the implementation makes the stance hard to see — every line of code in `src/` looks like FSM bookkeeping, but the architecture is making a specific claim about what parsing *is*.

## The claim

Most parsers are decision machines. Given an input, they output a structure: a constituency tree, a dependency graph, an alignment, a labeled bracketing. The parser's job is to pick one. Even probabilistic parsers, which assign weights to many candidate structures internally, are usually evaluated and consumed by selecting the maximum-likelihood one.

This parser is not a decision machine. It is an accretion machine. Given an input, it adds weighted labels to tokens — over and over, in layers, with old labels decaying as new ones accumulate. The parser never picks a structure. It produces a weighted annotation field over the original token sequence and stops. If a tree or graph or frame is needed, a separate downstream step reads one off the labels.

The claim hidden in this is that structure is not a thing parsers should commit to. Commitment is a downstream concern.

## What "decision" smuggles in

A constituency parser that returns a tree is implicitly answering several questions at once:

- Which tokens form a constituent at all?
- What category does each constituent have?
- What is its head?
- How do constituents nest?

These are not the same question, and they have different evidential bases. Whether `the cat` is a noun phrase has very different evidence behind it than whether the entire sentence is declarative or interrogative. Forcing them into a single output object — a tree — couples decisions that would be cleaner kept separate. A confidently identified NP can sit underneath a wildly uncertain top-level structure, but a tree gives them a single "is the parse correct" status.

Dependency parsers are slightly less coupled — each edge can be evaluated independently — but they still commit to a single edge per dependent. Soft variants exist, but at evaluation time they're usually argmaxed.

The accretion architecture refuses this coupling. Every label is its own claim with its own weight. If `cat` has `NOUN=0.45` and `VERB=0.18` and `PHRASE:NP_HEAD=0.31` and `ROLE:SUBJECT_CANDIDATE=0.22`, that's the parser's actual state. The downstream consumer can take the max, take the top-k, threshold, sample, or just look. The parser is not lying by reporting all of it.

## What you give up

You give up the convenience of a single answer. Anyone hoping to plug this parser into a pipeline that wants `tree.root.children[0].head` will have to write a projection step.

You give up the ability to express constraints that hold across an entire structure. A parser that builds a tree can guarantee non-crossing brackets; this parser cannot. If two FSMs emit conflicting span labels, the conflict shows up as conflicting label distributions, not as a structural impossibility the parser refuses to produce. Some applications want the structural guarantees.

You give up training data compatibility. Most syntactic resources are trees. Aligning a label-distribution output to a gold tree requires a metric, and the natural metrics (label-level F1, weighted Jaccard) are not the metrics the rest of the field uses (LAS, UAS, EVALB).

These are real costs. The architecture is not free.

## What you gain

You gain *online* parsing in a strong sense. Each layer transforms the previous layer's labels; intermediate states are inspectable; you can ask the parser what it thinks after layer 2 and after layer 5 and compare. A tree-building parser tends to be all-or-nothing: a complete tree, or a parse failure.

You gain *graceful degradation*. A sentence that none of the FSMs fully match still produces output — just a less-refined label distribution. There is no notion of "no parse." This matters for any application that operates on real text, where a quarter of inputs are fragmentary, ungrammatical, or full of names and constructions the grammar never saw. A decision parser fails on these. An accretion parser produces weak labels and moves on.

You gain *evidential transparency*. Because labels are emitted by named FSMs and accumulated additively, you can ask: which rule contributed how much to which label on which token? The trace files in this project's debug renderer answer that. A neural parser emits a distribution but no narrative; a decision-based symbolic parser emits a narrative but only for the single chosen structure. The accretion parser emits a narrative for every label it produced, including the ones nobody picked.

You gain *deferred commitment*. The parser does not have to choose. The downstream consumer chooses, with whatever criterion suits the task. A QA system might want top-k subject candidates; an information extractor might want one; a dialog state tracker might want the entire distribution. They all call the same parser.

## The cognitive parallel

Humans seem to parse online, accreting, not deciding. The well-studied "garden path" sentences (*The horse raced past the barn fell.*) work specifically because readers do not commit early; they hold multiple parses in some weighted sense and reweight as evidence comes in. Eye-tracking studies show regressions when an early-favoured reading becomes incompatible with later input. Decisions appear to be revisable, sometimes silently, sometimes with effort.

This is not a claim that the parser is psychologically realistic — it isn't, in lots of obvious ways. The point is that an accretion architecture has a natural place for the kind of incremental, ambiguity-tolerant, revisable processing readers seem to do. There is no parse to undo. There is only a label distribution to update.

The decay mechanism is the closest mirror. Labels that were useful early (lexical surface form) lose mass as labels that are useful later (semantic role) gain mass — but only if the later FSMs care to refresh them. A label that nobody refreshes is implicitly forgotten, the way readers seem to forget the surface form of a sentence within seconds while remembering its content much longer. The `FORGOTTEN` accumulator makes that forgetting auditable.

## The Bayesian parallel

In Bayesian inference, the inference step (computing or representing a posterior) is conceptually separate from the decision step (picking an action under a loss function). Conflating them is regarded as a category error. You don't pick a hypothesis during inference; you maintain a distribution. Picking a hypothesis is decision-theoretic: it depends on a utility you might not have at parse time.

The accretion parser is structurally analogous. Inference (label propagation through layered FSMs) produces a distribution. Decision (project a tree, take an argmax, threshold to spans) is downstream and depends on what the consumer needs. The parser does not have to know what the loss function is.

Whether the label weights are *actually* a posterior is a different question — the design doc is honest that they are "salience or activation, not probability." But the *architecture* is Bayesian-shaped: separate the representation of belief from the action taken on that belief. Whether you ever make the weights a real posterior is a choice, not a constraint.

## FORGOTTEN as a deferred-forgetting mechanism

The `FORGOTTEN` label deserves a closer look in this frame. It's not semantic. It's not noise. It's the system's way of admitting "there was weight here, and I let it go." It keeps total mass roughly conserved when weak labels are pruned, so the distribution stays comparable across layers.

Reframed: it is a *deferred* forgetting mechanism. Labels are not deleted at the moment they fall below threshold; they leave behind an accountancy trace. A subsequent layer that needs to know "how much was pruned around here" can read FORGOTTEN. The information is gone in detail but present in aggregate.

Most parsing pipelines have nothing analogous. When a feature is dropped, it's gone, and downstream code has no way to ask. The accretion architecture treats forgetting as a quantity rather than an event. That is consistent with the rest of the architecture: every choice is gradual, every commitment is deferrable, every disappearance leaves a residue.

## The downstream-consumer model

Because the parser does not commit, the question "what is the parse?" must be answered by something else. The architecture pushes this responsibility to a *projection* step — a function from label distribution to whatever object the application wants.

This is unusual but not new. Information retrieval has lived this way for decades: an indexer produces a weighted representation, and the query engine — a separate system — projects that representation into a ranked list of documents. Nobody asks "what is the document?" The indexer is not in the document-selection business.

The same logic applies here. The parser is not in the tree-selection business. The grammar projects spans, the dependency renderer projects edges, the role labeller projects frames — each one separately, each one with its own loss function and its own quality metric.

A consequence: the parser can be used for tasks that don't want trees at all. A discourse-marker classifier just reads `DISCOURSE:CONTRAST` labels off tokens. A coreference resolver reads `MENTION_OF:k` pointers. A sentiment analyzer reads `SENTIMENT:NEG` weights. None of them needs a tree. None of them is poorly served by an architecture that doesn't produce one.

## Where this view becomes uncomfortable

The accretion stance is comfortable as long as labels are local. The moment you want labels that express genuinely non-local relations — nested clauses, scope of negation, long-distance binding — the architecture starts to creak.

The parser can encode some of this with pointer labels (`SUBJECT_OF:k`, `MODIFIES:k`, `CLAUSE_DEPTH:n`). The implementation already produces `DEP:nsubj:2` pointers via captures. But every such label is a small data structure smuggled into a string. Once you have a pointer, you have an edge; once you have edges, you have a graph; once you have a graph, the question "what is the parse?" reasserts itself, and the consumer is now the one doing the work the parser refused to do.

There is a clean version of this objection: the parser is not actually deferring commitment, it is *outsourcing* commitment. The decision still happens. It just happens after the parser has run, in code the parser doesn't own.

That's true. The architecture's claim is weaker than "no decisions are made." The claim is "decisions are not pre-committed." The parser carries the distribution intact to a point where the loss function is known. What the consumer does with it is the consumer's problem, but at least the consumer has the full distribution to work with rather than the parser's preemptive guess.

## The tradeoff in one sentence

A decision parser hands the consumer an answer; an accretion parser hands the consumer the evidence and lets them choose. The first is convenient when the consumer's question matches the parser's; the second is robust when it doesn't, and degrades better when the input is messy. This project bets the second tradeoff is worth making explicit — and that the accretion of weighted labels is a good substrate to bet it on.

The substrate is mostly orthogonal to the bet. You could make the same bet with neural representations (token embeddings as continuous "label distributions") or with a tagger that emits 200 binary features per token. The architectural claim is what matters: don't pick the structure; carry the evidence.

## Open questions for later notes

- Can the label distribution be made into a calibrated posterior, and at what cost?
- Is there a useful intermediate between full structure commitment and full deferral — partial commitments that the parser is willing to make?
- What is the right metric for evaluating an accretion parser against a tree-annotated corpus, beyond projecting and evaluating the projection?
- What kinds of labels become unwieldy in the all-tokens-carry-everything substrate, and what would a hybrid representation that adds proper nodes for genuinely structural information look like?
- How much of the "online reading" intuition holds up if you actually examine human reading data, rather than treating it as a vague analogy?

These are not implementation notes. They are conceptual debts. The point of writing them down is to remember that the architecture took a position, and the position has consequences worth being honest about.
