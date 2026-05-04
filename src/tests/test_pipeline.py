from fsm_parser.blocks import FSMBlock, LexicalBlock
from fsm_parser.fsm import Emission, HasLabel, compile_linear
from fsm_parser.pipeline import Parser, ParserConfig


def _np_block():
    fsm = compile_linear(
        "det_noun_np",
        [HasLabel("POS:DET", 0.3), HasLabel("POS:NOUN", 0.3)],
        [Emission(label="PHRASE:NP_HEAD", weight=0.8)],
    )
    return FSMBlock(name="np", fsms=[fsm])


def test_layered_pipeline_runs_blocks_in_order():
    lex = LexicalBlock(
        name="lex",
        entries={"the": {"POS:DET": 1.0}, "cat": {"POS:NOUN": 1.0}},
    )
    parser = Parser(layers=[[lex], [_np_block()]])
    state = parser.parse("the cat")
    assert state.tokens[1].labels.get("PHRASE:NP_HEAD") > 0
    assert state.layer == 2


def test_normalization_runs_per_layer():
    lex = LexicalBlock(name="lex", entries={"x": {"WEAK": 0.0001}})
    parser = Parser(
        layers=[[lex]],
        config=ParserConfig(min_weight=0.01),
    )
    state = parser.parse("x")
    assert state.tokens[0].labels.get("WEAK") == 0.0
    assert state.tokens[0].labels.get("FORGOTTEN") > 0


def test_decay_reduces_old_labels_after_layers():
    lex = LexicalBlock(name="lex", entries={"x": {"OLD": 1.0}})
    no_op = LexicalBlock(name="noop", entries={})
    parser = Parser(
        layers=[[lex], [no_op], [no_op]],
        config=ParserConfig(decay=0.5),
    )
    state = parser.parse("x")
    # decayed three times after add: 1.0 * 0.5 ^ 3 = 0.125
    assert abs(state.tokens[0].labels.get("OLD") - 0.125) < 1e-9


def test_parse_with_trace_returns_layer_snapshots():
    lex = LexicalBlock(
        name="lex",
        entries={"the": {"POS:DET": 1.0}, "cat": {"POS:NOUN": 1.0}},
    )
    parser = Parser(layers=[[lex], [_np_block()]])
    final, traces = parser.parse_with_trace("the cat")
    assert len(traces) == 3  # init + 2 layers
    assert traces[0].layer == 0
    assert traces[-1].state.tokens[1].labels.get("PHRASE:NP_HEAD") > 0
    assert final.layer == 2


def test_book_disambiguation_after_aux():
    from fsm_parser.grammar import build_default_parser

    parser = build_default_parser()
    state = parser.parse("I can book flights")
    book = next(t for t in state.tokens if t.text == "book")
    assert book.labels.get("POS:VERB") > book.labels.get("POS:NOUN")


def test_book_disambiguation_after_det():
    from fsm_parser.grammar import build_default_parser

    parser = build_default_parser()
    state = parser.parse("the book fell")
    book = next(t for t in state.tokens if t.text == "book")
    assert book.labels.get("POS:NOUN") > book.labels.get("POS:VERB")
