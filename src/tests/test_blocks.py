from fsm_parser.blocks import FSMBlock, LexicalBlock
from fsm_parser.fsm import Emission, HasLabel, compile_linear
from fsm_parser.tokens import initialize_state


def test_lexical_block_emits_per_entry():
    block = LexicalBlock(
        name="lex",
        entries={"book": {"POS:NOUN": 0.6, "POS:VERB": 0.4}},
    )
    state = initialize_state("the book")
    deltas = block.apply(state)
    by_token = {(d.token_index, d.label): d.weight for d in deltas}
    assert by_token[(1, "POS:NOUN")] == 0.6
    assert by_token[(1, "POS:VERB")] == 0.4
    assert all(d.source == "lex" for d in deltas)


def test_lexical_block_lowercases_lookup():
    block = LexicalBlock(name="lex", entries={"the": {"POS:DET": 1.0}})
    state = initialize_state("THE")
    deltas = block.apply(state)
    assert any(d.label == "POS:DET" and d.weight == 1.0 for d in deltas)


def test_fsm_block_runs_all_fsms():
    state = initialize_state("the cat")
    state.tokens[0].labels.add("POS:DET", 1.0)
    state.tokens[1].labels.add("POS:NOUN", 1.0)
    fsm_a = compile_linear(
        "np_head",
        [HasLabel("POS:DET"), HasLabel("POS:NOUN")],
        [Emission(label="PHRASE:NP_HEAD", weight=0.8)],
    )
    fsm_b = compile_linear(
        "np_start",
        [HasLabel("POS:DET"), HasLabel("POS:NOUN")],
        [Emission(label="PHRASE:NP_START", weight=0.7, offset=-1)],
    )
    block = FSMBlock(name="phrases", fsms=[fsm_a, fsm_b])
    deltas = block.apply(state)
    labels = {d.label for d in deltas}
    assert "PHRASE:NP_HEAD" in labels
    assert "PHRASE:NP_START" in labels


def test_fsm_block_does_not_mutate_state():
    state = initialize_state("the cat")
    state.tokens[0].labels.add("POS:DET", 1.0)
    state.tokens[1].labels.add("POS:NOUN", 1.0)
    fsm = compile_linear(
        "np",
        [HasLabel("POS:DET"), HasLabel("POS:NOUN")],
        [Emission(label="X", weight=1.0)],
    )
    block = FSMBlock(name="b", fsms=[fsm])
    block.apply(state)
    assert state.tokens[1].labels.get("X") == 0.0
