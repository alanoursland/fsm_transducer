from fsm_parser.labels import LabelBag, LabelDelta
from fsm_parser.normalization import (
    NormalizationConfig,
    apply_deltas,
    normalize,
)
from fsm_parser.tokens import initialize_state


def test_decay_scales_existing_weights():
    bag = LabelBag()
    bag.add("A", 1.0)
    out = normalize(bag, NormalizationConfig(decay=0.5))
    assert out.get("A") == 0.5


def test_threshold_pruning_moves_into_forgotten():
    bag = LabelBag()
    bag.add("STRONG", 0.5)
    bag.add("WEAK", 0.001)
    out = normalize(bag, NormalizationConfig(min_weight=0.01))
    assert out.get("STRONG") == 0.5
    assert "WEAK" not in out
    assert out.get("FORGOTTEN") == 0.001


def test_top_k_drops_excess_into_forgotten():
    bag = LabelBag()
    bag.add("A", 0.5)
    bag.add("B", 0.4)
    bag.add("C", 0.1)
    out = normalize(bag, NormalizationConfig(max_labels=2))
    assert out.get("A") == 0.5
    assert out.get("B") == 0.4
    assert "C" not in out
    assert abs(out.get("FORGOTTEN") - 0.1) < 1e-9


def test_total_mass_rescale_preserves_proportions():
    bag = LabelBag()
    bag.add("A", 2.0)
    bag.add("B", 1.0)
    out = normalize(bag, NormalizationConfig(total_mass=1.0))
    assert abs(sum(out.weights.values()) - 1.0) < 1e-9
    assert abs(out.get("A") / out.get("B") - 2.0) < 1e-9


def test_preexisting_forgotten_decays_too():
    bag = LabelBag()
    bag.add("FORGOTTEN", 0.4)
    bag.add("X", 1.0)
    out = normalize(bag, NormalizationConfig(decay=0.5))
    assert out.get("FORGOTTEN") == 0.2
    assert out.get("X") == 0.5


def test_apply_deltas_adds_to_target_token():
    state = initialize_state("a b c")
    deltas = [
        LabelDelta(token_index=1, label="POS:NOUN", weight=0.5, source="t"),
        LabelDelta(token_index=1, label="POS:NOUN", weight=0.2, source="t"),
    ]
    apply_deltas(state, deltas)
    assert abs(state.tokens[1].labels.get("POS:NOUN") - 0.7) < 1e-9


def test_apply_deltas_ignores_out_of_bounds():
    state = initialize_state("a")
    deltas = [LabelDelta(token_index=99, label="X", weight=1.0)]
    apply_deltas(state, deltas)  # should not raise
    assert state.tokens[0].labels.get("X") == 0.0
