from fsm_parser.grammar import build_default_parser


def test_the_cat_slept_basic_pos():
    parser = build_default_parser()
    state = parser.parse("The cat slept.")
    by_text = {t.text: t for t in state.tokens}
    assert by_text["The"].labels.get("POS:DET") > 0
    assert by_text["cat"].labels.get("POS:NOUN") > 0
    assert by_text["slept"].labels.get("POS:VERB") > 0


def test_phrase_labels_appear():
    parser = build_default_parser()
    state = parser.parse("The cat slept")
    cat = next(t for t in state.tokens if t.text == "cat")
    slept = next(t for t in state.tokens if t.text == "slept")
    assert cat.labels.get("PHRASE:NP_HEAD") > 0
    assert slept.labels.get("PHRASE:VP_HEAD") > 0


def test_subject_candidate_emerges_before_verb():
    parser = build_default_parser()
    state = parser.parse("The cat slept")
    cat = next(t for t in state.tokens if t.text == "cat")
    assert cat.labels.get("ROLE:SUBJECT_CANDIDATE") > 0
