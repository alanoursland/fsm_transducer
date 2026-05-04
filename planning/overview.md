# Stacked Weighted FSM Parser

## Overview

This document describes a non-neural NLP parser based on stacked weighted finite-state machines. The parser's core operation is simple: it attaches weighted labels to tokens. Each processing block receives a sequence of tokens with labels, applies one or more FSMs, appends new labels, normalizes the label weights, and passes the result to the next block.

The parser does not need to build a tree as its native representation. Instead, it produces an evolving weighted annotation field over the original token sequence. If a tree or dependency structure is needed, it can be projected later from the final labels.

Informal summary: every token carries a bag of labels. Each FSM adds more labels to the bag. Old labels fade when they stop mattering.

## Core Invariant

The parser keeps one fundamental data shape throughout the whole pipeline:

```text
sequence<TokenWithLabels> -> sequence<TokenWithLabels>
```

A token is not treated as a privileged primitive. The token identity itself can be represented as just another label.

For example:

```text
Token 3:
  LEX:book        0.30
  LOWERCASE       0.06
  NOUN            0.24
  VERB            0.14
  NP_HEAD         0.18
  ACTION          0.07
  FORGOTTEN       0.01
```

All labels live in one shared weighted bucket. Lexical labels, part-of-speech labels, phrase labels, semantic labels, and structural labels compete within the same distribution.

## Tokens

A token can be any unit the system chooses to process. It might be a word, subword, punctuation mark, whitespace-sensitive segment, morphological unit, or a higher-level pre-tokenized object.

The parser does not require a permanent distinction between the token and its labels. A token's surface identity may be represented as labels such as:

```text
LEX:book
LOWER:book
SHAPE:lowercase
POSITION:17
```

Early layers may rely heavily on surface and lexical labels. Later layers may allow those labels to decay as more abstract labels become available.

## Labels

Labels are weighted claims attached to tokens. They may describe any property or role of the token.

Examples include:

```text
NOUN
VERB
DET
NP_HEAD
NP_START
NP_END
SUBJECT_CANDIDATE
OBJECT_CANDIDATE
ACTION
ANIMATE_ENTITY
QUESTION_INTENT
```

Labels are not necessarily mutually exclusive in a linguistic sense. Because they share one bucket, their weights should be interpreted as salience, activation, or carried evidence rather than strict probabilities of exclusive categories.

## FSM Blocks

An FSM block is a collection of finite-state machines that operate over the current token-label sequence.

Each FSM reads token labels and emits additional weighted labels. It may inspect raw lexical labels, previous labels added by earlier machines, or abstract labels produced by earlier blocks.

Conceptually:

```text
input labels -> FSM transitions -> emitted label deltas -> appended labels
```

For example:

```text
IF token_i has DET
AND token_i+1 has NOUN_CANDIDATE
THEN add NP_START to token_i
AND add NP_HEAD to token_i+1
AND add NP_END to token_i+1
```

A POS dictionary can be viewed as a simple FSM block. It consumes lexical labels and emits part-of-speech labels:

```text
LEX:book -> NOUN +0.6, VERB +0.5
LEX:dog  -> NOUN +0.8, VERB +0.1
```

In this model, a dictionary is not a special subsystem. It is simply one label-emitting FSM among many.

## Stacking

Blocks are stacked. The output of one block becomes the input of the next.

```text
Block 0: token identity, casing, shape, punctuation
Block 1: lexical and morphological labels
Block 2: POS and local syntactic labels
Block 3: phrase and role labels
Block 4: semantic labels
Block 5: discourse, intent, or task labels
```

The exact layers are not fixed. The important point is that later FSMs operate over richer labels than earlier FSMs.

This allows abstraction to accumulate without requiring long raw-token lookback. A later FSM may not need to inspect ten original words if an earlier block has already labeled a span-like pattern as `NP_HEAD`, `VERB_GROUP`, or `CLAUSE_CANDIDATE`.

## Decay

Earlier labels can decay as parsing progresses. Surface labels and low-level syntactic labels may be useful early but unnecessary later.

For example, `LEX:book` may initially be important for POS labeling. Later, once `NOUN`, `NP_HEAD`, or `RESERVATION_ACTION` has been inferred, the lexical label may lose weight.

Decay keeps the label bucket focused on information that remains useful for future blocks.

A label may survive if later FSMs refresh it. This allows important low-level evidence to persist when needed without making every early label permanent.

## Normalization and Pruning

After each block, a normalization layer stabilizes the label weights.

The normalization layer may:

1. Combine repeated labels.
2. Apply decay to old labels.
3. Add newly emitted labels.
4. Rescale weights.
5. Prune weak labels.
6. Assign pruned weight to a special `FORGOTTEN` label.

The `FORGOTTEN` label is not semantic. It is accounting residue. Its purpose is to preserve normalized mass after weak labels are pruned.

Example:

```text
Before pruning:
  NOUN              0.44
  VERB              0.21
  NP_HEAD           0.20
  RARE_SENSE_17     0.01
  ARCHAIC_USAGE     0.01
  LOW_CONF_SIGNAL   0.01

After pruning:
  NOUN              0.45
  VERB              0.22
  NP_HEAD           0.21
  FORGOTTEN         0.03
```

The expectation is that `FORGOTTEN` remains small as useful new labels are added. It is mostly there to keep the distribution normalized while allowing weak details to disappear.

## Lookback and State

FSMs may use state, bounded lookback, or both.

Without lookback, the FSM state must remember more context. With lookback, transition conditions can directly inspect prior token-label bags.

For example:

```text
IF current token has NOUN
AND previous token has DET
THEN add NP_HEAD +0.4 to current token
```

This changes the balance between state and transition complexity. More lookback means transitions can be more expressive. Less lookback means the FSM state carries more of the burden.

A useful compromise is bounded lookback plus stacked abstraction. Early blocks use short windows over raw labels. Later blocks use short windows over abstract labels.

## Multiple FSMs Over the Same Input

A block may contain many FSMs operating over the same token-label sequence. These machines can independently add, reinforce, or compete with labels.

Example:

```text
Lexicon FSM:
  LEX:book -> NOUN +0.6, VERB +0.5

Determiner FSM:
  DET before token -> NOUN +0.3

Modal FSM:
  MODAL before token -> VERB +0.4
```

Given:

```text
the book
```

The determiner FSM reinforces `NOUN`.

Given:

```text
can book
```

The modal FSM reinforces `VERB`.

No single FSM needs to decide the final interpretation. Each contributes weighted evidence.

## Optional Tree Projection

The parser's native output is still just labels attached to tokens. However, tree-like information can be encoded using labels.

Examples:

```text
NP_START
NP_INSIDE
NP_END
VP_START
VP_END
SUBJECT_OF:token_5
OBJECT_OF:token_5
HEAD:token_2
CLAUSE_DEPTH:2
```

A separate projection step can read these labels and render a constituency tree, dependency graph, or semantic frame if needed.

The parser therefore does not need to commit to a tree internally. It can carry weighted structural hints and produce a tree only at the boundary where another system or user needs one.

## Difference From Pairwise Dependency Parsing

Some parsers build candidate pairings between words and assign weights to those pairings, often selecting a best dependency structure. This parser does not require pairwise word attachment as its primitive operation.

Instead, its primitive operation is:

```text
label pattern over token context -> new weighted labels
```

Pairwise relationships can still be represented, but as labels:

```text
SUBJECT_OF:token_5
MODIFIES:token_7
ATTACHES_TO_PREVIOUS_VERB
```

This makes dependency-like structure optional and representational rather than foundational.

## Native Output

The final output is a token sequence with weighted labels:

```text
Token 0: "The"
  DET              0.34
  NP_START         0.31
  DEFINITE         0.22
  FORGOTTEN        0.01

Token 1: "cat"
  NOUN             0.28
  NP_HEAD          0.27
  ANIMATE_ENTITY   0.19
  SUBJECT_CANDIDATE 0.14
  NP_END           0.09
  FORGOTTEN        0.03

Token 2: "slept"
  VERB             0.31
  INTRANSITIVE     0.24
  PAST_TENSE       0.20
  PREDICATE        0.18
  FORGOTTEN        0.02
```

A downstream consumer can choose whether to use the whole distribution, take top labels, render spans, or project a tree.

## Key Design Principles

1. Preserve one data shape: tokens with weighted labels.
2. Treat token identity as a label, not a privileged object.
3. Let many FSMs operate over the same sequence.
4. Stack FSM blocks so labels become increasingly abstract.
5. Use normalization and pruning to keep label buckets manageable.
6. Let obsolete labels decay unless refreshed.
7. Keep trees optional; represent structural information as labels.
8. Interpret weights as salience or carried evidence, not necessarily strict probabilities.

## Open Design Questions

Several important choices remain open:

- What exact scoring algebra should label updates use?
- Should weights be additive, multiplicative, log-space, or rank-based?
- How aggressively should old labels decay?
- Should some labels be sticky or replenished every layer?
- How large should lookback windows be?
- Can blocks run to convergence, or should each block execute once?
- How should contradictory labels suppress each other?
- How should final labels be evaluated against POS tags, parses, semantic roles, or task outputs?

## Minimal Pseudocode

```text
labels = initialize_token_labels(tokens)

for block in blocks:
    emitted = empty_label_deltas(tokens)

    for fsm in block.fsms:
        emitted += fsm.run(labels)

    labels = merge(labels, emitted)
    labels = decay(labels, block.decay_policy)
    labels = normalize(labels)
    labels = prune_to_budget(labels, forgotten_label="FORGOTTEN")

return labels
```

## Summary

This parser is a stacked weighted FSM system whose only required output is labels attached to tokens. It can model lexical, syntactic, semantic, and structural information without neural networks and without requiring a tree as its core representation.

Its strength is uniformity. Everything is a label. Every block consumes labels and emits labels. Parsing is the gradual transformation of low-level token evidence into higher-level linguistic and semantic evidence.

In short: the system does not parse by choosing a tree. It parses by refining what each token can mean, what each token can do, and what each token may be part of, until the useful structure has emerged from the labels themselves.
