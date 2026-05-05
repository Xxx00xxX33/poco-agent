from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChannelArtifactResponse(BaseModel):
    artifact_id: UUID = Field(validation_alias="id")
    server_id: UUID
    channel_id: UUID
    source_session_id: UUID
    agent_identity_id: UUID | None = None
    publisher_user_id: str | None = None
    source_kind: str
    logical_path: str
    display_name: str
    object_key: str
    mime_type: str | None = None
    size_bytes: int | None = None
    is_previewable: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
