"""enrich_claim: resolves what it can, says so when it cannot, stays out of other
domains' way."""

from __future__ import annotations

import pytest

from indicium_adapters_astronomy import AstronomyAdapter


@pytest.fixture
def adapter() -> AstronomyAdapter:
    return AstronomyAdapter()


def test_resolves_a_uat_concept_with_a_lexical_justification(adapter):
    out = adapter.enrich_claim(
        {"subject": "Red giant tip", "qualifier": "calibrated_against", "object": "Cepheids"}
    )
    assert out["ontology_terms"]["subject"] == "UAT:1371"
    assert out["ontology_term_justifications"]["subject"] == "semapv:LexicalMatching"


def test_records_slots_it_could_not_resolve_instead_of_staying_silent(adapter):
    """ "not a UAT concept" must be distinguishable from "not attempted"."""
    out = adapter.enrich_claim({"subject": "our bespoke pipeline v3", "object": "Distance measure"})
    assert out["ontology_terms"]["object"] == "UAT:395"
    assert out["ontology_terms_unmatched"]["subject"] == "our bespoke pipeline v3"
    assert "subject" not in out["ontology_terms"]


def test_does_not_overwrite_a_term_another_adapter_already_set(adapter):
    out = adapter.enrich_claim(
        {"subject": "Red giant tip", "ontology_terms": {"subject": "CHEBI:99999"}}
    )
    assert out["ontology_terms"]["subject"] == "CHEBI:99999"


def test_generic_terms_carry_their_branch_so_a_consumer_can_discount_them(adapter):
    """ "Mass spectrometry" is genuinely UAT:2094, so the CURIE is emitted — but
    its branch marks it as shared method vocabulary rather than astronomy's own."""
    out = adapter.enrich_claim({"subject": "Red giant tip", "object": "Mass spectrometry"})
    from indicium_adapters_astronomy import _uat

    assert out["ontology_term_branches"]["subject"] == "Observational astronomy"
    assert out["ontology_term_branches"]["object"] in _uat.GENERIC_BRANCHES


def test_leaves_a_claim_from_another_domain_untouched(adapter):
    """An astronomy adapter loaded alongside others must not invent terms for
    claims that are not astronomy — over-firing manufactures phantom mappings
    exactly as under-firing manufactures false-clean ones."""
    for claim in (
        {"subject": "MTBLS1234", "qualifier": "assayed_with", "object": "LC-MS/MS"},
        {"subject": "H3K27ac", "qualifier": "marked_by", "object": "promoter regions"},
        {"subject": "SRR1234567", "qualifier": "aligned_with", "object": "STAR"},
        {"subject": "glacier mass balance", "qualifier": "correlates_with", "object": "runoff"},
    ):
        out = adapter.enrich_claim(claim)
        assert not out.get("ontology_terms"), out.get("ontology_terms")


def test_non_string_and_empty_slots_are_skipped_not_crashed(adapter):
    out = adapter.enrich_claim({"subject": None, "object": "", "qualifier": 42})
    assert not out.get("ontology_terms")
    assert not out.get("ontology_terms_unmatched")


def test_technique_names_in_the_qualifier_slot_resolve(adapter):
    out = adapter.enrich_claim({"subject": "the sample", "qualifier": "Astrometry"})
    assert out["ontology_terms"]["qualifier"].startswith("UAT:")


def test_unrelated_keys_are_preserved(adapter):
    out = adapter.enrich_claim({"subject": "Cosmology", "claim_id": "c1", "confidence": 0.9})
    assert out["claim_id"] == "c1"
    assert out["confidence"] == 0.9
