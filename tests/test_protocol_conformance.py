"""The adapter must satisfy the DomainAdapter protocol and its RDF-boundary rules."""

from __future__ import annotations

import re

import pytest

from indicium_adapters_astronomy import AstronomyAdapter

_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")


@pytest.fixture
def adapter() -> AstronomyAdapter:
    return AstronomyAdapter()


def test_satisfies_the_structural_protocol(adapter):
    from indicium_adapters import CURRENT_API_VERSION, DomainAdapter

    assert isinstance(adapter, DomainAdapter)
    # An adapter whose api_version differs is skipped by discover_adapters() with
    # only a UserWarning — it would vanish silently rather than fail loudly.
    assert adapter.api_version == CURRENT_API_VERSION


def test_every_qualifier_is_snake_case(adapter):
    """Perspicacité routes adapter qualifiers onto the open ``asb:domainQualifier``
    slot, whose SHACL shape enforces this pattern. A non-conforming value would be
    rejected at the RDF boundary rather than reported here."""
    bad = [q for q in adapter.qualifiers if not _SNAKE_CASE.match(q)]
    assert not bad, f"non-snake_case qualifiers: {bad}"


def test_ontology_prefixes_are_expandable_iris(adapter):
    for prefix, base in adapter.ontology_prefixes.items():
        assert _SNAKE_CASE.match(prefix.lower()), prefix
        assert base.startswith("http"), (prefix, base)


def test_extraction_context_names_the_domain_and_its_qualifiers(adapter):
    ctx = adapter.extraction_context()
    assert "astronomy" in ctx.lower()
    # The prompt must actually carry the qualifiers, else the LLM cannot use them.
    for q in ("observed_with", "calibrated_against", "distance_measured_by"):
        assert q in ctx


def test_declares_primary_domain_so_asb_classification_picks_it_up(adapter):
    """ASB reads ``primary_domain`` in preference to ``domain_id`` and unions it
    into the controlled vocabulary; without it an astronomy paper stays "other"."""
    assert adapter.primary_domain == "astronomy"


def test_enrich_claim_is_pure(adapter):
    claim = {"subject": "Red giant tip", "qualifier": "calibrated_against", "object": "Cepheids"}
    snapshot = {k: v for k, v in claim.items()}
    adapter.enrich_claim(claim)
    assert claim == snapshot, "enrich_claim mutated its input"


def test_no_accession_patterns_live_in_this_package():
    """ADR 0001: accession recognition is owned by asb-domain-core's canonical
    table. A copy here would be the duplicate-then-drift failure the ADR exists to
    prevent, so the package must not carry accession regexes."""
    import pathlib

    import indicium_adapters_astronomy

    pkg = pathlib.Path(indicium_adapters_astronomy.__file__).parent
    offenders = []
    for path in pkg.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for shape in (r"MTBLS\d", r"PXD\d", r"GSE\d", r"ascl:\\d", r"10\\.17909", r"MSV\d"):
            if shape in text:
                offenders.append((path.name, shape))
    assert not offenders, f"accession patterns must not be duplicated here: {offenders}"
