import uuid
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_session import AgentSession
from app.models.channel_artifact import ChannelArtifact
from app.models.user import User
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.channel_artifact_repository import ChannelArtifactRepository
from app.schemas.workspace import FileNode
from app.services.server_member_service import require_server_member
from app.services.storage_service import S3StorageService
from app.utils.workspace import build_workspace_file_nodes
from app.utils.workspace_manifest import (
    build_nodes_from_file_entries,
    extract_manifest_files,
    normalize_manifest_path,
)


class ChannelArtifactService:
    def __init__(self) -> None:
        self._storage = S3StorageService()

    @staticmethod
    def _parse_scope_ids(
        db_session: AgentSession,
    ) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID | None] | None:
        config_snapshot = db_session.config_snapshot or {}
        server_id_raw = str(config_snapshot.get("server_id") or "").strip()
        channel_id_raw = str(config_snapshot.get("channel_id") or "").strip()
        agent_identity_id_raw = str(config_snapshot.get("agent_identity_id") or "").strip()
        if not server_id_raw or not channel_id_raw:
            return None
        server_id = uuid.UUID(server_id_raw)
        channel_id = uuid.UUID(channel_id_raw)
        agent_identity_id = (
            uuid.UUID(agent_identity_id_raw) if agent_identity_id_raw else None
        )
        return server_id, channel_id, agent_identity_id

    @staticmethod
    def _resolve_object_key(
        file_entry: dict[str, Any],
        *,
        workspace_files_prefix: str,
    ) -> str | None:
        object_key = (
            file_entry.get("key")
            or file_entry.get("object_key")
            or file_entry.get("oss_key")
            or file_entry.get("s3_key")
        )
        if object_key:
            return str(object_key)
        normalized_path = normalize_manifest_path(file_entry.get("path"))
        if not normalized_path:
            return None
        prefix = workspace_files_prefix.rstrip("/")
        if not prefix:
            return None
        return f"{prefix}/{normalized_path.lstrip('/')}"

    @staticmethod
    def _is_publishable_path(path: str) -> bool:
        normalized = normalize_manifest_path(path)
        if not normalized:
            return False
        return not (
            normalized.startswith("/agent_state/")
            or normalized.startswith("/.poco-local/")
        )

    def sync_session_workspace_artifacts(
        self,
        db: Session,
        db_session: AgentSession,
    ) -> int:
        if (db_session.workspace_export_status or "").strip().lower() != "ready":
            return 0
        if not db_session.workspace_manifest_key or not db_session.workspace_files_prefix:
            return 0

        scope = self._parse_scope_ids(db_session)
        if scope is None:
            return 0
        server_id, channel_id, agent_identity_id = scope

        manifest = self._storage.get_manifest(db_session.workspace_manifest_key)
        artifacts: list[ChannelArtifact] = []
        for file_entry in extract_manifest_files(manifest):
            normalized_path = normalize_manifest_path(file_entry.get("path"))
            if not normalized_path or not self._is_publishable_path(normalized_path):
                continue
            object_key = self._resolve_object_key(
                file_entry,
                workspace_files_prefix=db_session.workspace_files_prefix,
            )
            if not object_key:
                continue
            artifacts.append(
                ChannelArtifact(
                    server_id=server_id,
                    channel_id=channel_id,
                    source_session_id=db_session.id,
                    agent_identity_id=agent_identity_id,
                    publisher_user_id=db_session.user_id,
                    source_kind="workspace_export",
                    logical_path=normalized_path,
                    display_name=PurePosixPath(normalized_path).name,
                    object_key=object_key,
                    mime_type=file_entry.get("mimeType") or file_entry.get("mime_type"),
                    size_bytes=file_entry.get("size"),
                    is_previewable=True,
                )
            )

        ChannelArtifactRepository.upsert_many(db, artifacts=artifacts)
        return len(artifacts)

    def list_channel_artifact_nodes(
        self,
        db: Session,
        *,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> list[FileNode]:
        require_server_member(db, server_id, current_user.id)
        artifacts = ChannelArtifactRepository.list_by_channel(
            db,
            channel_id=channel_id,
        )

        grouped_entries: dict[str, dict[str, Any]] = {}
        for artifact in artifacts:
            if artifact.agent_identity_id is not None:
                group_key = f"agent:{artifact.agent_identity_id}"
                agent = AgentIdentityRepository.get_by_id(db, artifact.agent_identity_id)
                group_name = (
                    agent.display_name
                    if agent is not None and agent.display_name
                    else str(artifact.agent_identity_id)
                )
            else:
                publisher_label = artifact.publisher_user_id or "shared"
                group_key = f"user:{publisher_label}"
                group_name = publisher_label

            group = grouped_entries.setdefault(
                group_key,
                {"name": group_name, "files": [], "url_map": {}},
            )
            relative_path = artifact.logical_path.lstrip("/")
            group["files"].append(
                {
                    "path": relative_path,
                    "key": artifact.object_key,
                    "mimeType": artifact.mime_type,
                    "size": getattr(artifact, "size_bytes", None),
                }
            )
            group["url_map"][normalize_manifest_path(artifact.logical_path)] = (
                self._storage.presign_get(
                    artifact.object_key,
                    response_content_disposition="inline",
                    response_content_type=artifact.mime_type,
                )
            )

        roots: list[FileNode] = []
        for group_key, group in grouped_entries.items():
            raw_nodes = build_nodes_from_file_entries(group["files"])
            nodes = build_workspace_file_nodes(
                raw_nodes,
                file_url_builder=lambda file_path, url_map=group["url_map"]: url_map.get(
                    normalize_manifest_path(file_path) or file_path
                ),
            )
            roots.append(
                FileNode(
                    id=f"group/{group_key}",
                    name=str(group["name"]),
                    type="folder",
                    path=f"group/{group_key}",
                    children=nodes,
                )
            )
        return roots
