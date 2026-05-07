import json
from typing import Any

import httpx
from claude_agent_sdk import create_sdk_mcp_server, tool
from claude_agent_sdk.types import McpSdkServerConfig

from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_trace_id,
)

CHANNEL_ARTIFACTS_MCP_SERVER_KEY = "__poco_channel_artifacts"


class ChannelArtifactClient:
    def __init__(self, base_url: str, session_id: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_id = session_id
        self.timeout = timeout

    @staticmethod
    def _trace_headers() -> dict[str, str]:
        return {
            "X-Request-ID": get_request_id() or generate_request_id(),
            "X-Trace-ID": get_trace_id() or generate_trace_id(),
        }

    async def _request(self, path: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json={"session_id": self.session_id, **payload},
                headers=self._trace_headers(),
            )
            response.raise_for_status()

        body = response.json()
        if not isinstance(body, dict):
            raise RuntimeError("Invalid channel artifact response")
        if body.get("code") != 0:
            raise RuntimeError(str(body.get("message") or "Channel artifact error"))
        return body.get("data")

    async def list_artifacts(self) -> Any:
        return await self._request("/api/v1/agent-channel-artifacts/list", {})

    async def read_artifact(
        self,
        *,
        artifact_id: str | None,
        logical_path: str | None,
        max_bytes: int | None,
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-artifacts/read",
            {
                "artifact_id": artifact_id,
                "logical_path": logical_path,
                "max_bytes": max_bytes,
            },
        )

    async def search_artifacts(
        self,
        *,
        query: str,
        limit: int | None,
        include_content: bool,
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-artifacts/search",
            {
                "query": query,
                "limit": limit,
                "include_content": include_content,
            },
        )


def _format_tool_result(title: str, data: Any) -> dict[str, Any]:
    body = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    return {"content": [{"type": "text", "text": f"{title}\n{body}"}]}


async def _run_tool(title: str, operation) -> dict[str, Any]:
    try:
        result = await operation
    except Exception as exc:
        return _format_tool_result(f"{title}_error", {"error": str(exc)})
    return _format_tool_result(title, result)


def create_channel_artifacts_mcp_server(
    artifact_client: ChannelArtifactClient,
) -> McpSdkServerConfig:
    @tool(
        "list_channel_artifacts",
        "List read-only published artifacts available in the current channel",
        {},
    )
    async def list_channel_artifacts(args: dict[str, Any]) -> dict[str, Any]:
        _ = args
        return await _run_tool(
            "list_channel_artifacts",
            artifact_client.list_artifacts(),
        )

    @tool(
        "read_channel_artifact",
        "Read one published channel artifact by artifact_id or logical_path",
        {"artifact_id": str, "logical_path": str, "max_bytes": int},
    )
    async def read_channel_artifact(args: dict[str, Any]) -> dict[str, Any]:
        artifact_id = args.get("artifact_id")
        logical_path = args.get("logical_path")
        if (
            not isinstance(artifact_id, str)
            or not artifact_id.strip()
        ) and (
            not isinstance(logical_path, str)
            or not logical_path.strip()
        ):
            return _format_tool_result(
                "read_channel_artifact_error",
                {"error": "artifact_id or logical_path must be provided"},
            )
        if isinstance(logical_path, str) and logical_path.strip().startswith(
            "/workspace"
        ):
            return _format_tool_result(
                "read_channel_artifact_error",
                {
                    "error": (
                        "logical_path is a published artifact identifier, "
                        "not a /workspace path"
                    )
                },
            )
        max_bytes = args.get("max_bytes")
        return await _run_tool(
            "read_channel_artifact",
            artifact_client.read_artifact(
                artifact_id=artifact_id.strip() if isinstance(artifact_id, str) else None,
                logical_path=(
                    logical_path.strip() if isinstance(logical_path, str) else None
                ),
                max_bytes=max_bytes if isinstance(max_bytes, int) else None,
            ),
        )

    @tool(
        "search_channel_artifacts",
        "Search current channel artifacts by name, logical path, source, or text",
        {"query": str, "limit": int, "include_content": bool},
    )
    async def search_channel_artifacts(args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return _format_tool_result(
                "search_channel_artifacts_error",
                {"error": "query must be a non-empty string"},
            )
        limit = args.get("limit")
        include_content = args.get("include_content")
        return await _run_tool(
            "search_channel_artifacts",
            artifact_client.search_artifacts(
                query=query.strip(),
                limit=limit if isinstance(limit, int) else None,
                include_content=(
                    include_content if isinstance(include_content, bool) else False
                ),
            ),
        )

    return create_sdk_mcp_server(
        name="poco-channel-artifacts",
        version="0.1.0",
        tools=[
            list_channel_artifacts,
            read_channel_artifact,
            search_channel_artifacts,
        ],
    )
