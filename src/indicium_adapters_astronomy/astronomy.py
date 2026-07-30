"""AstronomyAdapter — the astronomy DomainAdapter (api_version=1)."""

from __future__ import annotations

from typing import Final

from . import _uat

# Claim slots worth resolving against the thesaurus. ``qualifier`` is included
# because a qualifier literal sometimes carries a technique name ("astrometry"),
# which is itself a UAT concept.
_ENRICHABLE_SLOTS: Final[tuple[str, ...]] = ("subject", "object", "qualifier")

# SSSOM justification for a label / alternative-label string match. Every CURIE
# this adapter emits comes from exact-after-normalisation matching against the
# published UAT, so this is the only justification it can honestly claim.
_LEXICAL: Final[str] = "semapv:LexicalMatching"


class AstronomyAdapter:
    """Observational astronomy and astrophysics.

    Owns the tier-3 concerns only (ADR 0001): the classification vocabulary and
    claim/ontology enrichment. It deliberately does **not** recognise repository
    accessions — those belong to the canonical accession table in
    ``asb-domain-core``, and a second copy of those patterns here would be the
    duplicate-then-drift failure that ADR 0001 exists to prevent. What this
    adapter contributes for identifiers is ``ontology_prefixes``, so a consumer
    can expand the CURIEs that tier produces.

    The concept vocabulary is the **whole** Unified Astronomy Thesaurus (UAT
    v6.0.0, 2411 concepts, 4219 preferred + alternative labels), vendored as a
    generated index with provenance. External advice (2026-07-30) confirmed the
    UAT is the right spine for astronomy topic tagging, and that astronomy has no
    counterpart to EDAM's *operations* and *data formats* vocabularies — so this
    adapter declares subject matter and techniques, and file formats stay in the
    ASB domain profile's ``format_registry`` where they can be curated.

    ``subdomains`` and ``techniques`` are read from the thesaurus itself (its
    level-1 branches, and the leaves of "Astronomical techniques") rather than
    hand-listed, so the vocabulary is the field's own and moves with a UAT
    release rather than with an editor's opinion.

    Every qualifier matches ``^[a-z][a-z0-9_]*$`` (snake_case), required because
    Perspicacité routes adapter qualifiers onto the open ``asb:domainQualifier``
    slot whose SHACL shape enforces that pattern; non-conforming values would be
    rejected at the RDF boundary. Enforced by
    ``tests/test_protocol_conformance.py``.
    """

    domain_id = "astronomy"
    api_version = 1

    # ASB's classification layer reads ``primary_domain`` in preference to
    # ``domain_id`` (see agentic_science_builder.classification._adapter_vocab),
    # and unions it into the controlled vocabulary. Declaring it here is what
    # stops an astronomy paper classifying as "other".
    primary_domain = "astronomy"

    qualifiers: frozenset[str] = frozenset(
        {
            # --- Observation and provenance of a measurement ------------------
            "observed_with",  # object is an instrument, telescope or survey
            "measured_from",  # object is a data product the value came from
            "detected_in",  # object is a band, survey or epoch
            "cross_matched_with",  # object is another catalogue
            "selected_by",  # object is a selection criterion or cut
            # --- Calibration and the distance ladder --------------------------
            "calibrated_against",  # object is a standard, zero point or anchor
            "standardized_by",  # object is the quantity used to standardise
            "distance_measured_by",  # object is the distance indicator or method
            "corrected_for",  # object is extinction, reddening, a bias, a blend
            # --- Membership and location --------------------------------------
            "member_of",  # object is a cluster, galaxy or population
            "located_in",  # object is a region, field or footprint
            "hosts",  # object is a companion, planet, remnant, disc
            # --- Physical and statistical relations ---------------------------
            "correlates_with",
            "anti_correlates_with",
            "scales_with",  # a period-luminosity / mass-metallicity style relation
            "varies_with_period",
            "derived_from_model",  # object is an isochrone, track or synthesis model
            "fitted_with",  # object is the fitting method or functional form
            "constrains",  # object is the parameter the observation constrains
            "degenerate_with",  # object is the parameter it trades against
        }
    )

    ontology_prefixes: dict[str, str] = {
        # The concept spine.
        "UAT": _uat.UAT_BASE_IRI,
        # Identifier namespaces this adapter does NOT mine but whose CURIEs a
        # consumer may need to expand. Recognition of these lives in
        # asb-domain-core's canonical accession table.
        "ASCL": "https://ascl.net/",
        "IVOA": "http://www.ivoa.net/rdf/",
        "SIMBAD": "https://simbad.cds.unistra.fr/simbad/sim-id?Ident=",
        "VizieR": "https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=",
        "ADS": "https://ui.adsabs.harvard.edu/abs/",
        "MAST": "https://archive.stsci.edu/",
    }

    # ---- vocabulary sourced from the thesaurus -----------------------------

    @property
    def subdomains(self) -> tuple[str, ...]:
        """The UAT's own level-1 branches, lower-cased and hyphenated."""
        return tuple(sorted(_slug(name) for name in _uat.top_level_branches()))

    @property
    def techniques(self) -> tuple[str, ...]:
        """The leaves of UAT "Astronomical techniques", lower-cased and hyphenated."""
        return tuple(sorted(_slug(name) for name in _uat.techniques()))

    # ---- protocol methods --------------------------------------------------

    def extraction_context(self) -> str:
        return (
            "Domain: observational astronomy and astrophysics. Name subjects and "
            "objects with the terminology of the Unified Astronomy Thesaurus "
            "where one applies (for example 'red giant tip', 'distance measure', "
            "'period-luminosity relation'), using the singular preferred label "
            "rather than a paraphrase. Prefer a concrete instrument, survey or "
            "data-release name over a generic word: 'Gaia DR2' rather than "
            "'the catalogue'. Domain qualifiers available in addition to the base "
            "set: " + ", ".join(sorted(self.qualifiers)) + "."
        )

    def enrich_claim(self, claim: dict) -> dict:
        """Attach UAT CURIEs to the slots whose text names a UAT concept.

        Pure: returns a new dict and never mutates the input.

        Matching is exact after case-folding and whitespace collapse. Substring
        and fuzzy matching over a 2411-term thesaurus manufacture
        confident-looking wrong CURIEs ("Mass" inside "Mass function"), and a
        wrong identifier is worse than no identifier.

        A slot that carries text but resolves to nothing is recorded under
        ``ontology_terms_unmatched`` rather than passed over. Silence would make
        "this text is not a UAT concept" indistinguishable from "no attempt was
        made", which is the distinction a downstream mapping set needs.
        """
        out = dict(claim)
        terms: dict[str, str] = dict(out.get("ontology_terms") or {})
        justifications: dict[str, str] = dict(out.get("ontology_term_justifications") or {})
        unmatched: dict[str, str] = dict(out.get("ontology_terms_unmatched") or {})
        branches: dict[str, str] = dict(out.get("ontology_term_branches") or {})

        for slot in _ENRICHABLE_SLOTS:
            if slot in terms:
                continue  # another adapter already resolved this slot
            value = out.get(slot)
            if not isinstance(value, str) or not value.strip():
                continue
            concept_id = _uat.lookup(value)
            if concept_id:
                terms[slot] = _uat.curie(concept_id)
                justifications[slot] = _LEXICAL
                branch = _uat.concept_branch(concept_id)
                if branch:
                    branches[slot] = branch
                unmatched.pop(slot, None)
            else:
                unmatched[slot] = value

        if terms:
            out["ontology_terms"] = terms
            out["ontology_term_justifications"] = justifications
        if branches:
            out["ontology_term_branches"] = branches
        if unmatched:
            out["ontology_terms_unmatched"] = unmatched
        return out


def _slug(label: str) -> str:
    """ "Galactic and extragalactic astronomy" -> "galactic-and-extragalactic-astronomy"."""
    return "-".join(str(label).lower().split())
