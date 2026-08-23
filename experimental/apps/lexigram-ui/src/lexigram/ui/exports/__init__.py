"""Re-export submodules for the ``lexigram.ui`` public surface.

Static-analysis re-exports (``atoms``, ``molecules``, ``layouts``) plus
the runtime surface data (``lazy`` import map, ``public`` ``__all__``),
so the top-level ``lexigram.ui`` package stays small and import-cheap.
"""
