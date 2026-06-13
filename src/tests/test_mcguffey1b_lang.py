"""mcguffey1b: the grammar/semantics layer over the tier-1 parser.

These tests pin the *new* behaviour — that the brakes reject the
salad mcguffey1 accepts, that real corpus coverage barely moves, and
that generation with the brakes engaged never emits a violation.
"""

from pathlib import Path

import pytest

from fsm_parser.mcguffey1_lang import parse as parse_m1
from fsm_parser.mcguffey1b_lang import (
    accept,
    critique,
    generate_lm,
    parse,
    text_violations,
    violations,
)

CORPUS = (Path(__file__).resolve().parent.parent.parent
          / "data" / "early_reader" / "sentences" / "mcguffey_primer.txt")

# the salad the author fed in: grammatical-by-mcguffey1, rejected here
SALAD = [
    "Schoolhouse eat.", "Let neck rocks.", "Walks John watch.",
    "Think frog stand.", "Loves.", "Drives wreaths has.",
    "Come ship for bell.", "Runs lighthouse shut.", "Plays night hold.",
    "Loves nag jump.", "Kill noise walks.", "Made noise cry.",
]


@pytest.mark.parametrize("sent", SALAD)
def test_salad_is_rejected(sent):
    # mcguffey1 lets it through (or returns frames); 1b must not
    assert parse(sent) is None, (sent, parse_m1(sent))


def test_specific_violation_codes():
    # valency: intransitive 'loves' with no theme... 'loves' is
    # transitive, so the lone verb fails THEME_REQUIRED
    assert "VAL:THEME_REQUIRED" in critique(parse_m1("Loves."))
    # selection: inanimate agent of an agentive verb
    assert "SEL:ANIMATE_AGENT" in violations(
        {"pred": "eat", "agent": "schoolhouse"})
    # agreement: 3sg verb, plural/2nd-person subject
    assert "AGR:3SG_NEEDS_SG_SUBJ" in violations(
        {"pred": "runs", "agent": "they"})
    # complementation: bare-inf clause under a non-licensor
    assert "EMB:NOT_LICENSED" in violations(
        {"pred": "think", "theme": {"pred": "stand", "agent": "frog"}})


def test_good_sentences_survive():
    for s in ["The cat has the rat.", "See Spot run.", "Ann can fan the lad.",
              "Spot is fast.", "Do not rob the nest.", "Dick and Jane play.",
              "The owl can see best at night.", "I like to see boys play.",
              "He ran at him.", "I see her.",          # case: correct pronouns
              "They will not let them drown.",          # ECM: accusative subject
              "Two girls have gone out for a walk.",    # perfect-aux have
              "It has a new dress."]:                   # main-verb have + object
        assert parse(s) is not None, s
        assert parse(s) == parse_m1(s)  # same frames, just gated


def test_linguistic_audit_corrections():
    """The five corrections from the linguistic audit — each observed
    string must now be rejected, with the grounded violation."""
    # 1. case: nominative pronoun in an accusative (prep-object) slot
    assert parse("Ran at he?") is None
    assert "CASE:ACC_POBJ:at" in text_violations("Ran at he?",
                                                 parse_m1("Ran at he?"))
    # 2/4. selection: fish is intransitive; drown wants an animate patient
    assert parse("Fish noise from me.") is None
    assert "SEL:ANIMATE_THEME" in violations(
        {"pred": "drown", "agent": "you", "theme": "eyes"})
    # 3. valency: frame closure for main-verb have
    assert parse("Made Dick have?") is None
    assert "VAL:HAVE_NEEDS_COMPLEMENT:have" in text_violations(
        "Made Dick have?", parse_m1("Made Dick have?"))
    # 5. animacy: inanimate self-mover (already covered, kept as a guard)
    assert parse("Runs lighthouse shut.") is None


def test_case_is_finiteness_sensitive_ecm():
    # matrix subject is nominative; ECM embedded subject is accusative
    assert "CASE:NOM_SUBJECT" in violations({"pred": "ran", "agent": "me"})
    assert violations({"pred": "ran", "agent": "me"}, finite=False) == \
        []  # accusative subject is fine when case is assigned from above
    assert "CASE:ACC_ECM_SUBJECT" in violations(
        {"pred": "drown", "agent": "they"}, finite=False)


def test_coverage_floor_holds():
    """The brakes raise precision without gutting recall: 1b must keep
    most of what mcguffey1 parsed on the real corpus."""
    sents = CORPUS.read_text().strip().split("\n")
    m1 = [s for s in sents if parse_m1(s)]
    kept = [s for s in m1 if parse(s) is not None]
    # mcguffey1 ≈ 0.655; the critic keeps ≥ 0.85 of it (ratchet)
    assert len(kept) / len(m1) >= 0.85, f"{len(kept)}/{len(m1)}"


def test_generation_never_emits_a_violation():
    """The brake steers, it does not merely judge: every sampled
    sentence is critic-clean by construction."""
    text = generate_lm(8, seed=100, temperature=0.8)
    for s in text.replace("? ", "?\n").replace(". ", ".\n").splitlines():
        s = s.strip()
        fr = parse_m1(s)
        assert fr, s
        assert accept(s, fr), (s, critique(fr))


def test_generation_is_deterministic():
    # temperature >= 0.8: the brakes shrink the target region, and a
    # cold field cannot explore enough to satisfy them (see GROWTH.md)
    assert (generate_lm(3, seed=5, temperature=0.9)
            == generate_lm(3, seed=5, temperature=0.9))
