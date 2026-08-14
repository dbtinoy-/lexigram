from lexigram.admin.config import TableConfiguration
from lexigram.admin.resources.base import Resource


class TableTester:
    """
    Utility to test Admin Resource configurations.

    Usage:
        tester = TableTester(MyResource)
        tester.assert_columns(["id", "name"])
    """

    def __init__(self, resource_cls: type[Resource]):
        self.resource_cls = resource_cls
        self.config: TableConfiguration = resource_cls.get_table_config()

    def assert_columns(self, names: list[str], strict: bool = False):
        """
        Assert that the table has the specific columns.

        Args:
            names: List of column names to expect.
            strict: If True, asserts exact match (order and length).
                    If False (default), asserts that expected names are present.
        """
        actual_names = [col.name for col in self.config.columns]

        if strict:
            assert actual_names == names, (
                f"Strict mismatch.\\nExpected: {names}\\nActual:   {actual_names}"
            )
        else:
            missing = list(filter(lambda name: name not in actual_names, names))
            assert not missing, f"Missing columns: {missing}. Available: {actual_names}"

    def assert_actions(self, names: list[str]):
        """Assert that the table has the specific actions."""
        actual_names = [action.name for action in self.config.actions]
        missing = list(filter(lambda name: name not in actual_names, names))
        assert not missing, f"Missing actions: {missing}. Available: {actual_names}"

    def assert_bulk_actions(self, names: list[str]):
        """Assert that the table has the specific bulk actions."""
        actual_names = [action.name for action in self.config.bulk_actions]
        missing = list(filter(lambda name: name not in actual_names, names))
        assert not missing, (
            f"Missing bulk actions: {missing}. Available: {actual_names}"
        )

    def assert_filter_exists(self, name: str):
        """Assert a filter with the given name exists."""
        # Config has generated list of filter objects via config.filters property
        filters = self.config.filters
        actual_names = [f.name for f in filter(lambda f: hasattr(f, "name"), filters)]
        assert name in actual_names, (
            f"Filter '{name}' not found. Available: {actual_names}"
        )


__all__ = ["TableTester"]
