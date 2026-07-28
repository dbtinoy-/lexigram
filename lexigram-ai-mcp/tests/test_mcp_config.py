"""Tests for MCP configuration."""

from __future__ import annotations

import pytest

from lexigram.ai.mcp.config import (
    ConnectorsConfig,
    FilesystemConnectorConfig,
    GitHubConnectorConfig,
    GoogleDriveConnectorConfig,
    MCPConfig,
    SlackConnectorConfig,
    SQLConnectorConfig,
    WebFetchConnectorConfig,
    WebSearchConnectorConfig,
)


class TestFilesystemConnectorConfig:
    """Tests for FilesystemConnectorConfig."""

    def test_default_values(self) -> None:
        from lexigram.ai.mcp.config import FilesystemConnectorConfig

        config = FilesystemConnectorConfig()
        assert config.root_dir == ""
        assert config.read_only is False

    def test_custom_values(self) -> None:
        from lexigram.ai.mcp.config import FilesystemConnectorConfig

        config = FilesystemConnectorConfig(root_dir="/data", read_only=True)
        assert config.root_dir == "/data"
        assert config.read_only is True


class TestGitHubConnectorConfig:
    """Tests for GitHubConnectorConfig."""

    def test_default_values(self) -> None:
        from lexigram.ai.mcp.config import GitHubConnectorConfig

        config = GitHubConnectorConfig()
        assert config.token == ""
        assert config.api_url == "https://api.github.com"

    def test_custom_values(self) -> None:
        from lexigram.ai.mcp.config import GitHubConnectorConfig

        config = GitHubConnectorConfig(token="ghp_xxx", api_url="https://github.example.com/api/v3")
        assert config.token == "ghp_xxx"
        assert config.api_url == "https://github.example.com/api/v3"


class TestWebFetchConnectorConfig:
    """Tests for WebFetchConnectorConfig."""

    def test_default_values(self) -> None:
        from lexigram.ai.mcp.config import WebFetchConnectorConfig

        config = WebFetchConnectorConfig()
        assert config.enabled is False
        assert config.max_content_bytes == 512 * 1024
        assert config.user_agent == "lexigram-mcp/1.0"

    def test_custom_values(self) -> None:
        from lexigram.ai.mcp.config import WebFetchConnectorConfig

        config = WebFetchConnectorConfig(enabled=True, max_content_bytes=1024, user_agent="TestAgent/1.0")
        assert config.enabled is True
        assert config.max_content_bytes == 1024
        assert config.user_agent == "TestAgent/1.0"


class TestWebSearchConnectorConfig:
    """Tests for WebSearchConnectorConfig."""

    def test_default_values(self) -> None:
        from lexigram.ai.mcp.config import WebSearchConnectorConfig

        config = WebSearchConnectorConfig()
        assert config.provider == "brave"
        assert config.api_key == ""
        assert config.max_results == 10

    def test_custom_values(self) -> None:
        from lexigram.ai.mcp.config import WebSearchConnectorConfig

        config = WebSearchConnectorConfig(provider="google", api_key="key123", max_results=20)
        assert config.provider == "google"
        assert config.api_key == "key123"
        assert config.max_results == 20


class TestSlackConnectorConfig:
    """Tests for SlackConnectorConfig."""

    def test_default_values(self) -> None:
        from lexigram.ai.mcp.config import SlackConnectorConfig

        config = SlackConnectorConfig()
        assert config.bot_token == ""
        assert config.max_messages == 100

    def test_custom_values(self) -> None:
        from lexigram.ai.mcp.config import SlackConnectorConfig

        config = SlackConnectorConfig(bot_token="xoxb-xxx", max_messages=50)
        assert config.bot_token == "xoxb-xxx"
        assert config.max_messages == 50


class TestGoogleDriveConnectorConfig:
    """Tests for GoogleDriveConnectorConfig."""

    def test_default_values(self) -> None:
        from lexigram.ai.mcp.config import GoogleDriveConnectorConfig

        config = GoogleDriveConnectorConfig()
        assert config.service_account_json == ""
        assert config.impersonated_email == ""

    def test_custom_values(self) -> None:
        from lexigram.ai.mcp.config import GoogleDriveConnectorConfig

        config = GoogleDriveConnectorConfig(
            service_account_json="/path/to/creds.json",
            impersonated_email="user@example.com",
        )
        assert config.service_account_json == "/path/to/creds.json"
        assert config.impersonated_email == "user@example.com"


class TestSQLConnectorConfig:
    """Tests for SQLConnectorConfig."""

    def test_default_values(self) -> None:
        from lexigram.ai.mcp.config import SQLConnectorConfig

        config = SQLConnectorConfig()
        assert config.dsn == ""
        assert config.allowed_tables == []
        assert config.read_only is True

    def test_custom_values(self) -> None:
        from lexigram.ai.mcp.config import SQLConnectorConfig

        config = SQLConnectorConfig(
            dsn="postgresql://user:pass@localhost/db",
            allowed_tables=["users", "orders"],
            read_only=False,
        )
        assert config.dsn == "postgresql://user:pass@localhost/db"
        assert config.allowed_tables == ["users", "orders"]
        assert config.read_only is False


class TestConnectorsConfig:
    """Tests for ConnectorsConfig."""

    def test_default_values(self) -> None:
        from lexigram.ai.mcp.config import ConnectorsConfig

        config = ConnectorsConfig()
        assert isinstance(config.filesystem, FilesystemConnectorConfig)
        assert isinstance(config.github, GitHubConnectorConfig)
        assert isinstance(config.web_fetch, WebFetchConnectorConfig)

    def test_custom_values(self) -> None:
        from lexigram.ai.mcp.config import ConnectorsConfig, FilesystemConnectorConfig

        config = ConnectorsConfig(filesystem=FilesystemConnectorConfig(root_dir="/data"))
        assert config.filesystem.root_dir == "/data"


class TestMCPConfig:
    """Tests for MCPConfig."""

    def test_default_values(self) -> None:
        from lexigram.ai.mcp.config import MCPConfig

        config = MCPConfig()
        assert config.enabled is True
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.path == "/mcp"
        assert config.enable_sse is True
        assert config.stdio_mode is False
        assert config.server_name == "lexigram-mcp"
        assert config.server_version == "1.0.0"
        assert config.cors_origins == []
        assert config.max_request_size == 1024 * 1024
        assert config.request_timeout == 30.0

    def test_custom_values(self) -> None:
        from lexigram.ai.mcp.config import MCPConfig

        config = MCPConfig(
            enabled=False,
            host="127.0.0.1",
            port=9000,
            path="/custom-mcp",
            enable_sse=False,
            stdio_mode=True,
            server_name="custom-server",
            server_version="2.0.0",
            cors_origins=["https://example.com"],
            max_request_size=2 * 1024 * 1024,
            request_timeout=60.0,
        )
        assert config.enabled is False
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.path == "/custom-mcp"
        assert config.enable_sse is False
        assert config.stdio_mode is True
        assert config.server_name == "custom-server"
        assert config.server_version == "2.0.0"
        assert config.cors_origins == ["https://example.com"]
        assert config.max_request_size == 2 * 1024 * 1024
        assert config.request_timeout == 60.0

    def test_client_configuration(self) -> None:
        from lexigram.ai.mcp.config import MCPConfig

        config = MCPConfig(client_url="http://localhost:8080/mcp")
        assert config.client_url == "http://localhost:8080/mcp"

    def test_stdio_command_configuration(self) -> None:
        from lexigram.ai.mcp.config import MCPConfig

        config = MCPConfig(client_stdio_command=["python", "server.py"])
        assert config.client_stdio_command == ["python", "server.py"]

    def test_connectors_nested_config(self) -> None:
        from lexigram.ai.mcp.config import MCPConfig, ConnectorsConfig, FilesystemConnectorConfig

        config = MCPConfig(connectors=ConnectorsConfig(filesystem=FilesystemConnectorConfig(root_dir="/tmp")))
        assert config.connectors.filesystem.root_dir == "/tmp"