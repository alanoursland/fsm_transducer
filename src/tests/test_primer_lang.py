"""Acceptance tests for the primer language.

No external oracle exists for English (see PERSPECTIVE.md); these
goldens are hand-validated and are the acceptance suite.
"""

from fsm_parser.primer_lang import compile_text, parse, run_program


def _labels(r, slot_id):
    return {lab: round(w, 3) for lab, w in r.state.get_slot(slot_id).labels.items()}


# --- The two-stories experiment ------------------------------------------------------


def test_fork_pair_frames():
    assert parse("Play.") == [{"pred": "play", "agent": "you"}]
    assert parse("Play is fun.") == [{"pred": "is", "agent": "play", "attr": "fun"}]


def test_fork_superposition_is_in_the_field():
    """Both stories' eager labels are present on the fork token in BOTH
    sentences — the superposition is recorded, never retracted."""
    for src in ("Play.", "Play is fun."):
        labs = _labels(compile_text(src), "token:0")
        assert labs["STORY:IMP"] == 0.55
        assert labs["STORY:DECL"] == 0.45


def test_fork_only_the_survivor_confirms():
    """Confirmed EXEC ops come only from the story that reached the
    period; the dead story contributed eager labels and nothing else."""
    imp = _labels(compile_text("Play."), "token:0")
    assert imp["EXEC.0:IMPYOU"] == 0.55          # imperative survived
    assert not any(k == "EXEC.0:ENT(!{VAL})" for k in imp)
    decl = _labels(compile_text("Play is fun."), "token:0")
    assert decl["EXEC.0:ENT(!{VAL})"] == 0.45    # subject story survived
    assert not any(k.startswith("EXEC.0:IMPYOU") for k in decl)


# --- Golden frames -------------------------------------------------------------------


def test_see_spot_run_raising():
    assert parse("See Spot run.") == [
        {"pred": "see", "agent": "you",
         "theme": {"pred": "run", "agent": "spot"}}
    ]


def test_declaratives():
    assert parse("Spot runs.") == [{"pred": "runs", "agent": "spot"}]
    assert parse("Spot sees the ball.") == [
        {"pred": "sees", "agent": "spot", "theme": "ball"}
    ]
    assert parse("Sally sees Spot play.") == [
        {"pred": "sees", "agent": "sally",
         "theme": {"pred": "play", "agent": "spot"}}
    ]


def test_coordination():
    assert parse("Dick and Jane play.") == [
        {"pred": "play", "agent": ["dick", "jane"]}
    ]


def test_copula():
    assert parse("The ball is red.") == [
        {"pred": "is", "agent": "ball", "attr": "red"}
    ]


def test_vocative_imperative():
    # the vocative names the addressee: agent is Spot, not you
    assert parse("Run, Spot, run!") == [{"pred": "run", "agent": "spot"}]


def test_imperatives():
    assert parse("Run.") == [{"pred": "run", "agent": "you"}]
    assert parse("See the ball.") == [
        {"pred": "see", "agent": "you", "theme": "ball"}
    ]


def test_multi_sentence_primer_text():
    frames = parse("See Spot. See Spot run. Run, Spot, run!")
    assert frames == [
        {"pred": "see", "agent": "you", "theme": "spot"},
        {"pred": "see", "agent": "you", "theme": {"pred": "run", "agent": "spot"}},
        {"pred": "run", "agent": "spot"},
    ]


# --- Graceful degradation --------------------------------------------------------------


def test_unparseable_sentence_yields_no_frame_and_no_crash():
    r = compile_text("Ball the see.")
    res = run_program(r.program)
    assert res.valid and res.frames == []
    # the eager field still recorded the story that was tried
    assert "STORY:DECL" in _labels(r, "token:0")


def test_bad_sentence_does_not_strand_the_rest():
    frames = parse("Ball the see. Spot runs.")
    assert frames == [{"pred": "runs", "agent": "spot"}]


def test_unknown_word():
    r = compile_text("See the zebra.")
    assert "ERROR:UNKNOWN_WORD" in r.errors
    assert parse("See the zebra.") is None


def test_case_insensitive():
    assert parse("SEE SPOT RUN.") == parse("see spot run.")


# --- Field sanity -------------------------------------------------------------------------


def test_weighted_lexicon_on_tokens():
    labs = _labels(compile_text("Play."), "token:0")
    assert labs["V"] == 0.55 and labs["N"] == 0.45


def test_every_frame_has_pred_and_core_argument():
    texts = ["Play.", "See Spot run.", "Dick and Jane play.",
             "The ball is red.", "Run, Spot, run!"]
    for t in texts:
        for frame in parse(t):
            assert "pred" in frame
            assert "agent" in frame or "attr" in frame
