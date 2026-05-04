from fsm_parser.fsm import (
    Emission,
    FSMBuilder,
    FSMScanner,
    HasLabel,
    StateInfo,
)
from fsm_parser.tokens import initialize_state


def _seed(state, label_map):
    for index, labels in label_map.items():
        for label, weight in labels.items():
            state.tokens[index].labels.add(label, weight)


def test_on_accept_emission_fires_at_acceptance():
    state = initialize_state("the cat")
    _seed(state, {0: {"POS:DET": 1.0}, 1: {"POS:NOUN": 1.0}})
    b = FSMBuilder("np")
    s0, s1, s2 = b.fresh(3)
    b.start(s0).accept(s2)
    b.transition(s0, HasLabel("POS:DET"), s1)
    b.transition(s1, HasLabel("POS:NOUN"), s2)
    b.state_info(s2, on_accept=(Emission("NP_HEAD", 1.0),))
    fsm = b.build()
    deltas = FSMScanner().scan(fsm, state)
    heads = [d for d in deltas if d.label == "NP_HEAD"]
    assert len(heads) == 1
    assert heads[0].token_index == 1


def test_on_enter_fires_when_path_reaches_state():
    state = initialize_state("a b")
    _seed(state, {0: {"POS:NOUN": 1.0}, 1: {"POS:NOUN": 1.0}})
    b = FSMBuilder("noun_pair")
    s0, s1, s2 = b.fresh(3)
    b.start(s0).accept(s2)
    b.transition(s0, HasLabel("POS:NOUN"), s1)
    b.transition(s1, HasLabel("POS:NOUN"), s2)
    b.state_info(s1, on_enter=(Emission("ENTERED_S1", 1.0),))
    fsm = b.build()
    deltas = FSMScanner().scan(fsm, state)
    assert any(d.label == "ENTERED_S1" for d in deltas)
