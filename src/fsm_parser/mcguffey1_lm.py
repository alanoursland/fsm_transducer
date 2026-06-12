"""Autoregressive next-token generation from the tier-1 PARSER machine.

The transformer-LM loop, run on the clause story FSM directly: the
output at each step is a prediction for the next token; sample from it;
feed the sampled token back in; repeat.

No new grammar is written. The clause story machine's belief state over
a prefix is its live path frontier (state x weight), and each frontier
path's outgoing transition conditions say which label-classes may come
next. A vocabulary word's probability is the weight the machine puts on
it:

    P(w | prefix)  ~  sum over (path, transition)
                        path.weight * transition.weight
                                    * support(condition, lexicon[w])

where ``support`` is the soft (fuzzy) reading of the same condition the
scanner evaluates as a boolean — HasLabel reads the word's lexical tag
weight, And takes min, Or takes max. The weights on the labels ARE the
language model; sampling just rolls the dice the parser was already
holding.

This is the forward-prediction half of the parser, the same machine the
direction/locality note runs backwards: a prefix narrows the frontier,
the frontier constrains the future. Sentences end when a sampled token
is PUNCT; the machine restarts for the next sentence, which is also why
the output is grammatical-but-incoherent across sentences — the clause
machine carries no story memory between restarts. (That gap is the
REF/centering machinery, by design upstream of this module: a story
machine would re-weight THIS distribution, exactly like ENCL — upstream
narrates, the reflex reads.)
"""

from __future__ import annotations

import argparse
import random
from functools import lru_cache

from fsm_parser.fsm import (
    And,
    Always,
    AtSentenceEnd,
    AtSentenceStart,
    FSMScanner,
    HasAllLabels,
    HasAnyLabel,
    HasLabel,
    Never,
    Not,
    Or,
    ScanContext,
    WeightAbove,
    WeightBelow,
)
from fsm_parser.mcguffey1_lang import _machine, initialize, lexicon, parse

PUNCT_WORDS = {".": {"PUNCT": 1.0},
               "?": {"PUNCT": 1.0, "QMARK": 1.0},
               ",": {"COMMA": 1.0}}


def support(cond, labels: dict[str, float]) -> float:
    """Soft evaluation of a transition condition against a word's
    lexical tag weights. Agrees with boolean ``matches`` on which words
    are possible; grades them by how strongly tagged they are."""
    if isinstance(cond, HasLabel):
        w = labels.get(cond.label, 0.0)
        return w if w > cond.min_weight else 0.0
    if isinstance(cond, HasAnyLabel):
        return max((labels.get(l, 0.0) for l in cond.labels
                    if labels.get(l, 0.0) > cond.min_weight), default=0.0)
    if isinstance(cond, HasAllLabels):
        ws = [labels.get(l, 0.0) for l in cond.labels]
        return min(ws) if all(w > cond.min_weight for w in ws) else 0.0
    if isinstance(cond, Not):
        return 1.0 if support(cond.inner, labels) == 0.0 else 0.0
    if isinstance(cond, And):
        ws = [support(p, labels) for p in cond.parts]
        return min(ws) if all(ws) else 0.0
    if isinstance(cond, Or):
        return max(support(p, labels) for p in cond.parts)
    if isinstance(cond, WeightAbove):
        w = labels.get(cond.label, 0.0)
        return w if w > cond.threshold else 0.0
    if isinstance(cond, WeightBelow):
        return 1.0 if labels.get(cond.label, 0.0) < cond.threshold else 0.0
    if isinstance(cond, (Always, AtSentenceStart, AtSentenceEnd)):
        return 1.0  # positional gating handled by the caller's context
    if isinstance(cond, Never):
        return 0.0
    return 1.0  # opaque predicates: don't grade, don't forbid


@lru_cache(maxsize=1)
def _vocab() -> dict[str, dict[str, float]]:
    """Candidate next tokens: every lexicon word (with VAL, as the
    tokenizer would label it) plus sentence punctuation."""
    out = {}
    for word, tags in lexicon().items():
        labels = {lab: float(w) for lab, w in tags.items()}
        labels[f"VAL:{word}"] = 1.0
        out[word] = labels
    out.update(PUNCT_WORDS)
    return out


def _frontier(tokens: list[str]):
    state = initialize(" ".join(tokens))
    frontier: list = []
    FSMScanner().transduce(_machine(), state, stream="token",
                           anchored=True, frontier_out=frontier)
    return frontier


def next_token_distribution(tokens: list[str]) -> dict[str, float]:
    """P(next token | prefix), straight off the machine. Empty when the
    prefix has killed every path (the parser would reject anyway)."""
    pos = len(tokens)
    dist: dict[str, float] = {}
    for path in _frontier(tokens):
        ctx = ScanContext(scan_start=path.scan_start, n=pos + 1, pos=pos,
                          last_consumed=path.last_consumed,
                          captures=path.captures)
        for tr in _machine().transitions_from(path.state):
            if tr.epsilon:
                continue
            # positional conditions (AtSentenceStart) use the real ctx;
            # label conditions are graded softly per candidate word
            for word, labels in _vocab().items():
                s = support(tr.condition, labels)
                if s <= 0.0:
                    continue
                if isinstance(tr.condition, (AtSentenceStart, AtSentenceEnd)) \
                        and not tr.condition.matches(None, ctx):
                    continue
                dist[word] = dist.get(word, 0.0) + path.weight * tr.weight * s
    return dist


def sample_token(dist: dict[str, float], rng: random.Random,
                 temperature: float = 1.0) -> str:
    words = list(dist)
    weights = [dist[w] ** (1.0 / temperature) for w in words]
    return rng.choices(words, weights=weights, k=1)[0]


def _sample_sentence(rng: random.Random, temperature: float,
                     max_tokens: int, prompt: list[str]) -> str | None:
    tokens = list(prompt)
    while len(tokens) < max_tokens:
        dist = next_token_distribution(tokens)
        if not dist:
            return None
        tok = sample_token(dist, rng, temperature)
        if tok in (".", "?"):
            return _render(tokens, tok) if tokens else None
        if not tokens and tok == ",":
            return None
        tokens.append(tok)
    return None  # runaway: reject


def generate_lm(n_sentences: int = 5, *, temperature: float = 1.0,
                seed: int | None = None, max_tokens: int = 10,
                prompt: list[str] | None = None,
                max_tries: int = 200) -> str:
    """The autoregressive loop: predict, sample, feed back; PUNCT ends a
    sentence and resets the frontier.

    The frontier machine is permissive (it accretes labels; the VM
    judges, and projection absorbs strays), so sampled sentences are
    rejection-checked against the ROUND-TRIP ORACLE: a sentence is kept
    only if it parses to frames that regenerate and parse back to the
    same frames. The LM proposes; the certified core of the language
    accepts. No scoring outside the machines."""
    from fsm_parser.mcguffey1_gen import generate as gen_from_frame

    rng = random.Random(seed)
    sentences: list[str] = []
    while len(sentences) < n_sentences:
        for _ in range(max_tries):
            cand = _sample_sentence(rng, temperature, max_tokens,
                                    prompt or [])
            frames = parse(cand) if cand is not None else None
            if not frames or not _covered(cand, frames):
                continue
            regen = [gen_from_frame(f) for f in frames]
            if all(regen) and parse(" ".join(regen)) == frames:
                sentences.append(cand)
                break
        else:
            raise RuntimeError("no round-trippable sentence in max_tries")
    return " ".join(sentences)


# function words the frames legitimately do not record
_UNFRAMED = {"the", "a", "an", "and", "not", "is", "are", "was", "were",
             "do", "does", "did", "there", "to", ",", ".", "?"}


def _frame_words(frames: list[dict]) -> set[str]:
    words: set[str] = set()

    def walk(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if k not in ("mood", "neg"):
                    walk(x)
                if k not in ("pred", "agent", "theme", "attr", "mod",
                             "neg", "mood", "wh"):
                    words.add(k)  # preposition keys are surface words
        elif isinstance(v, list):
            for x in v:
                walk(x)
        else:
            words.add(str(v).lower())
    walk(frames)
    return words


def _covered(text: str, frames: list[dict]) -> bool:
    """No token left behind: projection absorbs strays silently, so a
    candidate counts only if every sampled token made it into the
    meaning (or is closed-class the frames don't record)."""
    allowed = _frame_words(frames) | _UNFRAMED
    return all(t in allowed for t in text.lower().rstrip(".?").split())


def _render(tokens: list[str], punct: str) -> str:
    lex = lexicon()
    out = []
    for i, w in enumerate(tokens):
        if w == "i":
            out.append("I")
        elif i == 0 or "NAME" in lex.get(w, {}):
            out.append(w.capitalize())
        else:
            out.append(w)
    text = " ".join(out).replace(" ,", ",")
    return text + punct


def _prompt_tokens(prompt: str | None) -> list[str] | None:
    if not prompt:
        return None
    return [tok.lower() for tok in prompt.replace(",", " ,").split()]


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m fsm_parser.mcguffey1_lm",
        description="Generate text from the tier-1 McGuffey symbolic language model.",
    )
    p.add_argument(
        "n_sentences",
        nargs="?",
        type=int,
        default=5,
        help="number of sentences to generate (default: 5)",
    )
    p.add_argument("--seed", type=int, help="random seed for deterministic output")
    p.add_argument(
        "--temperature",
        "-t",
        type=float,
        default=1.0,
        help="sampling temperature (default: 1.0)",
    )
    p.add_argument(
        "--max-tokens",
        type=int,
        default=10,
        help="maximum tokens per sampled sentence before rejection (default: 10)",
    )
    p.add_argument(
        "--prompt",
        help="prefix tokens each generated sentence must continue, e.g. 'the cat'",
    )
    p.add_argument(
        "--max-tries",
        type=int,
        default=200,
        help="rejection-sampling attempts per sentence (default: 200)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)
    print(generate_lm(
        args.n_sentences,
        seed=args.seed,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        prompt=_prompt_tokens(args.prompt),
        max_tries=args.max_tries,
    ))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
