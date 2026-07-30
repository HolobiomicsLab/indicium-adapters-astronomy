"""Unified Astronomy Thesaurus lookup — the adapter's only concept vocabulary.

Loaded once from the generated ``_uat_index.json`` (see
``scripts/generate_uat_index.py``). No network, no I/O beyond that one read, so
``enrich_claim`` stays the pure function the DomainAdapter protocol requires.

Why the whole thesaurus rather than a curated subset: a hand-picked list is a
closed vocabulary that silently returns "no term" for everything outside it, and
a term absent for that reason is indistinguishable from a term that genuinely has
no UAT concept. Shipping all 2411 concepts removes the distinction problem, and
:func:`lookup` reports a miss explicitly so a caller can tell "not in the UAT"
from "not attempted".
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Final

_INDEX_PATH: Final[Path] = Path(__file__).with_name("_uat_index.json")

UAT_PREFIX: Final[str] = "UAT"
UAT_BASE_IRI: Final[str] = "http://astrothesaurus.org/uat/"


def _normalise(label: str) -> str:
    """Lookup key: case-folded, whitespace-collapsed.

    Must stay identical to ``scripts/generate_uat_index.py::_normalise`` — if the
    two ever diverge every lookup silently misses, so a test pins them together.
    """
    return " ".join(str(label).lower().split())


@lru_cache(maxsize=1)
def _index() -> dict:
    return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))


def provenance() -> dict:
    """Where the vocabulary came from — release, URL, licence, retrieval date."""
    return dict(_index()["_provenance"])


def top_level_branches() -> dict[str, str]:
    """The UAT's own level-1 branches, ``{label: concept_id}``.

    These are the adapter's ``subdomains``: taking them from the thesaurus rather
    than inventing a list means the subdomain vocabulary is the field's own.
    """
    return dict(_index()["top_level_branches"])


def techniques() -> dict[str, str]:
    """UAT "Astronomical techniques" leaves, ``{label: concept_id}``.

    The adapter's ``techniques`` vocabulary, again taken from the thesaurus rather
    than hand-listed.
    """
    return dict(_index()["techniques"])


def concept_label(concept_id: str) -> str | None:
    """Preferred label for a UAT concept id, or None if unknown."""
    return _index()["concepts"].get(str(concept_id))


#: UAT branches whose leaves are generic method / statistics / laboratory
#: vocabulary shared with other sciences ("Mass spectrometry", "Regression",
#: "Neural networks"), as opposed to astronomy's own subject matter. Derived from
#: the thesaurus, not hand-listed.
GENERIC_BRANCHES: Final[frozenset[str]] = frozenset({"Interdisciplinary astronomy"})


def concept_branch(concept_id: str) -> str | None:
    """The UAT level-1 branch a concept sits under, or None if unknown.

    A consumer composing several domain adapters uses this to see that a matched
    term is shared vocabulary rather than astronomy-specific: the UAT genuinely
    contains "Mass spectrometry" and "Regression", so a lexical match on those
    words is a true mapping of the label but not evidence the astronomy sense was
    meant.
    """
    return _index()["branch_of"].get(str(concept_id))


def lookup(text: str) -> str | None:
    """Return the UAT concept id whose preferred or alternative label matches
    *text* exactly after normalisation, else None.

    Deliberately exact-after-normalisation: substring or fuzzy matching over a
    2411-term thesaurus produces confident-looking wrong CURIEs (``"Mass"``
    inside ``"Mass function"``), and a wrong identifier is worse than none.
    """
    if not text:
        return None
    return _index()["labels"].get(_normalise(text))


def curie(concept_id: str) -> str:
    """``1371`` -> ``UAT:1371``."""
    return f"{UAT_PREFIX}:{concept_id}"


def expand(curie_str: str) -> str | None:
    """``UAT:1371`` -> ``http://astrothesaurus.org/uat/1371``; None if not a UAT CURIE."""
    prefix, _, local = str(curie_str).partition(":")
    if prefix != UAT_PREFIX or not local:
        return None
    return f"{UAT_BASE_IRI}{local}"
