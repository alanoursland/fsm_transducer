# Tokenization as Parsing

## Purpose

The parser design originally treated tokens as the starting point. A parser state was a sequence of tokens, and every token carried a weighted label bag. Parser blocks read that sequence and emitted more labels.

That was useful for getting the first version working, but it hides a hard problem: **tokens are not natural primitives**.

In natural language, token boundaries are messy. In programming languages, tokenization is often described as regular-language recognition, but real languages repeatedly violate the clean separation between lexing and parsing. In large language models, tokens are statistical artifacts that often do not correspond to words, morphemes, syntax, or meaning.

So tokenization should not be treated as an external preprocessing step. In this architecture, tokenization should be understood as the first parsing problem.

The tokenizer is a transducer that turns low-level input evidence into weighted token hypotheses.

## The Problem With Assuming Tokens

A token looks simple only after someone has already made decisions.

For example:

```text
don't
```

could be treated as:

```text
["don't"]
```

or:

```text
["do", "n't"]
```

or semantically as:

```text
do + not
```

In programming languages, the problem can be sharper:

```text
a >> b
```

may contain a right-shift operator, while:

```text
vector<vector<int>> x
```

may require interpreting `>>` as two closing angle brackets in a template context.

A lexer that emits a single fixed token stream has already committed to one interpretation. That may be fine for many languages and tools, but it conflicts with the accretion stance of this parser.

The parser should be allowed to say:

```text
this span might be SHIFT_RIGHT
this span might be GT followed by GT
later context should decide
```

The same applies to natural language:

```text
New York
```

may be two word tokens syntactically but one named-entity unit semantically.

```text
kick the bucket
```

may be a verb phrase syntactically but one idiomatic semantic event.

Tokenization is not merely splitting. It is representational choice.

## Tokenization as Accretion

A conventional pipeline says:

```text
characters -> tokens -> parser
```

The accretion architecture should say:

```text
characters
-> character labels
-> boundary hypotheses
-> lexeme hypotheses
-> token hypotheses
-> syntax and semantics
```

A token is not an input object. A token is a hypothesis over a span.

For example, the input:

```text
book
```

may start as character slots:

```text
b
o
o
k
```

Early transducers add labels:

```text
b: CHAR:LETTER, WORD_START
o: CHAR:LETTER, WORD_CONT
o: CHAR:LETTER, WORD_CONT
k: CHAR:LETTER, WORD_END
```

Then a reducing transducer proposes a token slot:

```text
Slot {
  kind: TOKEN
  labels: {
    TOKEN:WORD = 0.95
    TEXT:book = 1.00
    LOWER:book = 1.00
  }
  source_span: chars 0..3
  parents: [char_0, char_1, char_2, char_3]
}
```

Later layers may add:

```text
POS:NOUN = 0.55
POS:VERB = 0.45
```

The token did not exist at the beginning. It accreted from evidence.

## Characters, Bytes, and Graphemes

The lowest-level input unit should be explicit.

Possible base units include:

```text
bytes
Unicode scalar values
grapheme clusters
characters
pre-tokenized words
```

For programming-language experiments, characters may be enough at first. For robust natural-language processing, Unicode grapheme clusters are a better conceptual primitive, because what users perceive as one character may consist of multiple Unicode code points.

For the first implementation, the practical choice is:

```text
base slots = characters
```

Each character slot receives basic labels:

```text
CHAR:LETTER
CHAR:DIGIT
CHAR:WHITESPACE
CHAR:PUNCT
CHAR:QUOTE
CHAR:OPERATOR
CHAR:OPEN_DELIM
CHAR:CLOSE_DELIM
```

Those labels are not final categories. They are the first layer of evidence.

## Boundary Hypotheses

Tokenization can be decomposed into two related questions:

```text
Where are the boundaries?
What kind of token does each span form?
```

Boundary labels can be attached to character slots:

```text
TOKEN_START
TOKEN_CONTINUE
TOKEN_END
BOUNDARY_BEFORE
BOUNDARY_AFTER
```

For example:

```text
foo + 123
```

might accumulate:

```text
f: TOKEN_START, IDENT_START
o: TOKEN_CONTINUE, IDENT_CONT
o: TOKEN_END, IDENT_END
+: TOKEN_START, TOKEN_END, OPERATOR
1: TOKEN_START, NUMBER_START
2: TOKEN_CONTINUE, NUMBER_CONT
3: TOKEN_END, NUMBER_END
```

A token projection step can read these boundary labels and produce candidate token slots.

This keeps boundary detection inspectable.

## Lexeme Hypotheses

A lexeme is a span-level claim.

Examples:

```text
IDENT
NUMBER
STRING
COMMENT
OPERATOR
KEYWORD
PUNCTUATION
WHITESPACE
```

A lexeme transducer may scan character labels and propose new token slots.

For a number:

```text
DIGIT+ ("." DIGIT+)?
```

it may create:

```text
TOKEN:NUMBER
TEXT:12.34
```

For an identifier:

```text
IDENT_START IDENT_CONT*
```

it may create:

```text
TOKEN:IDENT
TEXT:my_variable
```

For a quoted string, it may create:

```text
TOKEN:STRING
STRING:VALID
STRING:HAS_ESCAPES
```

String tokenization is a useful early test because it requires state: inside string, outside string, escape sequence, string end.

## Token Identity as Labels

A token slot should not have one fixed type.

It should carry a weighted label bag:

```text
TOKEN:IDENT = 0.91
TOKEN:KEYWORD = 0.34
TEXT:if = 1.00
LOWER:if = 1.00
```

This allows later context to reweight ambiguous cases.

For example, `if` in a programming language is usually a keyword, but in some languages keywords may be contextual. A tokenizer should not need to know all future syntax rules in advance. It can emit both:

```text
TOKEN:KEYWORD:IF
TOKEN:IDENT
```

with different weights.

The parser can resolve or preserve the ambiguity later.

## Whitespace and Comments

Whitespace and comments are often discarded by lexers, but discarding them too early loses information.

Whitespace can matter for:

```text
Python indentation
Markdown line structure
operator separation
sentence segmentation
format-sensitive languages
```

Comments can matter for:

```text
documentation extraction
pragmatic intent
code understanding
linting
region annotations
```

In this architecture, whitespace and comments should initially become slots or labels like everything else.

A later projection can hide them if the consumer does not need them.

For example:

```text
TOKEN:WHITESPACE
LAYOUT:NEWLINE
LAYOUT:INDENT_DELTA:+1
COMMENT:LINE
COMMENT:DOC
```

The parser should be able to forget them gradually, not erase them immediately.

## Tokenization and Programming Languages

Programming languages are a good testbed because they usually have formal grammars and expected parse trees. But they also expose the lie that tokenization is always simple.

Examples:

### C++

```text
vector<vector<int>> x
```

The character sequence `>>` may need to be interpreted as two `>` tokens in template context.

### JavaScript

```text
x / y
```

versus:

```text
if (/abc/.test(x)) ...
```

The slash character may begin division or a regular expression literal depending on syntactic context.

### Python

Python indentation produces `INDENT` and `DEDENT` tokens that depend on line structure and indentation stack state.

### Shell languages

Quoting, interpolation, escaping, and word splitting depend on context.

These cases show that tokenization is not merely a regular-language preprocessing step. It is a context-sensitive part of interpretation.

## Ambiguous Tokenization

The parser should allow overlapping token candidates.

For example:

```text
>>
```

may produce:

```text
slot_a:
  span: chars 0..1
  labels:
    TOKEN:SHIFT_RIGHT = 0.60

slot_b:
  span: chars 0..0
  labels:
    TOKEN:GT = 0.55

slot_c:
  span: chars 1..1
  labels:
    TOKEN:GT = 0.55
```

All candidates can coexist.

Later syntax transducers may boost one interpretation:

```text
inside template argument list:
  TOKEN:GT +0.40
  TOKEN:SHIFT_RIGHT - or no refresh
```

Projection can choose a final token stream if needed.

This is consistent with the parser's core philosophy: defer commitment until the consumer or later context supplies a reason to choose.

## Token Streams as Projections

A token stream should be treated as a projection from a richer field.

The tokenizer may produce:

```text
character slots
boundary labels
token candidates
whitespace slots
comment slots
alternative segmentations
```

A downstream parser or compiler may want one clean stream:

```text
IDENT("vector")
LT
IDENT("vector")
LT
IDENT("int")
GT
GT
IDENT("x")
SEMICOLON
```

That stream is a projected view.

The parser state may still preserve alternative candidates and provenance.

This distinction is important:

```text
token candidates are evidence
a token stream is a decision
```

## Tokenization and Shape-Changing Transducers

Tokenization is the first major example of a reducing transducer.

```text
characters -> token slots
```

It may also be a resegmenting transducer:

```text
one surface token -> multiple syntax tokens
multiple surface tokens -> one semantic unit
```

Examples:

```text
don't -> do + not
New York -> LOCATION_NAME
>> -> > + >
```

So tokenization belongs inside the broader system of shape-changing transducers.

It is not a special external phase.

## A Practical Pipeline

A first scannerless tokenizer pipeline might look like this:

```text
Layer 0: input characters
  create one slot per character

Layer 1: character classification
  add LETTER, DIGIT, WHITESPACE, QUOTE, OPERATOR, etc.

Layer 2: local character context
  add IDENT_START, IDENT_CONT, NUMBER_START, STRING_START, etc.

Layer 3: lexeme recognition
  create token candidate slots from character spans

Layer 4: token context
  distinguish keywords, identifiers, operators, delimiters

Layer 5: syntax
  operate primarily over token slots

Layer 6: projection
  produce a token stream, AST, label table, or other task-specific output
```

This pipeline keeps tokenization inspectable and revisable.

## First Test Languages

Good experimental targets:

### Arithmetic Expressions

Useful for testing numbers, identifiers, operators, grouping, precedence, and associativity.

Example:

```text
1 + 2 * 3
```

This is easy enough to debug but meaningful enough to test projection into an AST.

### JSON

Useful for testing strings, numbers, arrays, objects, punctuation, nesting, and validity.

JSON has relatively clean tokenization, but strings and escapes make it nontrivial.

### S-expressions

Useful for testing simple recursive structure with minimal tokenization complexity.

Example:

```text
(define x (+ 1 2))
```

### C++-like Mini Language

Useful for specifically testing ambiguous tokenization.

Example:

```text
a >> b
vector<vector<int>> x
```

This should come after simpler languages.

## Implementation Notes

The current implementation can evolve toward tokenization-as-parsing without a full rewrite.

### Step 1: character initialization

Add an alternate initializer:

```text
initialize_char_state(text)
```

This creates one slot per character instead of one token per word/punctuation span.

### Step 2: character label blocks

Add blocks for:

```text
is_letter
is_digit
is_whitespace
is_quote
is_operator_char
is_open_delimiter
is_close_delimiter
```

### Step 3: lexeme reducers

Add non-destructive token candidate creation.

A reducer should emit a new slot rather than deleting characters.

### Step 4: token projection

Write a projection function that selects a token sequence from weighted token candidates.

At first, this can be simple:

```text
choose non-overlapping candidates by highest weight
```

Later, it can become a dynamic programming problem.

### Step 5: syntax over token stream

Once token candidates exist, run the existing syntax transducers over the projected or candidate token stream.

The first version can project early. Later versions can preserve ambiguity longer.

## Open Questions

### What is the base unit?

Characters are simple, but Unicode grapheme clusters are more correct for natural language.

### When should token candidates become a stream?

Should syntax operate over all overlapping candidates, or should a token stream be projected before syntax?

### How should overlapping candidates be scored?

A token candidate has its own label weights, but a whole tokenization also has a sequence-level score.

### How much context should tokenization use?

A tokenizer that uses too much syntax becomes a parser. In this architecture that may be acceptable, but the boundary should be clear.

### What should happen to whitespace and comments?

They can be preserved as slots, hidden from some streams, or allowed to decay.

### Are token labels probabilities?

As with the rest of the architecture, weights should initially be treated as salience or evidence, not calibrated probabilities.

## Design Principle

Do not assume tokens.

Accrete them.

A token is a weighted span hypothesis over lower-level evidence. It may be ambiguous, context-sensitive, split, merged, hidden, or projected depending on what later stages need.

Tokenization is not the parser's input.

Tokenization is the parser's first act of interpretation.
