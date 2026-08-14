"""Tests for lazy loading utilities used by lexigram-admin."""

from lexigram.primitives.lazy import LazyImport


def test_lazy_import_defers_loading():
    """Test that LazyImport doesn't load until first access."""
    lazy_json = LazyImport("json")
    assert lazy_json.is_initialized() is False
    # Access triggers loading
    _ = lazy_json.dumps
    assert lazy_json.is_initialized() is True


def test_lazy_import_works_correctly():
    """Test that LazyImport correctly proxies module access."""
    lazy_json = LazyImport("json")
    result = lazy_json.dumps({"key": "value"})
    assert '"key"' in result
    assert '"value"' in result


def test_lazy_import_repr():
    """Test repr of LazyImport."""
    lazy_os = LazyImport("os")
    assert "not loaded" in repr(lazy_os)
    _ = lazy_os.path
    assert "loaded" in repr(lazy_os)
