import builtins
import importlib


def _raise_import_for(names):
    orig = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        for n in names:
            if name == n or name.startswith(n + "."):
                raise ImportError(f"No module named {n}")
        return orig(name, globals, locals, fromlist, level)

    return fake_import


def test_clip_module_imports_do_not_require_heavy_packages(monkeypatch):
    """Importing the clip module should not execute heavy imports at module import-time.

    The module should only raise on initialization (when a user tries to use CLIPEmbedding),
    not when importing the module itself.
    """
    monkeypatch.setattr(
        builtins, "__import__", _raise_import_for(["transformers", "torch", "PIL"]),
    )

    # Should be able to import the module even if heavy deps are missing
    mod = importlib.import_module("lexigram.ai.rag.multimodal.embeddings.clip")
    assert hasattr(mod, "CLIPEmbedding")
