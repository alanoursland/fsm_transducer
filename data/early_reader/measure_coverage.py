"""Measure a tier language's coverage of its corpus file.

The growth-curve experiment (Steele protocol): coverage = fraction of
corpus sentences producing at least one well-formed frame. Reports
overall coverage, the curve over corpus order (the primer escalates
difficulty, so the curve is the growth story), and a failure sample
for the next growth iteration.

    python measure_coverage.py [tier_file] [--failures N]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fsm_parser.mcguffey1_lang import compile_text, run_program  # noqa: E402


def measure(path: Path, n_failures: int = 25) -> None:
    sentences = path.read_text().strip().split("\n")
    results = []
    for s in sentences:
        r = compile_text(s)
        if r.errors:
            results.append((s, "unknown-word"))
            continue
        res = run_program(r.program)
        if res.valid and res.frames:
            results.append((s, None))
        elif res.frames:
            results.append((s, "leftover-stack"))
        else:
            results.append((s, "no-frame"))

    ok = sum(1 for _, f in results if f is None)
    print(f"{path.name}: {ok}/{len(results)} = {ok/len(results):.1%} coverage")

    # curve over corpus order (deciles)
    n = len(results)
    print("curve (corpus order, deciles):", end=" ")
    for d in range(10):
        chunk = results[d * n // 10:(d + 1) * n // 10]
        good = sum(1 for _, f in chunk if f is None)
        print(f"{good/len(chunk):.0%}", end=" ")
    print()

    fails = [(s, f) for s, f in results if f is not None]
    by_kind: dict[str, int] = {}
    for _, f in fails:
        by_kind[f] = by_kind.get(f, 0) + 1
    print("failure kinds:", by_kind)
    print(f"\nfirst {n_failures} failures:")
    for s, f in fails[:n_failures]:
        print(f"  [{f}] {s}")


if __name__ == "__main__":
    tier = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(__file__).parent / "sentences" / "mcguffey_primer.txt"
    measure(tier)
