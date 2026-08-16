from datetime import datetime
import pytest

pytest.importorskip("jinja2")

from lexigram.web.templates import Jinja2Templates


def test_template_filters_and_globals(tmp_path):
    # Create template directory and file
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    tpl_file = tpl_dir / "test.html"
    tpl_file.write_text(
        "json: {{ data|tojson }}\n"
        "time: {{ value|format_datetime }}\n"
        "now: {{ now() }}\n"
        "static: {{ static_url('img.png') }}\n",
    )

    templates = Jinja2Templates(directory=tpl_dir)

    content = templates.render_template(
        "test.html",
        {"data": {"a": 1}, "value": datetime(2020, 1, 1, 12, 0)},
    )

    assert "json:" in content
    assert '"a"' in content or '"a"' in content
    assert "time:" in content
    assert "2020" in content
    assert "now:" in content
    assert "static: /static/img.png" in content
