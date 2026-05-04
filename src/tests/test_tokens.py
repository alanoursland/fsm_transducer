from fsm_parser.tokens import initialize_state, tokenize


def test_tokenize_words_and_punct():
    assert tokenize("The cat slept.") == ["The", "cat", "slept", "."]


def test_tokenize_handles_multiple_punct():
    assert tokenize("Wait, what?!") == ["Wait", ",", "what", "?", "!"]


def test_initialize_state_attaches_identity_labels():
    state = initialize_state("The cat")
    assert len(state.tokens) == 2
    the = state.tokens[0]
    assert the.text == "The"
    assert the.labels.get("TEXT:The") == 1.0
    assert the.labels.get("LOWER:the") == 1.0
    assert the.labels.get("TOKEN") == 1.0
    assert the.labels.get("SHAPE:Xxx") == 1.0


def test_initialize_state_marks_punct():
    state = initialize_state("Hi.")
    period = state.tokens[1]
    assert period.text == "."
    assert period.labels.get("PUNCT") == 1.0


def test_initialize_state_layer_is_zero():
    state = initialize_state("hi")
    assert state.layer == 0
