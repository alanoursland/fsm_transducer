from pathlib import Path

from fsm_parser.config import load_grammar, parse_grammar
from fsm_parser.pipeline import Parser


def test_combinator_grammar_yaml_loads_and_runs():
    path = Path(__file__).resolve().parent.parent / "examples" / "grammar_combinators.yaml"
    grammar = load_grammar(path)
    parser = Parser(layers=grammar.layers)
    state = parser.parse("the big red dog")
    dog = next(t for t in state.tokens if t.text == "dog")
    the = next(t for t in state.tokens if t.text == "the")
    assert dog.labels.get("PHRASE:NP_HEAD") > 0
    assert the.labels.get("PHRASE:NP_START") > 0


def test_combinator_grammar_handles_no_adjs():
    path = Path(__file__).resolve().parent.parent / "examples" / "grammar_combinators.yaml"
    grammar = load_grammar(path)
    parser = Parser(layers=grammar.layers)
    state = parser.parse("the dog")
    dog = next(t for t in state.tokens if t.text == "dog")
    assert dog.labels.get("PHRASE:NP_HEAD") > 0


def test_inline_combinator_grammar():
    raw = {
        "layers": [
            {
                "blocks": [
                    {
                        "name": "lex",
                        "type": "lexical",
                        "entries": {"x": {"X": 1.0}, "y": {"Y": 1.0}},
                    }
                ]
            },
            {
                "blocks": [
                    {
                        "name": "rule",
                        "type": "fsm",
                        "fsms": [
                            {
                                "name": "alt_rule",
                                "machine": {
                                    "op": "alt",
                                    "machines": [
                                        {
                                            "op": "literal",
                                            "match": {"has": "X"},
                                            "emit": [{"label": "X_HIT", "weight": 1.0}],
                                        },
                                        {
                                            "op": "literal",
                                            "match": {"has": "Y"},
                                            "emit": [{"label": "Y_HIT", "weight": 1.0}],
                                        },
                                    ],
                                },
                            }
                        ],
                    }
                ]
            },
        ]
    }
    grammar = parse_grammar(raw)
    parser = Parser(layers=grammar.layers)
    state = parser.parse("x y")
    assert state.tokens[0].labels.get("X_HIT") > 0
    assert state.tokens[1].labels.get("Y_HIT") > 0
