"""Astronomy DomainAdapters for the indicium ecosystem.

Exposes :class:`AstronomyAdapter` via the ``indicium.adapters`` entry point, so
``indicium_adapters.discover_adapters()`` finds it on install and ASB's
classification vocabulary picks up ``primary_domain="astronomy"``.
"""

from .astronomy import AstronomyAdapter

__all__ = ["AstronomyAdapter", "__version__"]

__version__ = "0.1.0"
