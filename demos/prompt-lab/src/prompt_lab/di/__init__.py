"""Dependency injection wiring.

The ``LabProvider`` seeds prompt template revisions at registration and
assembles the deterministic A/B runner at boot — demonstrating the
two-phase Provider lifecycle (register = bind, boot = initialise).
"""
