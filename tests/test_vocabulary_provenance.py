"""Every declared astronomy term is either a UAT concept or knowingly not one.

The adapter's vocabulary is read from the Unified Astronomy Thesaurus so it
moves with a UAT release rather than with an editor's opinion. Two named lists
qualify that read, and each carries a different promise:

``_SUBFIELDS`` / ``_METHODS`` widen it. Most of their members ARE published UAT
concepts sitting deeper than a level-1 branch or an "Astronomical techniques"
leaf -- ``transit photometry`` is UAT 1709 under "Exoplanet astronomy" -- so
naming them reaches more of the field's own vocabulary. The rest the corpus
attests and UAT does not carry.

``_NON_DISCRIMINATING`` narrows it, withholding the leaves other sciences share.

Both promises rot silently. A term withheld under a label UAT has since renamed
withholds nothing; a term declared as "UAT does not carry this" that UAT later
adopts leaves a duplicate spelling beside the real concept. These tests pin each
term against the shipped index, so a UAT upgrade turns the guard red and the
lists get revisited instead of quietly drifting.

Run: python3 -m pytest tests/test_vocabulary_provenance.py -q
"""

from __future__ import annotations

import pytest

from indicium_adapters_astronomy import _uat
from indicium_adapters_astronomy.astronomy import (
    _METHODS,
    _NON_DISCRIMINATING,
    _SUBFIELDS,
    AstronomyAdapter,
)

# Members UAT carries today. The rest of each list is attested by the corpus
# and absent from the thesaurus; the split is asserted below in both directions.
IN_THESAURUS = frozenset({
    "asteroseismology", "celestial-mechanics", "extragalactic-astronomy",
    "gamma-ray-astronomy", "infrared-astronomy", "planetary-science",
    "radio-astronomy", "solar-physics", "star-formation", "stellar-astrophysics",
    "time-domain-astronomy", "adaptive-optics", "doppler-imaging",
    "gravitational-microlensing", "transit-photometry",
    "very-long-baseline-interferometry",
})


def concept_of(term: str) -> str | None:
    """Return the UAT concept id `term` names, or None."""
    return _uat.lookup(term.replace("-", " "))


@pytest.mark.parametrize("term", sorted(set(_SUBFIELDS) | set(_METHODS)))
def test_a_widening_term_is_either_a_uat_concept_or_declared_absent(term: str) -> None:
    """No third state: a term is in the thesaurus or it is knowingly not."""
    found = concept_of(term) is not None

    assert found == (term in IN_THESAURUS), (
        f"{term!r} is {'now' if found else 'no longer'} a UAT concept; "
        "move it across IN_THESAURUS and check it is not a duplicate spelling"
    )


@pytest.mark.parametrize("term", sorted(_NON_DISCRIMINATING))
def test_a_withheld_term_is_still_a_technique_leaf(term: str) -> None:
    """Withholding a leaf UAT no longer publishes withholds nothing at all."""
    leaves = {name.lower().replace(" ", "-") for name in _uat.techniques()}

    assert term in leaves, f"{term!r} is no longer a UAT technique leaf"


def test_the_shared_terms_are_absent_from_what_the_adapter_declares() -> None:
    """The point of the whole exercise: astronomy stops claiming them."""
    declared = set(AstronomyAdapter().techniques)

    assert not (declared & _NON_DISCRIMINATING)
    assert "mass-spectrometry" not in declared, "a metabolomics and proteomics term"


def test_withholding_did_not_empty_the_vocabulary() -> None:
    """A narrowed adapter must still be able to claim its own papers."""
    adapter = AstronomyAdapter()

    assert len(adapter.techniques) > len(_NON_DISCRIMINATING)
    assert "transit-photometry" in adapter.techniques
    assert "asteroseismology" in adapter.subdomains


def test_enrichment_still_sees_the_whole_thesaurus() -> None:
    """Narrowing the domain claim must not narrow concept resolution.

    A paper doing spacecraft mass spectrometry keeps its UAT CURIE; what it
    stops doing is counting as evidence of which field the paper is in.
    """
    assert concept_of("mass-spectrometry") is not None
    assert concept_of("spectroscopy") is not None


if __name__ == "__main__":  # offline smoke: runs this module's tests
    raise SystemExit(pytest.main([__file__, "-q"]))
