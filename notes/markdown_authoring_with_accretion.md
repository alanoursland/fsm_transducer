# Using the Accretion Architecture to Write Markdown Documents

## Purpose

This document explores how the stacked weighted transducer architecture can be used not only to parse language, but to help write structured Markdown documents.

Markdown is a good target because it sits between plain text and formal structure. It is readable as text, but it also carries document structure: headings, lists, emphasis, code blocks, links, block quotes, tables, and sections. A Markdown document is not just a string. It is a layered artifact containing prose, syntax, hierarchy, intent, and presentation cues.

That makes Markdown a natural fit for an accretion parser.

The architecture can treat a Markdown document as a weighted field of evolving labels over characters, tokens, lines, blocks, sections, and semantic slots. Those labels can then support editing, outlining, validation, transformation, summarization, and generation.

The key idea is:

```text
Markdown writing is not just text generation.
It is structure accretion over a document surface.
```

## Why Markdown Fits the Architecture

Markdown has several properties that make it useful for this parser.

First, it has visible syntax. Headings begin with `#`, list items begin with markers, code fences use backticks, and links have recognizable delimiters. These are easy for finite-state transducers to recognize.

Second, Markdown is line-oriented. Many document structures can be detected by scanning lines rather than needing a full syntactic tree.

Third, Markdown is forgiving. Invalid or partial Markdown still has meaning. A draft document may have half-finished headings, incomplete lists, missing links, or unclosed code fences. A decision parser may want to classify these as errors. An accretion parser can simply assign weaker or conflicting labels.

Fourth, Markdown combines syntax and semantics. A heading is not only a syntactic marker; it also announces a topic. A list is not only a layout form; it may represent steps, options, requirements, risks, or examples. A code block is not only fenced text; it may be an implementation sketch, a command, a grammar fragment, or a test case.

This architecture can represent all of those claims as labels with weights.

## Markdown as Layered Evidence

A Markdown document can be processed at multiple levels:

```text
characters
-> inline tokens
-> lines
-> blocks
-> sections
-> document roles
-> authoring intents
```

Each level can be represented as a stream of slots.

A character stream may identify punctuation, whitespace, delimiter characters, and code fence markers.

A line stream may identify headings, blank lines, list items, table rows, code fence boundaries, and quote markers.

A block stream may identify paragraphs, lists, code blocks, tables, and quotes.

A section stream may identify title sections, introductions, design sections, examples, risks, and conclusions.

A semantic stream may identify claims, definitions, open questions, TODOs, decisions, constraints, examples, and implementation steps.

The parser does not need to immediately choose a complete Markdown AST. It can accumulate evidence at all these levels.

## Slot Streams for Markdown

A useful Markdown authoring state might contain these streams:

```text
char
inline
line
block
section
semantic
```

Each stream contains weighted labeled slots.

### Character slots

Character slots represent the raw document surface.

Example labels:

```text
CHAR:# 
CHAR:BACKTICK
CHAR:DASH
CHAR:DIGIT
CHAR:WHITESPACE
CHAR:NEWLINE
CHAR:LBRACKET
CHAR:RBRACKET
CHAR:LPAREN
CHAR:RPAREN
```

### Inline slots

Inline slots represent words, punctuation, inline code spans, links, emphasis spans, and references.

Example labels:

```text
INLINE:WORD
INLINE:CODE
INLINE:LINK_TEXT
INLINE:LINK_TARGET
INLINE:EMPHASIS
INLINE:STRONG
INLINE:REFERENCE
```

### Line slots

Line slots represent one logical line of Markdown.

Example labels:

```text
LINE:BLANK
LINE:HEADING
LINE:LIST_ITEM
LINE:ORDERED_LIST_ITEM
LINE:QUOTE
LINE:CODE_FENCE
LINE:TABLE_ROW
LINE:PARAGRAPH_TEXT
```

### Block slots

Block slots represent larger units made from one or more lines.

Example labels:

```text
BLOCK:PARAGRAPH
BLOCK:LIST
BLOCK:ORDERED_LIST
BLOCK:CODE
BLOCK:QUOTE
BLOCK:TABLE
BLOCK:HEADING
```

### Section slots

Section slots represent heading-governed document regions.

Example labels:

```text
SECTION:TITLE
SECTION:INTRODUCTION
SECTION:BACKGROUND
SECTION:DESIGN
SECTION:IMPLEMENTATION
SECTION:EXAMPLE
SECTION:RISKS
SECTION:OPEN_QUESTIONS
SECTION:CONCLUSION
```

### Semantic slots

Semantic slots represent what the document is doing.

Example labels:

```text
SEM:CLAIM
SEM:DEFINITION
SEM:REQUIREMENT
SEM:CONSTRAINT
SEM:RATIONALE
SEM:EXAMPLE
SEM:WARNING
SEM:TODO
SEM:DECISION
SEM:QUESTION
SEM:SUMMARY
```

These slots may not correspond cleanly to Markdown syntax. A paragraph may contain both a definition and a warning. A list may contain requirements. A code block may contain an example, a grammar, or an implementation sketch.

The all-labels-in-one-bucket principle remains useful here: syntactic, rhetorical, and semantic evidence can coexist on the same slot.

## Parsing Markdown Without Premature Commitment

Markdown often has ambiguous or incomplete syntax.

For example:

```text
- item one
  continuation
```

The second line may be a continuation of the list item, a nested paragraph, or malformed indentation.

A decision parser may need to choose. An accretion parser can maintain labels:

```text
LINE:LIST_CONTINUATION = 0.62
LINE:PARAGRAPH_TEXT = 0.31
LINE:INDENTED_BLOCK = 0.18
```

Similarly:

```text
---
```

could be a thematic break, YAML front matter delimiter, or content depending on position.

Labels can express that:

```text
LINE:THEMATIC_BREAK = 0.50
LINE:FRONT_MATTER_DELIMITER = 0.74
```

Contextual transducers later reweight those labels.

At the top of a document:

```text
---
title: Example
---
```

the front-matter interpretation grows stronger.

In the middle of a section, the thematic-break interpretation grows stronger.

This is the same deferred-commitment principle used for tokenization and parsing.

## Writing as Accretion

When used for authoring, the architecture can reverse its usual orientation.

Instead of only reading a document and accumulating labels, it can help a writer grow a document by adding structure and content incrementally.

A Markdown writing system could maintain a live labeled state of the document and propose edits such as:

```text
ADD_HEADING
SPLIT_SECTION
EXPAND_PARAGRAPH
INSERT_EXAMPLE
ADD_WARNING
CONVERT_PARAGRAPH_TO_LIST
PROMOTE_LIST_TO_STEPS
ADD_OPEN_QUESTION
ADD_SUMMARY
```

Each proposed edit is backed by labels in the current document.

For example, if several nearby paragraphs have labels:

```text
SEM:IMPLEMENTATION_DETAIL
SEM:ORDERED_STEP
SEM:DEPENDENCY
```

the system might propose:

```text
Convert this paragraph group into an ordered implementation list.
```

If a section contains many claims but no examples, it might propose:

```text
Insert an example after this definition.
```

If a document has an introduction and implementation section but no risks section, it might propose:

```text
Add a Risks and Open Questions section.
```

The system is not merely generating text. It is reading the evolving document state and applying structural transformations.

## Markdown Transducers

Different transducer types are useful for Markdown authoring.

### Annotating transducers

These preserve document shape and add labels.

Examples:

```text
line starts with "# " -> LINE:HEADING, HEADING_LEVEL:1
line starts with "- " -> LINE:LIST_ITEM
paragraph contains "must" -> SEM:REQUIREMENT
paragraph contains "because" -> SEM:RATIONALE
code fence says "python" -> CODE:PYTHON
```

### Reducing transducers

These group lower-level slots into higher-level slots.

Examples:

```text
characters -> inline tokens
lines -> paragraph block
list item lines -> list block
heading + following content -> section
```

### Expanding transducers

These add implied or helper slots.

Examples:

```text
TODO paragraph -> task slot
heading "Open Questions" -> question-container slot
section lacking examples -> missing-example slot
ambiguous claim -> clarification-needed slot
```

### Restructuring transducers

These propose document edits.

Examples:

```text
paragraph sequence -> bullet list
flat heading structure -> nested section structure
long section -> split into subsections
list of vague items -> table with columns
```

These editing transducers may not be applied automatically. They can produce candidate edits with weights, and an author or downstream policy can choose.

## Example: From Draft to Structure

Suppose the draft contains:

```markdown
# Parser idea

It works by adding weighted labels to tokens. The labels decay over layers. We might need trees later but they are projections.

Need to think about tokenizer.
Need examples.
```

Initial line labels:

```text
0: LINE:HEADING, HEADING_LEVEL:1
1: LINE:BLANK
2: LINE:PARAGRAPH_TEXT
3: LINE:BLANK
4: LINE:PARAGRAPH_TEXT
5: LINE:PARAGRAPH_TEXT
```

Semantic labels:

```text
line 2:
  SEM:CLAIM = 0.72
  SEM:DESIGN_SUMMARY = 0.63
  SEM:DEFINITION = 0.41

line 4:
  SEM:TODO = 0.58
  SEM:OPEN_QUESTION = 0.39

line 5:
  SEM:TODO = 0.66
```

A reducing transducer groups line 4 and line 5 into a candidate task block:

```text
BLOCK:TASK_LIST_CANDIDATE = 0.71
```

A restructuring transducer proposes:

```markdown
## Open Questions

- How should tokenization work?
- What examples should be used?
```

The proposed edit is not magic. It follows from accumulated labels:

```text
SEM:TODO
SEM:OPEN_QUESTION
SECTION:MISSING_OPEN_QUESTIONS
```

## Example: Section Role Detection

Markdown headings give surface structure, but not always rhetorical role.

A heading like:

```markdown
## Why this matters
```

may receive labels:

```text
SECTION:RATIONALE = 0.82
SECTION:INTRODUCTION = 0.28
```

A heading like:

```markdown
## Implementation path
```

may receive:

```text
SECTION:IMPLEMENTATION = 0.86
SECTION:ROADMAP = 0.64
```

A heading like:

```markdown
## Risks
```

may receive:

```text
SECTION:RISKS = 0.94
```

These labels allow document-level checks:

```text
Does this design doc have a motivation section?
Does it have implementation steps?
Does it have risks?
Does it have open questions?
Are examples present near definitions?
```

The parser can answer these questions from labels without needing a single rigid document schema.

## Example: Markdown Validation

The architecture can support linting and validation.

Possible labels:

```text
ISSUE:HEADING_LEVEL_SKIP
ISSUE:UNMATCHED_CODE_FENCE
ISSUE:BROKEN_LINK
ISSUE:EMPTY_SECTION
ISSUE:LONG_PARAGRAPH
ISSUE:LIST_MARKER_INCONSISTENT
ISSUE:TABLE_ALIGNMENT_MISMATCH
ISSUE:MISSING_LANGUAGE_FOR_CODE_BLOCK
```

These are just labels. They can carry weights and provenance.

For example:

```text
ISSUE:UNMATCHED_CODE_FENCE = 0.91
```

may be attached to the opening code fence line.

A lower-confidence issue might be:

```text
ISSUE:POSSIBLE_BROKEN_REFERENCE = 0.42
```

because the reference could be defined later or in another file.

The same trace mechanism used for parsing can explain why a validation label appeared.

## Example: Document Outline Projection

A Markdown outline is a projection from accumulated labels.

The parser may maintain:

```text
LINE:HEADING
HEADING_LEVEL:2
SECTION:DESIGN
SECTION:IMPLEMENTATION
SECTION:RISKS
```

A projection step reads those labels into:

```text
- Title
  - Motivation
  - Design
  - Implementation
  - Risks
  - Open Questions
```

The outline is not the parser's native output. It is one useful view.

Another projection might produce:

```text
tasks
definitions
claims
examples
warnings
```

A third projection might produce a Markdown AST.

This is consistent with the broader architecture: the parser carries evidence; projections make task-specific commitments.

## Authoring Actions as Projections

In a writing assistant, projections can become actions.

Examples:

```text
Projection: outline
Action: show table of contents

Projection: task labels
Action: collect TODOs

Projection: weak sections
Action: suggest sections to expand

Projection: issue labels
Action: show lint warnings

Projection: claim/example balance
Action: suggest examples

Projection: heading roles
Action: reorganize document
```

The same labeled document state can support many different authoring tools.

## Markdown Generation

The architecture can also generate Markdown, but generation should be framed carefully.

A generator can consume semantic slots and project them into Markdown surface form.

For example:

```text
SECTION:DESIGN
SEM:DEFINITION
SEM:EXAMPLE
SEM:OPEN_QUESTION
```

may project into:

```markdown
## Design

[definition paragraph]

### Example

[example block]

## Open Questions

- [question]
```

This is not the same as a language model generating arbitrary text. It is structured realization from an explicit document state.

Generation can be done in stages:

```text
semantic plan
-> section slots
-> block slots
-> line slots
-> Markdown text
```

At each stage, labels remain inspectable.

## Markdown as a Testbed

Markdown is a useful testbed for the architecture because it combines:

```text
regular syntax
line-sensitive structure
nested blocks
informal prose
semantic document roles
partial drafts
ambiguous syntax
projection needs
```

It is simpler than a programming language but richer than arithmetic expressions.

It also exercises shape-changing transducers:

```text
characters -> lines
lines -> blocks
blocks -> sections
sections -> semantic document plan
semantic gaps -> inserted slots
```

And it exercises authoring actions:

```text
labels -> suggestions
labels -> rewrites
labels -> validation issues
labels -> summaries
```

## Possible Pipeline

A Markdown processing pipeline might look like this:

```text
Layer 0: character stream
  raw characters

Layer 1: character syntax
  hashes, dashes, brackets, backticks, newlines, whitespace

Layer 2: line construction
  create line slots from character spans

Layer 3: line classification
  heading, list item, code fence, quote, table row, paragraph

Layer 4: block construction
  group lines into paragraphs, lists, code blocks, tables, quotes

Layer 5: inline parsing
  emphasis, links, code spans, references

Layer 6: section construction
  group heading-governed regions

Layer 7: semantic role labeling
  claims, definitions, examples, requirements, TODOs, risks

Layer 8: document-level diagnostics
  missing sections, weak examples, broken structure, unresolved questions

Layer 9: projection
  outline, AST, lint report, rewrite suggestions, generated Markdown
```

This pipeline does not require every layer to make hard decisions. It can carry candidate blocks, candidate sections, and candidate semantic roles with weights.

## Useful Labels

A Markdown authoring grammar might start with labels like these.

### Surface labels

```text
CHAR:HASH
CHAR:BACKTICK
CHAR:DASH
CHAR:STAR
CHAR:BRACKET_OPEN
CHAR:BRACKET_CLOSE
CHAR:PAREN_OPEN
CHAR:PAREN_CLOSE
CHAR:PIPE
CHAR:NEWLINE
```

### Line labels

```text
LINE:BLANK
LINE:HEADING
LINE:LIST_ITEM
LINE:ORDERED_LIST_ITEM
LINE:QUOTE
LINE:CODE_FENCE_OPEN
LINE:CODE_FENCE_CLOSE
LINE:TABLE_ROW
LINE:PARAGRAPH
```

### Block labels

```text
BLOCK:PARAGRAPH
BLOCK:LIST
BLOCK:CODE
BLOCK:QUOTE
BLOCK:TABLE
BLOCK:HEADING
BLOCK:FRONT_MATTER
```

### Section labels

```text
SECTION:TITLE
SECTION:ABSTRACT
SECTION:MOTIVATION
SECTION:BACKGROUND
SECTION:DESIGN
SECTION:IMPLEMENTATION
SECTION:EVALUATION
SECTION:RISKS
SECTION:OPEN_QUESTIONS
SECTION:CONCLUSION
```

### Semantic labels

```text
SEM:CLAIM
SEM:DEFINITION
SEM:EXAMPLE
SEM:COUNTEREXAMPLE
SEM:RATIONALE
SEM:REQUIREMENT
SEM:CONSTRAINT
SEM:DECISION
SEM:TODO
SEM:QUESTION
SEM:WARNING
SEM:SUMMARY
```

### Diagnostic labels

```text
ISSUE:MISSING_EXAMPLE
ISSUE:UNCLEAR_SECTION_PURPOSE
ISSUE:HEADING_LEVEL_SKIP
ISSUE:UNMATCHED_FENCE
ISSUE:LONG_PARAGRAPH
ISSUE:INCONSISTENT_TERMINOLOGY
ISSUE:UNRESOLVED_TODO
```

### Edit proposal labels

```text
EDIT:SPLIT_SECTION
EDIT:ADD_EXAMPLE
EDIT:CONVERT_TO_LIST
EDIT:ADD_SUMMARY
EDIT:REORDER_SECTIONS
EDIT:DEFINE_TERM
EDIT:RESOLVE_TODO
```

## Editing Without Losing the Draft

A writing tool built on this architecture should preserve the original draft.

Instead of immediately rewriting text, it can create candidate slots and edit proposals.

For example:

```text
EDIT:CONVERT_TO_LIST = 0.73
```

attached to a paragraph group does not mean the paragraph must be changed. It means the system has evidence that a list projection may be useful.

An authoring UI could show:

```text
This paragraph contains several step-like claims. Convert to list?
```

The author decides.

This matches the parser's broader stance: evidence first, decision later.

## Relationship to Markdown ASTs

Existing Markdown parsers usually produce an AST. That is useful and should not be discarded.

In this architecture, a Markdown AST is a projection.

The parser may produce a label field rich enough to derive:

```text
document
heading
paragraph
list
list_item
code_block
link
emphasis
```

But it can also preserve information that ordinary ASTs do not represent well:

```text
uncertain block type
possible broken syntax
semantic role
authoring intent
missing examples
unresolved questions
latent section purpose
```

So the goal is not to replace Markdown ASTs. The goal is to produce a richer intermediate representation from which ASTs, outlines, diagnostics, and edits can all be projected.

## Open Questions

### How much Markdown syntax should be formally recognized?

A small subset may be enough for authoring support. Full CommonMark compatibility is a larger project.

### Should line slots or block slots be primary?

Markdown is line-oriented, but many useful operations are block-oriented. A multi-stream state avoids forcing one choice.

### How should edits be represented?

An edit proposal could be a label, a structured delta, or a full patch. Labels are simple but may be too weak for complex rewrites.

### How should generated Markdown preserve style?

A document has local style: heading conventions, bullet markers, code fence styles, table formatting, and prose tone. Style labels may be needed.

### How should semantic labels be learned?

Some labels can be rule-based, such as TODO detection. Others, such as unclear rationale or weak examples, may require learned transducers or human-authored heuristics.

### How should confidence be shown to authors?

A writing assistant should not overwhelm the author with every weak label. Projection and UI policy matter.

## Recommended First Experiment

Build a small Markdown analyzer that works over line slots.

Initial features:

```text
heading detection
list item detection
code fence detection
paragraph grouping
section grouping
TODO detection
open question detection
long paragraph warning
missing example warning
outline projection
```

This avoids the hardest inline Markdown cases while exercising the architecture.

A good first input:

```markdown
# Project Title

This parser accumulates labels over tokens.

## Design

The parser has layers. Each layer adds labels.

Need example.

## Open Questions

How should tokenization work?
```

Expected projections:

```text
outline
TODO list
section roles
diagnostics
```

This would demonstrate that Markdown writing can be treated as accretion over a document, not just parsing to an AST.

## Summary

Markdown is a strong application for the architecture because it is simultaneously text, syntax, structure, and intent.

The parser can process Markdown as layered evidence:

```text
characters -> lines -> blocks -> sections -> semantic roles -> edit proposals
```

It can support:

```text
parsing
linting
outlining
summarization
rewriting
generation
authoring suggestions
```

without requiring every stage to collapse the document into one final structure.

The central principle remains the same:

```text
Do not decide too early.
Accrete evidence.
Project only when a consumer needs a view.
```

For Markdown authoring, that means the document is not merely a string to be generated. It is a living labeled field, and writing is the process of shaping that field into a clearer form.
