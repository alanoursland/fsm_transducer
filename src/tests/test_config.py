from pathlib import Path

import pytest

from fsm_parser.blocks import FSMBlock, LexicalBlock
from fsm_parser.config import ConfigError, load_grammar, parse_grammar
from fsm_parser.pipeline import Parser


def test_parse_grammar_builds_layers():
    raw = {
        "layers": [
            {
                "blocks": [
                    {
                        "name": "lex",
                        "type": "lexical",
                        "entries": {"the": {"POS:DET": 1.0}},
                    }
                ]
            },
            {
                "blocks": [
                    {
                        "name": "np",
                        "type": "fsm",
                        "fsms": [
                            {
                                "name": "det_noun",
                                "pattern": [
                                    {"has": "POS:DET", "min_weight": 0.3},
                                    {"has": "POS:NOUN", "min_weight": 0.3},
                                ],
                                "emit": [
                                    {
                                        "label": "PHRASE:NP_HEAD",
                                        "weight": 0.8,
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        ]
    }
    grammar = parse_grammar(raw)
    assert len(grammar.layers) == 2
    assert isinstance(grammar.layers[0][0], LexicalBlock)
    assert isinstance(grammar.layers[1][0], FSMBlock)


def test_unknown_block_type_errors():
    raw = {"layers": [{"blocks": [{"name": "x", "type": "weird"}]}]}
    with pytest.raises(ConfigError):
        parse_grammar(raw)


def test_missing_layers_errors():
    with pytest.raises(ConfigError):
        parse_grammar({})


def test_load_example_grammar_yaml():
    path = Path(__file__).resolve().parent.parent / "examples" / "grammar.yaml"
    grammar = load_grammar(path)
    parser = Parser(layers=grammar.layers)
    state = parser.parse("the book")
    assert state.tokens[1].labels.get("POS:NOUN") > 0
