"""Mock MCP adapters for demo purposes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol


@dataclass
class MCPResource:
    resource_id: str
    title: str
    source_url: str
    status: str = "pending_verification"
    content: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


class MCPAdapter(Protocol):
    name: str

    def search(self, query: str, limit: int = 5) -> list[MCPResource]:
        ...


class MockLegalRegistryAdapter:
    """Mock external law-registry resource connector.

    It never returns fabricated citations. In real deployments this adapter
    would authenticate against an approved provider and return checked
    resources that still enter the knowledge-base pipeline.
    """

    name = "mock_legal_registry"

    def __init__(self) -> None:
        self.tool_calls: list[dict[str, object]] = []

    def search(self, query: str, limit: int = 5) -> list[MCPResource]:
        self._log("search_external_registry", query, 0)
        return []

    def list_resources(self) -> list[MCPResource]:
        self._log("list_resources", "", 3)
        return [
            MCPResource(
                resource_id="MOCK-EXT-001",
                title="DEMO external contract-law resource",
                source_url="https://example.invalid/mock-external",
                status="pending_verification",
                metadata={"jurisdiction": "中国大陆", "source_type": "external_registry"},
            ),
            MCPResource(
                resource_id="MOCK-EXT-002",
                title="DEMO external labor-law resource",
                source_url="https://example.invalid/mock-external",
                status="pending_verification",
                metadata={"jurisdiction": "中国大陆", "source_type": "external_registry"},
            ),
            MCPResource(
                resource_id="MOCK-EXT-003",
                title="DEMO external data-compliance resource",
                source_url="https://example.invalid/mock-external",
                status="pending_verification",
                metadata={"jurisdiction": "中国大陆", "source_type": "external_registry"},
            ),
        ]

    def search_external_registry(
        self,
        query: str,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[MCPResource]:
        self._log(
            "search_external_registry",
            query,
            0,
            detail=f"metadata_filter={metadata_filter or {}}; mock adapter 不注入外部结果",
        )
        return []

    def get_legal_update(self, resource_id: str) -> MCPResource:
        self._log("get_legal_update", resource_id, 1)
        return MCPResource(
            resource_id=resource_id,
            title=f"DEMO update notice for {resource_id}",
            source_url="https://example.invalid/mock-external",
            status="pending_verification",
            content="MOCK update notice; 未经验证，不进入知识库。",
        )

    def sync_verified_resource(self, resource_id: str) -> MCPResource:
        self._log("sync_verified_resource", resource_id, 1)
        return MCPResource(
            resource_id=resource_id,
            title=f"Mock sync placeholder for {resource_id}",
            source_url="https://example.invalid/mock-external",
            status="mock_synced_not_verified",
            content="MOCK sync placeholder; 仅供接口演示，不代表真实法规同步。",
        )

    def get_tool_call_log(self) -> list[dict[str, object]]:
        return list(self.tool_calls)

    def _log(
        self,
        tool: str,
        query: str,
        result_count: int,
        detail: str = "",
    ) -> None:
        self.tool_calls.append(
            {
                "tool": tool,
                "query": query[:120],
                "result_count": result_count,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "detail": detail,
                "mock": True,
            }
        )


class RegistryHub:
    def __init__(self, adapters: list[MCPAdapter] | None = None) -> None:
        self.adapters: list[MCPAdapter] = adapters or [MockLegalRegistryAdapter()]

    def names(self) -> list[str]:
        return [adapter.name for adapter in self.adapters]

    def search_all(self, query: str) -> list[MCPResource]:
        resources: list[MCPResource] = []
        for adapter in self.adapters:
            if hasattr(adapter, "search_external_registry"):
                resources.extend(adapter.search_external_registry(query))
            else:
                resources.extend(adapter.search(query))
        return resources
