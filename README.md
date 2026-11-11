# indicium-adapters-astronomy

An astronomy `DomainAdapter` for the [indicium](https://github.com/HolobiomicsLab/indicium)
ecosystem: Unified Astronomy Thesaurus concept enrichment for validated claims, and the
classification vocabulary that lets AgenticScienceBuilder recognise an astronomy paper as
astronomy.

## What it does

- **Declares the domain.** `domain_id` and `primary_domain` are `"astronomy"`. ASB's
  classification layer unions the `primary_domain`, `subdomains` and `techniques` of every
  installed adapter into its controlled vocabulary, so installing this package is what stops
  an astronomy paper being classified as `other`.
- **Enriches claims with UAT concepts.** `enrich_claim` attaches a `UAT:` CURIE to any claim
  slot whose text names a UAT concept, with a `semapv:LexicalMatching` justification for
  downstream SSSOM emitters.
- **Publishes the prefixes** needed to expand astronomy CURIEs (`UAT`, `ASCL`, `IVOA`,
  `SIMBAD`, `VizieR`, `ADS`, `MAST`).

## What it deliberately does not do

**It does not recognise repository accessions.** Under ADR 0001 those belong to the canonical
accession table in `asb-domain-core`, which is the single source of truth for accession
patterns; a second copy here would be the duplicate-then-drift failure that architecture
exists to prevent. The astronomy families (MAST DOI, ASCL record, VizieR catalogue DOI, IVOA
`ivo://`) live there. A test in this package greps its own source for accession shapes and
fails if any appear.

**It does not declare a vocabulary of operations or data formats.** Astronomy has no
counterpart to EDAM's operation and format branches — confirmed with a domain expert,
2026-07-30. File formats therefore stay in the ASB domain profile's `format_registry`, where
they can be curated with a per-format authoritative reference, rather than being invented here.

## The vocabulary is the thesaurus, not an editor's list

The concept vocabulary is the **whole** Unified Astronomy Thesaurus — UAT v6.0.0, 2411
concepts, 4219 preferred and alternative labels — vendored as a generated index under
`src/indicium_adapters_astronomy/_uat_index.json` with a provenance block recording the
release, source URL, licence and retrieval date.

A curated subset was rejected on purpose: a hand-picked list is a closed vocabulary that
returns "no term" for everything outside it, and a term absent for that reason is
indistinguishable from a term that genuinely has no UAT concept.

`subdomains` and `techniques` are read from the thesaurus too — its level-1 branches, and the
leaves of "Astronomical techniques" — so they move with a UAT release rather than with a
maintainer's opinion.

Regenerate for a newer release with:

```bash
python scripts/generate_uat_index.py --release v6.1.0
```

`tests/test_uat_index.py` then re-verifies five identifiers against a source outside this
package: the UAT ids that Koblischke & Anderson (2024), ApJ, `doi:10.3847/1538-4357/ad7095`
print beside their keywords. If the index were fabricated or misparsed those would not line up.

## Two honest limitations

**Matching is exact after case-folding and whitespace collapse.** Substring and fuzzy matching
over a 2411-term thesaurus manufacture confident-looking wrong CURIEs — `"Mass"` inside
`"Mass function"` — and a wrong identifier is worse than no identifier. The cost is recall: a
paraphrase does not resolve. A slot that carries text but matches nothing is recorded under
`ontology_terms_unmatched` rather than passed over in silence, so "not a UAT concept" stays
distinguishable from "not attempted".

**The UAT is not disjoint from other sciences' words.** It genuinely contains *Mass
spectrometry* (`UAT:2094`), *Spectroscopy*, *Calibration*, *Regression* and *Neural networks*.
A lexical match on those is a true mapping of the label but not evidence that the astronomy
sense was meant. Rather than invent a gate this layer cannot support — `enrich_claim` sees one
claim, with no document context — each term carries its UAT level-1 branch in
`ontology_term_branches`. Terms under `Interdisciplinary astronomy` (Astrostatistics,
Laboratory astrophysics) are the generic ones; `_uat.GENERIC_BRANCHES` names them. A consumer
composing several adapters should prefer a domain-specific adapter's term for such a slot, and
`enrich_claim` never overwrites a term another adapter has already set.

## Install

The public dependencies are installed from PyPI with the development extra:

```bash
python -m pip install -e ".[dev]"
```

`requires-python >= 3.11`, matching the published base packages, so this package can be
installed into the AgenticScienceBuilder environment where the classification vocabulary it
feeds is consumed.

## Licence

Code: MIT. The vendored UAT index is derived from the Unified Astronomy Thesaurus, © American
Astronomical Society, released under a Creative Commons licence; see
<https://github.com/astrothesaurus/UAT> and the `_provenance` block in the index.
