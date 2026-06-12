"""Generation + the round-trip oracle for tier-1 McGuffey English."""

from pathlib import Path

from fsm_parser.analysis import signature
from fsm_parser.mcguffey1_gen import build_token_emitter, generate
from fsm_parser.mcguffey1_lang import build_clause_story, compile_text, parse, run_program

CORPUS = Path(__file__).parent.parent.parent / "data" / "early_reader" / "sentences" / "mcguffey_primer.txt"


def test_generation_goldens():
    cases = [
        ({"pred": "has", "agent": "cat", "theme": "rat"}, "The cat has the rat."),
        ({"pred": "fan", "agent": "ann", "theme": "lad", "mod": "can",
          "mood": "q"}, "Can Ann fan the lad?"),
        ({"pred": "see", "agent": "you",
          "theme": {"pred": "run", "agent": "spot"}}, "See Spot run."),
        ({"pred": "intro", "agent": ["cat", "rat"]}, "The cat and the rat."),
        ({"pred": "run", "agent": "you"}, "Run."),
        ({"pred": "is", "agent": "ball", "attr": "red"}, "The ball is red."),
    ]
    for frame, text in cases:
        assert generate(frame) == text, frame


def test_round_trip_identity_on_goldens():
    frames = [
        {"pred": "ran", "agent": "rat", "at": "ann"},
        {"pred": "play", "agent": ["dick", "jane"]},
        {"pred": "rob", "agent": "you", "theme": "nest", "neg": True, "mod": "do"},
        {"pred": "is", "theme": "bird", "in": "nest"},
    ]
    for f in frames:
        text = generate(f)
        assert text is not None, f
        assert parse(text) == [f], (f, text)


def test_corpus_round_trip_floors():
    """The round-trip oracle over the real corpus. Ratchets, not targets:
    generable >= 88% of parsed frames; identity >= 88% of generable.
    Known failures are parser story-mixtures — the oracle's job is to
    keep finding them (see GENERATION.md)."""
    parsed = gen_ok = rt_ok = 0
    for s in CORPUS.read_text().strip().split("\n"):
        r = compile_text(s)
        if r.errors:
            continue
        res = run_program(r.program)
        if not (res.valid and res.frames):
            continue
        parsed += 1
        texts = [generate(f) for f in res.frames]
        if any(t is None for t in texts):
            continue
        gen_ok += 1
        if parse(" ".join(texts)) == res.frames:
            rt_ok += 1
    assert gen_ok / parsed >= 0.88, f"generable regressed: {gen_ok}/{parsed}"
    assert rt_ok / gen_ok >= 0.88, f"round-trip regressed: {rt_ok}/{gen_ok}"


def test_signatures_declare_closed_alphabets():
    """Machines have inspectable I/O alphabets; the parser's input
    alphabet is small and closed (the Unicode lesson, enforced)."""
    parse_sig = signature(build_clause_story())
    assert len(parse_sig.inputs) <= 25            # 21 today; closed, small
    assert "QMARK" in parse_sig.inputs
    gen_sig = signature(build_token_emitter())
    assert "EL:*" in gen_sig.inputs               # family-level reporting
    assert "TOKEN.0:*" in gen_sig.outputs         # tokens are just labels
    # composes_after reports input families an upstream doesn't provide
    assert "NAME" in gen_sig.composes_after({"EL:*"})


def test_article_distribution_is_in_the_field():
    """The field holds a weighted distribution over surface forms —
    a language model in the literal sense; argmax renders it."""
    from fsm_parser.fsm import FSMScanner
    from fsm_parser.mcguffey1_gen import element_stream
    from fsm_parser.normalization import apply_deltas

    state = element_stream([("ENT", "cat")])
    apply_deltas(state, FSMScanner().transduce(
        build_token_emitter(), state, stream="el", anchored=True))
    labs = state.stream("el")[0].labels
    assert round(labs.get("TOKEN.0:the"), 2) == 0.7
    assert round(labs.get("TOKEN.0:a"), 2) == 0.3
