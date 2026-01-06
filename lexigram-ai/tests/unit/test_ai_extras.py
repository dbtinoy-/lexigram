from pathlib import Path
import tomllib


def _load_pyproject(path: Path):
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_ai_extra_declared():
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = _load_pyproject(pyproject)
    extras = data.get("project", {}).get("optional-dependencies", {})

    assert "ai" in extras, "Expected 'ai' extra in pyproject.toml"
    ai = extras["ai"]
    assert any("tiktoken" in pkg for pkg in ai), "tiktoken should be in 'ai' extras"
    assert any("chromadb" in pkg for pkg in ai), "chromadb should be in 'ai' extras"
