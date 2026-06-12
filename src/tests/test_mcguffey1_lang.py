"""Tier-1 McGuffey language: goldens, the growth invariant, coverage floor."""

from pathlib import Path

from fsm_parser.mcguffey1_lang import compile_text, parse, run_program

CORPUS = Path(__file__).parent.parent.parent / "data" / "early_reader" / "sentences" / "mcguffey_primer.txt"


# --- Goldens (new tier-1 constructions) -------------------------------------------


def test_fragments_and_groups():
    assert parse("A cat and a rat.") == [{"pred": "intro", "agent": ["cat", "rat"]}]


def test_pp_and_compounds():
    assert parse("The rat ran at Ann.") == [{"pred": "ran", "agent": "rat", "at": "ann"}]
    assert parse("Sue loves her pet bird.") == [
        {"pred": "loves", "agent": "sue", "theme": "bird"}]


def test_modals_and_negation():
    assert parse("Ann can fan Nat.") == [
        {"pred": "fan", "agent": "ann", "theme": "nat", "mod": "can"}]
    f = parse("Do not rob the nest.")[0]
    assert f["pred"] == "rob" and f["agent"] == "you" and f.get("neg") is True


def test_questions_via_inversion():
    assert parse("Can Ann fan the lad?") == [
        {"pred": "fan", "agent": "ann", "theme": "lad", "mod": "can", "mood": "q"}]
    assert parse("Has Ann a hat?") == [
        {"pred": "has", "agent": "ann", "theme": "hat", "mood": "q"}]
    assert parse("Is the cat on the mat?") == [
        {"pred": "is", "theme": "cat", "on": "mat", "mood": "q"}]
    f = parse("What do you see?")[0]
    assert f["wh"] == "what" and f["mood"] == "q"


def test_copulas():
    assert parse("The old man is kind.") == [
        {"pred": "is", "agent": "man", "attr": "kind"}]
    assert parse("There is a bird in the nest.") == [
        {"pred": "is", "theme": "bird", "in": "nest"}]


def test_clause_and_object_coordination():
    assert parse("Ann sat, and Nat ran.") == [
        {"pred": "sat", "agent": "ann"}, {"pred": "ran", "agent": "nat"}]
    assert parse("The man sat; the lad ran.") == [
        {"pred": "sat", "agent": "man"}, {"pred": "ran", "agent": "lad"}]
    assert parse("Ann has a hat and a fan.") == [
        {"pred": "has", "agent": "ann", "theme": ["hat", "fan"]}]


# --- The growth invariant: nothing the seed parses is lost --------------------------


def test_growth_never_loses_ground():
    """Every primer (seed) golden must still parse in the grown language,
    with the same core roles — Steele's rule, mechanized."""
    seed_goldens = {
        "See Spot run.": {"pred": "see", "agent": "you",
                          "theme": {"pred": "run", "agent": "spot"}},
        "Spot sees the ball.": {"pred": "sees", "agent": "spot", "theme": "ball"},
        "Dick and Jane play.": {"pred": "play", "agent": ["dick", "jane"]},
        "The ball is red.": {"pred": "is", "agent": "ball", "attr": "red"},
        "Run, Spot, run!": {"pred": "run", "agent": "spot"},
        "Play.": {"pred": "play", "agent": "you"},
        "Play is fun.": {"pred": "is", "agent": "play", "attr": "fun"},
    }
    for sentence, expected in seed_goldens.items():
        frames = parse(sentence)
        assert frames is not None and len(frames) == 1, sentence
        for k, v in expected.items():
            assert frames[0].get(k) == v, (sentence, k, frames[0])


# --- Coverage floor (the growth-curve experiment's ratchet) --------------------------


def test_corpus_coverage_floor():
    """65%+ of the real McGuffey Primer parses. This number may only go
    UP in future growth iterations (ratchet, not target)."""
    sentences = CORPUS.read_text().strip().split("\n")
    ok = 0
    for s in sentences:
        r = compile_text(s)
        if r.errors:
            continue
        res = run_program(r.program)
        if res.valid and res.frames:
            ok += 1
    assert ok / len(sentences) >= 0.65, f"coverage regressed: {ok}/{len(sentences)}"


def test_graceful_on_everything():
    """No sentence in the corpus raises; failures degrade to no-frame."""
    for s in CORPUS.read_text().strip().split("\n"):
        r = compile_text(s)
        run_program(r.program)  # must not raise
