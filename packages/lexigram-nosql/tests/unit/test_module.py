from __future__ import annotations

from lexigram.contracts.data.nosql.nosql import DocumentStoreProtocol
from lexigram.di.module import DynamicModule
from lexigram.nosql.module import NoSQLModule


def test_nosql_module_has_configure() -> None:
    assert hasattr(NoSQLModule, "configure")
    assert callable(NoSQLModule.configure)


def test_nosql_module_configure_returns_dynamic_module() -> None:
    result = NoSQLModule.configure()
    assert isinstance(result, DynamicModule)


def test_nosql_module_configure_exports_document_store_protocol() -> None:
    module = NoSQLModule.configure()
    assert DocumentStoreProtocol in module.exports
