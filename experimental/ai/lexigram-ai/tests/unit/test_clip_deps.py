
import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

import builtins
import sys
from types import SimpleNamespace


from lexigram.ai.rag.multimodal.embeddings.clip import CLIPEmbedding


def _raise_import_for(names):
    """Return a fake __import__ that raises ImportError for the given names."""

    orig = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        for n in names:
            if name == n or name.startswith(n + "."):
                raise ImportError(f"No module named {n}")
        return orig(name, globals, locals, fromlist, level)

    return fake_import


def test_clip_raises_helpful_error_when_missing(monkeypatch):
    # Simulate missing heavy libs
    monkeypatch.setattr(
        builtins, "__import__", _raise_import_for(["transformers", "torch", "PIL"]),
    )

    with pytest.raises(ImportError) as ei:
        CLIPEmbedding()

    assert "Install with" in str(ei.value) or "lexigram-ai" in str(ei.value)


def test_clip_initializes_when_deps_mocked(monkeypatch):
    # Provide fake minimal transformers/torch/PIL modules in sys.modules
    from importlib.machinery import ModuleSpec
    from types import ModuleType

    # Create a fake transformers module with a proper __spec__ so find_spec works
    fake_transformers = ModuleType("transformers")
    fake_transformers.__spec__ = ModuleSpec("transformers", None)
    fake_transformers.CLIPModel = SimpleNamespace(
        from_pretrained=lambda name: SimpleNamespace(
            to=lambda device: None,
            eval=lambda: None,
            config=SimpleNamespace(projection_dim=512),
        ),
    )
    fake_transformers.CLIPProcessor = SimpleNamespace(
        from_pretrained=lambda name: lambda *args, **kwargs: {},
    )

    fake_torch = ModuleType("torch")
    fake_torch.__spec__ = ModuleSpec("torch", None)
    fake_torch.cuda = SimpleNamespace(is_available=lambda: False)
    fake_torch.backends = SimpleNamespace(
        mps=SimpleNamespace(is_available=lambda: False),
    )

    # Fake PIL Image module
    fake_PIL = ModuleType("PIL")
    fake_PIL.__spec__ = ModuleSpec("PIL", None)
    fake_PIL.Image = SimpleNamespace(open=lambda *args, **kwargs: SimpleNamespace())

    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setitem(
        sys.modules, "transformers.CLIPModel", fake_transformers.CLIPModel,
    )
    monkeypatch.setitem(
        sys.modules, "transformers.CLIPProcessor", fake_transformers.CLIPProcessor,
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "PIL", fake_PIL)

    # Should not raise
    embedder = CLIPEmbedding()
    assert embedder.get_embedding_dimension() == 512
