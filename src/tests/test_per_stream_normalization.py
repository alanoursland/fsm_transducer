from fsm_parser import (
    CharClassBlock,
    Parser,
    ParserConfig,
    SimpleCharToTokenReducer,
    initialize_char_state,
)
from fsm_parser.normalization import NormalizationConfig


def test_char_stream_can_decay_faster_than_token():
    config = ParserConfig(
        decay=1.0,
        min_weight=0.0,
        stream_configs={
            "char": NormalizationConfig(decay=0.5, min_weight=0.0),
            "token": NormalizationConfig(decay=1.0, min_weight=0.0),
        },
    )
    parser = Parser(
        layers=[[CharClassBlock()], [SimpleCharToTokenReducer()]],
        config=config,
    )
    state = initialize_char_state("foo")
    parser.parse_state(state)
    # Char labels were initialized at 1.0; decayed twice (after each layer),
    # 1.0 * 0.5 ** 2 = 0.25.
    assert abs(state.stream("char")[0].labels.get("CHAR") - 0.25) < 1e-9
    # Token slot was created at layer 2; it has only been normalized once with
    # decay=1.0 since creation.
    assert state.tokens[0].labels.get("TOKEN:IDENT") == 1.0


def test_default_config_used_when_no_stream_specific_config():
    config = ParserConfig(decay=0.9, min_weight=0.0)
    parser = Parser(
        layers=[[CharClassBlock()], [SimpleCharToTokenReducer()]],
        config=config,
    )
    state = initialize_char_state("foo")
    parser.parse_state(state)
    # Char labels decay at 0.9 each layer, twice: 0.81.
    assert abs(state.stream("char")[0].labels.get("CHAR") - 0.81) < 1e-9
