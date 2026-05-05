import uuid
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.channel_artifact_repository import ChannelArtifactRepository
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.services.storage_service import S3StorageService


class ChannelSharedContextService:
    MAX_RECENT_MESSAGES = 8
    MAX_ARTIFACTS = 4
    MAX_TEXT_ARTIFACT_BYTES = 64 * 1024
    TEXT_EXTENSIONS = {
        ".md",
        ".txt",
        ".json",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
    }

    def __init__(self) -> None:
        self._storage = S3StorageService()

    @staticmethod
    def _message_text(message: Any) -> str:
        text_preview = getattr(message, "text_preview", None)
        if isinstance(text_preview, str) and text_preview.strip():
            return text_preview.strip()
        content = getattr(message, "content", None)
        if isinstance(content, dict):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
            title = content.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
        return ""

    @staticmethod
    def _message_author_label(message: Any) -> str:
        author_user = getattr(message, "author_user", None)
        if author_user is not None:
            display_name = getattr(author_user, "display_name", None)
            if isinstance(display_name, str) and display_name.strip():
                return display_name.strip()
            user_id = getattr(author_user, "user_id", None)
            if isinstance(user_id, str) and user_id.strip():
                return user_id.strip()
        author_user_id = getattr(message, "author_user_id", None)
        if isinstance(author_user_id, str) and author_user_id.strip():
            return author_user_id.strip()
        return "Unknown"

    @classmethod
    def _is_text_artifact(cls, artifact: Any) -> bool:
        mime_type = getattr(artifact, "mime_type", None)
        if isinstance(mime_type, str) and mime_type.startswith("text/"):
            return True
        suffix = PurePosixPath(getattr(artifact, "logical_path", "")).suffix.lower()
        return suffix in cls.TEXT_EXTENSIONS

    def _artifact_block(self, artifact: Any) -> str:
        lines = [
            f"- {getattr(artifact, 'display_name', 'artifact')} ({getattr(artifact, 'logical_path', '')})"
        ]
        size_bytes = getattr(artifact, "size_bytes", None)
        if isinstance(size_bytes, int) and size_bytes > self.MAX_TEXT_ARTIFACT_BYTES:
            lines.append("  [metadata only: file too large to inline]")
            return "\n".join(lines)
        if not self._is_text_artifact(artifact):
            lines.append("  [metadata only: binary or unsupported preview type]")
            return "\n".join(lines)
        try:
            content = self._storage.get_text(getattr(artifact, "object_key"))
        except Exception:
            lines.append("  [metadata only: failed to load file content]")
            return "\n".join(lines)
        trimmed = content.strip()
        if not trimmed:
            lines.append("  [empty file]")
            return "\n".join(lines)
        lines.append("  -----")
        lines.append(trimmed[: self.MAX_TEXT_ARTIFACT_BYTES])
        return "\n".join(lines)

    def build_message_trigger_prompt(
        self,
        db: Session,
        *,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        message: Any,
        current_user: Any,
        agent_display_name: str,
    ) -> str:
        del server_id
        recent_messages = ServerChannelMessageRepository.list_by_channel(
            db,
            channel_id,
            limit=self.MAX_RECENT_MESSAGES,
        )
        recent_messages = list(reversed(recent_messages))
        artifacts = ChannelArtifactRepository.list_by_channel(db, channel_id=channel_id)[
            : self.MAX_ARTIFACTS
        ]

        actor_label = getattr(current_user, "display_name", None) or getattr(
            current_user, "primary_email", None
        ) or getattr(current_user, "id", "User")
        trigger_text = self._message_text(message)
        thread_root_id = getattr(message, "thread_root_message_id", None) or getattr(
            message, "id", None
        )

        lines = [
            f"You are {agent_display_name}.",
            f"{actor_label} triggered you from a server conversation.",
            f"Channel ID: {channel_id}",
            f"Trigger message ID: {getattr(message, 'id', '')}",
            f"Thread root message ID: {thread_root_id}",
            "",
            "Trigger message:",
            trigger_text or "[no visible trigger text]",
            "",
            "Recent conversation context:",
        ]

        if recent_messages:
            for recent in recent_messages:
                text = self._message_text(recent)
                if not text:
                    continue
                lines.append(f"- {self._message_author_label(recent)}: {text}")
        else:
            lines.append("- [no recent visible messages]")

        lines.append("")
        lines.append("Published channel artifacts you can read:")
        if artifacts:
            for artifact in artifacts:
                lines.append(self._artifact_block(artifact))
        else:
            lines.append("- [no published artifacts yet]")

        lines.append("")
        lines.append(
            "Act on the trigger message and the shared channel context above. Do not assume access to private agent state or raw local mount paths unless they appear in the published artifacts section."
        )
        return "\n".join(lines)
