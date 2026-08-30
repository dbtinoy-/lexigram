from __future__ import annotations

from lexigram.admin.schema import SchemaField
from lexigram.admin.schema.belongs_to_many import BelongsToManyField
from lexigram.admin.ui.fields.pivot_data import PivotColumn, PivotDataField, PivotTable
from lexigram.result import Ok
from lexigram.ui import Element


class TestPivotColumn:
    def test_construct_with_minimum_args(self) -> None:
        col = PivotColumn(name="role", label="Role")
        assert col.name == "role"
        assert col.label == "Role"
        assert col.field_type == "text"

    def test_construct_with_all_args(self) -> None:
        col = PivotColumn(
            name="is_primary",
            label="Primary",
            field_type="checkbox",
            required=True,
            default="true",
        )
        assert col.field_type == "checkbox"
        assert col.required is True


class TestPivotDataField:
    def test_construct(self) -> None:
        field = PivotDataField(name="pivot_data")
        assert field.name == "pivot_data"
        assert field.pivot_columns == []

    def test_construct_with_columns(self) -> None:
        field = PivotDataField(
            name="pivot_data",
            pivot_columns=[
                PivotColumn(name="role", label="Role"),
            ],
        )
        assert len(field.pivot_columns) == 1

    def test_render_form_returns_element(self) -> None:
        field = PivotDataField(name="pivot_data")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_form_with_pivot_columns(self) -> None:
        field = PivotDataField(
            name="pivot_data",
            pivot_columns=[
                PivotColumn(name="role", label="Role"),
                PivotColumn(name="is_primary", label="Primary", field_type="checkbox"),
            ],
        )
        element = field.render_form({"role": "admin"})
        assert isinstance(element, Element)

    def test_render_column_with_values(self) -> None:
        field = PivotDataField(name="pivot_data")
        element = field.render_column(None, {"role": "admin", "is_primary": "true"})
        output = str(element)
        assert "role" in output
        assert "admin" in output

    def test_render_column_with_none(self) -> None:
        field = PivotDataField(name="pivot_data")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_with_dict(self) -> None:
        field = PivotDataField(name="pivot_data")
        result = field.from_form({"role": "admin"})
        assert isinstance(result, Ok)
        assert result.unwrap() == {"role": "admin"}

    def test_from_form_with_none(self) -> None:
        field = PivotDataField(name="pivot_data")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None


class TestBelongsToManyField:
    def test_construct(self) -> None:
        field = BelongsToManyField(name="roles")
        assert field.name == "roles"

    def test_render_form_returns_element(self) -> None:
        field = BelongsToManyField(name="roles")
        element = field.render_form(["1", "2"])
        assert isinstance(element, Element)

    def test_render_form_with_none(self) -> None:
        field = BelongsToManyField(name="roles")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_form_with_label(self) -> None:
        field = BelongsToManyField(name="roles", label="Roles")
        element = field.render_form(None)
        output = str(element)
        assert "Roles" in output

    def test_render_column_with_values(self) -> None:
        field = BelongsToManyField(name="roles")
        element = field.render_column(None, ["1", "2", "3"])
        output = str(element)
        assert "3" in output
        assert "relations" in output

    def test_render_column_with_none(self) -> None:
        field = BelongsToManyField(name="roles")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_render_column_empty_list(self) -> None:
        field = BelongsToManyField(name="roles")
        element = field.render_column(None, [])
        output = str(element)
        assert "\u2014" in output

    def test_from_form_valid_json(self) -> None:
        field = BelongsToManyField(name="roles")
        result = field.from_form('["1","2","3"]')
        assert isinstance(result, Ok)
        assert result.unwrap() == ["1", "2", "3"]

    def test_from_form_invalid_json_returns_err(self) -> None:
        field = BelongsToManyField(name="roles")
        from lexigram.admin.schema import FieldError
        from lexigram.result import Err

        result = field.from_form("not json")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_none_returns_ok_none(self) -> None:
        field = BelongsToManyField(name="roles")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_to_form_with_list(self) -> None:
        field = BelongsToManyField(name="roles")
        result = field.to_form(["1", "2"])
        import json
        assert json.loads(result) == ["1", "2"]

    def test_to_form_with_none(self) -> None:
        field = BelongsToManyField(name="roles")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = BelongsToManyField(name="roles")
        assert isinstance(field, SchemaField)


class TestPivotTable:
    def test_construct(self) -> None:
        table = PivotTable(pivot_columns=[], rows=[])
        assert table.pivot_columns == []

    def test_render_with_rows(self) -> None:
        table = PivotTable(
            pivot_columns=[
                PivotColumn(name="role", label="Role"),
            ],
            rows=[
                {"id": "1", "label": "Admin", "pivot": {"role": "manager"}},
            ],
        )
        html = table.render(resource_name="users", parent_id="p1")
        assert "Admin" in html
        assert "manager" in html

    def test_render_empty_rows(self) -> None:
        table = PivotTable(pivot_columns=[], rows=[])
        html = table.render()
        assert "<table" in html
        assert "<tbody" in html


class TestPivotInputEscaping:
    """Pivot inputs are built as raw HTML strings — dynamic values must be
    escaped before they cross into attribute/text context."""

    def _render(self, value: str, field_type: str = "text") -> str:
        field = PivotDataField(
            name="pivot_data",
            pivot_columns=[PivotColumn(name="role", label="Role", field_type=field_type)],
        )
        element = field.render_form({"role": value})
        return str(element)

    def test_quotes_escaped_in_text_input_value(self) -> None:
        html = self._render('x" onfocus="alert(1)')
        assert 'value="x&#34; onfocus=&#34;alert(1)' in html or 'value="x&quot;' in html
        assert 'onfocus="alert(1)' not in html

    def test_tags_escaped_in_text_input_value(self) -> None:
        html = self._render("<script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_option_text_escaped_in_select(self) -> None:
        html = self._render("<b>admin</b>", field_type="select")
        assert "<b>admin</b>" not in html
        assert "&lt;b&gt;admin&lt;/b&gt;" in html

    def test_field_type_escaped_in_attribute(self) -> None:
        field = PivotDataField(
            name="pivot_data",
            pivot_columns=[PivotColumn(name="role", label="Role", field_type='text" autofocus onfocus="x')],
        )
        html = str(field.render_form({"role": "v"}))
        # The injected quotes are escaped, so no attribute breakout is possible
        assert 'onfocus="x"' not in html
        assert "&quot;" in html
        # The field type string remains inside the quoted attribute value
        assert 'type="text&quot; autofocus onfocus=&quot;x"' in html
