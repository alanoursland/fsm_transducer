from fsm_parser.labels import LabelBag, LabelDelta


def test_add_accumulates():
    bag = LabelBag()
    bag.add("NOUN", 0.3)
    bag.add("NOUN", 0.4)
    assert bag.get("NOUN") == 0.7


def test_get_default_for_missing():
    bag = LabelBag()
    assert bag.get("VERB") == 0.0
    assert bag.get("VERB", default=0.5) == 0.5


def test_has_threshold():
    bag = LabelBag()
    bag.add("X", 0.5)
    assert bag.has("X", 0.5)
    assert not bag.has("X", 0.6)


def test_top_k_orders_by_weight():
    bag = LabelBag()
    bag.add("A", 0.1)
    bag.add("B", 0.5)
    bag.add("C", 0.3)
    assert bag.top_k(2) == [("B", 0.5), ("C", 0.3)]


def test_total_sums_weights():
    bag = LabelBag()
    bag.add("A", 0.1)
    bag.add("B", 0.4)
    assert bag.total() == 0.5


def test_copy_independent():
    bag = LabelBag()
    bag.add("A", 0.1)
    other = bag.copy()
    other.add("A", 1.0)
    assert bag.get("A") == 0.1
    assert other.get("A") == 1.1


def test_label_delta_fields():
    d = LabelDelta(token_index=2, label="NOUN", weight=0.5, source="rule")
    assert d.token_index == 2
    assert d.label == "NOUN"
    assert d.weight == 0.5
    assert d.source == "rule"
