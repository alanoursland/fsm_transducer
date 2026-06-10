import json
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent


def _run(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "fsm_parser", *args],
        cwd=SRC,
        capture_output=True,
        text=True,
        input=input_text,
        check=False,
    )


def test_cli_parse_text_argument():
    result = _run(["parse", "The cat slept."])
    assert result.returncode == 0, result.stderr
    assert "Layer" in result.stdout
    assert "cat" in result.stdout


def test_cli_parse_json_output():
    result = _run(["parse", "The cat", "--json"])
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["layer"] >= 1
    assert any(t["text"] == "cat" for t in payload["tokens"])


def test_cli_trace_includes_layers():
    result = _run(["trace", "The cat"])
    assert result.returncode == 0, result.stderr
    assert "Layer 0" in result.stdout
    assert "Layer 1" in result.stdout


def test_cli_grammar_yaml_loads():
    grammar = SRC / "examples" / "grammar.yaml"
    result = _run(["parse", "the book", "-g", str(grammar)])
    assert result.returncode == 0, result.stderr
    assert "book" in result.stdout


def test_cli_reads_stdin_when_no_text():
    result = _run(["parse"], input_text="The cat slept.\n")
    assert result.returncode == 0, result.stderr
    assert "cat" in result.stdout
