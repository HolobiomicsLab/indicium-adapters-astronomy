"""The vendored UAT index: provenance, integrity, and identifiers verified against
a source outside this package."""

from __future__ import annotations

import json
import re
from pathlib import Path

from indicium_adapters_astronomy import _uat


def test_provenance_is_recorded():
    prov = _uat.provenance()
    assert prov["release"] == "v6.0.0"
    assert prov["url"] == "https://github.com/astrothesaurus/UAT"
    assert "Creative Commons" in prov["licence"]
    assert prov["generator"] == "scripts/generate_uat_index.py"


def test_identifiers_match_a_published_paper_keyword_block():
    """Independent check that the index is the real UAT and not a guess.

    AAS journals print UAT concept ids beside their keywords. These five are taken
    from the keyword block of Koblischke & Anderson (2024), ApJ,
    doi:10.3847/1538-4357/ad7095 — a source outside this package and outside the
    generator. If the index were fabricated or misparsed, these would not line up.
    """
    for label, expected_id in (
        ("Red giant tip", "1371"),
        ("Population II stars", "1284"),
        ("Distance measure", "395"),
        ("Small Magellanic Cloud", "1468"),
        ("Magellanic Clouds", "990"),
    ):
        assert _uat.lookup(label) == expected_id, label
        assert _uat.concept_label(expected_id) == label


def test_lookup_is_case_and_whitespace_insensitive():
    for variant in ("red giant tip", "RED GIANT TIP", "  Red   giant tip  "):
        assert _uat.lookup(variant) == "1371"


def test_lookup_resolves_alternative_labels():
    """altNames are indexed, so a paper's synonym still resolves."""
    index = json.loads(
        (Path(_uat.__file__).with_name("_uat_index.json")).read_text(encoding="utf-8")
    )
    # More lookup labels than concepts is the signature of altNames being indexed.
    assert len(index["labels"]) > len(index["concepts"])


def test_lookup_does_not_substring_match():
    """A wrong CURIE is worse than none: matching must be exact after normalisation."""
    assert _uat.lookup("tip") is None
    assert _uat.lookup("Red giant tip of the branch") is None


def test_lookup_misses_return_none_not_a_wrong_concept():
    # Deliberately terms with no UAT concept at all. NOT "mass spectrometry" —
    # the UAT really does contain it (UAT:2094, under Laboratory astrophysics),
    # which is the overlap the next test documents.
    for text in ("chromatin accessibility", "glacier mass balance", "promoter regions", ""):
        assert _uat.lookup(text) is None, text


def test_the_uat_overlaps_other_sciences_vocabulary_and_says_so():
    """The thesaurus contains generic method and statistics terms. A lexical match
    on those is a true mapping of the label but not evidence the astronomy sense
    was meant, so the level-1 branch is carried alongside so a consumer can judge.

    Recorded as a test because it is a property of the vocabulary, not a bug: a
    gate cannot be built at this layer (enrich_claim sees one claim, no document).
    """
    generic = {"mass spectrometry": "2094", "regression": "1914", "neural networks": "1933"}
    for label, cid in generic.items():
        assert _uat.lookup(label) == cid, label
        assert _uat.concept_branch(cid) in _uat.GENERIC_BRANCHES, label

    # Astronomy's own subject matter sits outside the generic branches.
    assert _uat.concept_branch("1371") == "Observational astronomy"
    assert _uat.concept_branch("1371") not in _uat.GENERIC_BRANCHES


def test_curie_and_expansion_round_trip():
    assert _uat.curie("1371") == "UAT:1371"
    assert _uat.expand("UAT:1371") == "http://astrothesaurus.org/uat/1371"
    assert _uat.expand("CHEBI:1234") is None


def test_every_concept_id_is_numeric_and_every_label_non_empty():
    index = json.loads(
        (Path(_uat.__file__).with_name("_uat_index.json")).read_text(encoding="utf-8")
    )
    for cid, label in index["concepts"].items():
        assert re.fullmatch(r"\d+", cid), cid
        assert label.strip(), cid
    for key, cid in index["labels"].items():
        assert key == " ".join(key.lower().split()), f"unnormalised lookup key: {key!r}"
        assert cid in index["concepts"], f"label {key!r} points at unknown concept {cid}"


def test_generator_and_loader_normalise_identically():
    """If the two normalisers drift, every lookup silently misses."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen", Path(__file__).resolve().parents[1] / "scripts" / "generate_uat_index.py"
    )
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    for sample in ("Red Giant Tip", "  Mass   Function ", "SMC", ""):
        assert gen._normalise(sample) == _uat._normalise(sample)


def test_vocabulary_comes_from_the_thesaurus_not_a_hand_list():
    branches = _uat.top_level_branches()
    assert len(branches) == 11
    assert branches["Stellar astronomy"] == "1583"
    assert branches["Cosmology"] == "343"
    techniques = _uat.techniques()
    assert "Astrometry" in techniques
    assert all(re.fullmatch(r"\d+", v) for v in techniques.values())
