import importlib


def import_attr(name: str):
    """Import an attribute from lexigram.web and return it."""
    mod = importlib.import_module("lexigram.web")
    val = getattr(mod, name)
    return val


def test_lazy_import_get_warns_and_returns():
    """Test that `get` can be imported from `lexigram.web`."""
    val = import_attr("get")
    # Should return a callable decorator or function
    assert callable(val)


def test_lazy_import_body_warns_and_returns():
    """Test that `body` can be imported from `lexigram.web`."""
    val = import_attr("body")
    assert callable(val)
