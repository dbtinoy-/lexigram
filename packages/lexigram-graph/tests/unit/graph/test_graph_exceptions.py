"""Tests for graph exceptions."""

from __future__ import annotations

import pytest

from lexigram.graph import exceptions as exc


class TestGraphError:
    """Tests for GraphError."""

    def test_graph_error_code(self) -> None:
        """Verify error has correct code."""
        error = exc.GraphError("test error")
        assert error._code == "LEX_ERR_GRAPH_001"

    def test_graph_error_message(self) -> None:
        """Verify error message is set."""
        error = exc.GraphError("test error")
        assert "test error" in str(error)


class TestGraphConnectionError:
    """Tests for GraphConnectionError."""

    def test_connection_error_code(self) -> None:
        """Verify error has correct code."""
        error = exc.GraphConnectionError("connection failed")
        assert error._code == "LEX_ERR_GRAPH_002"


class TestGraphNotFoundError:
    """Tests for GraphNotFoundError."""

    def test_not_found_error(self) -> None:
        """Verify error captures graph name."""
        error = exc.GraphNotFoundError("my_graph")
        assert error.graph_name == "my_graph"
        assert "my_graph" in str(error)
        assert error._code == "LEX_ERR_GRAPH_003"


class TestGraphAlreadyExistsError:
    """Tests for GraphAlreadyExistsError."""

    def test_already_exists_error(self) -> None:
        """Verify error captures graph name."""
        error = exc.GraphAlreadyExistsError("my_graph")
        assert error.graph_name == "my_graph"
        assert "my_graph" in str(error)
        assert error._code == "LEX_ERR_GRAPH_004"


class TestGraphNodeNotFoundError:
    """Tests for GraphNodeNotFoundError."""

    def test_node_not_found_error(self) -> None:
        """Verify error captures node id."""
        error = exc.GraphNodeNotFoundError("node-123")
        assert error.node_id == "node-123"
        assert "node-123" in str(error)
        assert error._code == "LEX_ERR_GRAPH_005"


class TestGraphEdgeNotFoundError:
    """Tests for GraphEdgeNotFoundError."""

    def test_edge_not_found_error(self) -> None:
        """Verify error captures edge id."""
        error = exc.GraphEdgeNotFoundError("edge-456")
        assert error.edge_id == "edge-456"
        assert "edge-456" in str(error)
        assert error._code == "LEX_ERR_GRAPH_006"


class TestDetachRequiredError:
    """Tests for DetachRequiredError."""

    def test_detach_required_error(self) -> None:
        """Verify error captures node and edge count."""
        error = exc.DetachRequiredError("node-789", 5)
        assert error.node_id == "node-789"
        assert error.edge_count == 5
        assert "node-789" in str(error)
        assert "5" in str(error)
        assert error._code == "LEX_ERR_GRAPH_007"


class TestTraversalError:
    """Tests for TraversalError."""

    def test_traversal_error_code(self) -> None:
        """Verify error has correct code."""
        error = exc.TraversalError("traversal failed")
        assert error._code == "LEX_ERR_GRAPH_008"


class TestCypherCompilationError:
    """Tests for CypherCompilationError."""

    def test_cypher_error_message(self) -> None:
        """Verify error wraps Cypher error."""
        error = exc.CypherCompilationError("invalid syntax")
        assert "invalid syntax" in str(error)
        assert error._code == "LEX_ERR_GRAPH_009"


class TestGraphSchemaError:
    """Tests for GraphSchemaError."""

    def test_schema_error_code(self) -> None:
        """Verify error has correct code."""
        error = exc.GraphSchemaError("schema error")
        assert error._code == "LEX_ERR_GRAPH_010"


class TestGraphTransactionError:
    """Tests for GraphTransactionError."""

    def test_transaction_error_code(self) -> None:
        """Verify error has correct code."""
        error = exc.GraphTransactionError("transaction failed")
        assert error._code == "LEX_ERR_GRAPH_011"


class TestGraphQueryError:
    """Tests for GraphQueryError."""

    def test_query_error_code(self) -> None:
        """Verify error has correct code."""
        error = exc.GraphQueryError("query failed")
        assert error._code == "LEX_ERR_GRAPH_012"