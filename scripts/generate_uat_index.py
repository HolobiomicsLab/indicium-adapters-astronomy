#!/usr/bin/env python3
"""Regenerate ``_uat_index.json`` from an official Unified Astronomy Thesaurus release.

The adapter never guesses a UAT identifier: every CURIE it emits comes from this
generated index, and the index comes from the AAS release. Run this to move to a
new UAT version, then re-run the test suite — ``tests/test_uat_index.py`` pins the
provenance block and spot-checks identifiers against values printed independently
in a published AAS paper's keyword list.

    python scripts/generate_uat_index.py --release v6.0.0

Network access is required. Nothing else in the package touches the network.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import date
from pathlib import Path

_RAW = "https://raw.githubusercontent.com/astrothesaurus/UAT/{release}/{name}"
_OUT = (
    Path(__file__).resolve().parents[1] / "src" / "indicium_adapters_astronomy" / "_uat_index.json"
)


def _normalise(label: str) -> str:
    """Lookup key: case-folded, whitespace-collapsed. Must stay identical to
    ``_uat._normalise`` — a drift test asserts the two agree."""
    return " ".join(str(label).lower().split())


def _fetch(release: str, name: str) -> object:
    with urllib.request.urlopen(_RAW.format(release=release, name=name), timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build(release: str) -> dict:
    concept_list = _fetch(release, "UAT_list.json")
    tree = _fetch(release, "UAT_simple.json")

    labels: dict[str, str] = {}
    concepts: dict[str, str] = {}
    for concept in concept_list:
        uri = concept.get("uri") or ""
        cid = uri.rsplit("/", 1)[-1]
        name = concept.get("name")
        if not cid or not name:
            continue
        concepts[cid] = name
        # A preferred label always wins over an alternative one that normalises
        # to the same key, hence assignment here and setdefault below.
        labels[_normalise(name)] = cid
        for alt in concept.get("altNames") or []:
            labels.setdefault(_normalise(alt), cid)

    branches = {c["name"]: c["uri"].rsplit("/", 1)[-1] for c in tree["children"]}

    # Top-level branch per concept, walked from ``broader``. This is what lets a
    # consumer see that a matched term is generic method / statistics vocabulary
    # ("Mass spectrometry" and "Regression" sit under "Interdisciplinary
    # astronomy") rather than astronomy's own subject matter — the UAT is not
    # disjoint from other sciences' words, and pretending otherwise would either
    # drop legitimate astronomy usage or hide the ambiguity.
    by_id = {c["uri"].rsplit("/", 1)[-1]: c for c in concept_list if c.get("uri")}

    def _root(cid: str, depth: int = 0) -> str | None:
        concept = by_id.get(cid)
        if concept is None or depth > 12:
            return None
        broader = concept.get("broader") or []
        if not broader:
            return concept.get("name")
        return _root(broader[0]["uri"].rsplit("/", 1)[-1], depth + 1)

    branch_of = {cid: _root(cid) for cid in concepts}
    branch_of = {k: v for k, v in branch_of.items() if v}

    # Techniques come from the thesaurus too, not from a hand-written list: the
    # children of UAT "Astronomical techniques" under "Observational astronomy".
    techniques: dict[str, str] = {}
    for branch in tree["children"]:
        if branch.get("name") != "Observational astronomy":
            continue
        for sub in branch.get("children") or []:
            if sub.get("name") != "Astronomical techniques":
                continue
            for leaf in sub.get("children") or []:
                techniques[leaf["name"]] = leaf["uri"].rsplit("/", 1)[-1]

    return {
        "_provenance": {
            "source": "Unified Astronomy Thesaurus (UAT), American Astronomical Society",
            "release": release,
            "files": ["UAT_list.json", "UAT_simple.json"],
            "url": "https://github.com/astrothesaurus/UAT",
            "homepage": "http://astrothesaurus.org",
            "licence": "Creative Commons (see the UAT repository LICENSE.md)",
            "retrieved": date.today().isoformat(),
            "generator": "scripts/generate_uat_index.py",
            "note": (
                "GENERATED FILE — do not hand-edit. Regenerate with the script "
                "above to move to a new UAT release."
            ),
        },
        "top_level_branches": branches,
        "techniques": techniques,
        "branch_of": branch_of,
        "labels": labels,
        "concepts": concepts,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release", default="v6.0.0", help="UAT git tag (default: v6.0.0)")
    args = ap.parse_args()
    index = build(args.release)
    _OUT.write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"wrote {_OUT} — {len(index['concepts'])} concepts, "
        f"{len(index['labels'])} lookup labels, {len(index['top_level_branches'])} branches, "
        f"{len(index['techniques'])} techniques, "
        f"{len(index['branch_of'])} branch assignments"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
