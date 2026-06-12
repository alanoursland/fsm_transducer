"""Command-line entry point.

Examples (from inside the ``src`` directory):

    python -m fsm_parser parse "The book fell."
    python -m fsm_parser trace "I can book flights."
    python -m fsm_parser parse --grammar examples/grammar.yaml "The cat slept."
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsm_parser.config import load_grammar
from fsm_parser.debug import render_state, render_trace
from fsm_parser.grammar import build_default_parser
from fsm_parser.labels import AddSlot, LabelDelta
from fsm_parser.pipeline import Parser
from fsm_parser.tokens import ParserState


def _make_parser_from_args(args: argparse.Namespace) -> Parser:
    if args.grammar:
        grammar = load_grammar(args.grammar)
        return Parser(layers=grammar.layers)
    return build_default_parser()


def _slot_to_dict(slot) -> dict:
    return {
        "id": slot.id,
        "kind": slot.kind,
        "stream": slot.stream,
        "text": slot.text,
        "source_span": (
            [slot.source_span.start, slot.source_span.end]
            if slot.source_span is not None
            else None
        ),
        "labels": dict(slot.labels.weights),
    }


def _state_to_dict(state: ParserState) -> dict:
    return {
        "layer": state.layer,
        "tokens": [
            {
                "index": t.index,
                "text": t.text,
                "labels": dict(t.labels.weights),
            }
            for t in state.tokens
        ],
        "streams": {
            name: [_slot_to_dict(s) for s in slots]
            for name, slots in state.streams.items()
        },
    }


def _delta_to_dict(d) -> dict:
    if isinstance(d, LabelDelta):
        return {
            "type": "add_label",
            "slot_id": d.slot_id,
            "token_index": d.token_index,
            "label": d.label,
            "weight": d.weight,
            "source": d.source,
        }
    if isinstance(d, AddSlot):
        return {
            "type": "add_slot",
            "stream": d.stream,
            "slot": _slot_to_dict(d.slot),
            "source": d.source,
        }
    return {"type": "unknown", "repr": repr(d)}


def cmd_parse(args: argparse.Namespace) -> int:
    parser = _make_parser_from_args(args)
    text = _read_input(args)
    state = parser.parse(text)
    if args.json:
        json.dump(_state_to_dict(state), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(render_state(state, top_k=args.top_k))
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    parser = _make_parser_from_args(args)
    text = _read_input(args)
    _, traces = parser.parse_with_trace(text)
    if args.json:
        out = [
            {
                "layer": t.layer,
                "blocks": t.block_names,
                "deltas": [_delta_to_dict(d) for d in t.deltas],
                "state": _state_to_dict(t.state),
            }
            for t in traces
        ]
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(render_trace(traces, top_k=args.top_k))
    return 0


def cmd_mcguffey1(args: argparse.Namespace) -> int:
    from fsm_parser.mcguffey1_lm import _prompt_tokens, generate_lm

    print(generate_lm(
        args.n_sentences,
        seed=args.seed,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        prompt=_prompt_tokens(args.prompt),
        max_tries=args.max_tries,
    ))
    return 0


def _read_input(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.file:
        return Path(args.file).read_text()
    return sys.stdin.read()


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fsm-parser")
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("text", nargs="?", help="text to parse")
    common.add_argument("--file", "-f", help="read input from file")
    common.add_argument("--grammar", "-g", help="path to grammar YAML")
    common.add_argument("--json", action="store_true", help="emit JSON output")
    common.add_argument("--top-k", type=int, default=5, help="labels per token")

    parse = sub.add_parser("parse", parents=[common], help="parse text")
    parse.set_defaults(func=cmd_parse)

    trace = sub.add_parser("trace", parents=[common], help="parse with layer trace")
    trace.set_defaults(func=cmd_trace)

    lm = sub.add_parser("mcguffey1", help="generate McGuffey tier-1 text")
    lm.add_argument(
        "n_sentences",
        nargs="?",
        type=int,
        default=5,
        help="number of sentences to generate (default: 5)",
    )
    lm.add_argument("--seed", type=int, help="random seed for deterministic output")
    lm.add_argument(
        "--temperature",
        "-t",
        type=float,
        default=1.0,
        help="sampling temperature (default: 1.0)",
    )
    lm.add_argument(
        "--max-tokens",
        type=int,
        default=10,
        help="maximum tokens per sampled sentence before rejection (default: 10)",
    )
    lm.add_argument(
        "--prompt",
        help="prefix tokens each generated sentence must continue, e.g. 'the cat'",
    )
    lm.add_argument(
        "--max-tries",
        type=int,
        default=200,
        help="rejection-sampling attempts per sentence (default: 200)",
    )
    lm.set_defaults(func=cmd_mcguffey1)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
