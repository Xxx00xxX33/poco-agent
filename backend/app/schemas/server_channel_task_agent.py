from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.server_channel_task import (
    ServerChannelTaskClaimRequest,
    ServerChannelTaskCreateRequest,
    ServerChannelTaskResponse,
    ServerChannelTaskStatusUpdateRequest,
)


class AgentChannelTaskContext(BaseModel):
    session_id: UUID
    user_id: str
    server_id: UUID
    channel_id: UUID
    agent_identity_id: UUID
    agent_handle: str
    agent_label: str
    agent_preset_id: int
    thread_root_message_id: UUID | None = None


class AgentChannelTaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: str | None = "medium"
    status: str = "todo"
    thread_root_message_id: UUID | None = None


class AgentChannelTaskStatusRequest(BaseModel):
    task_id: UUID
    status: str
    position: int = Field(default=0, ge=0)


class AgentChannelTaskClaimSelfRequest(BaseModel):
    task_id: UUID


class AgentChannelTaskCommentRequest(BaseModel):
    task_id: UUID
    text: str = Field(min_length=1)


class AgentChannelTaskOperationResponse(BaseModel):
    action: str
    task: ServerChannelTaskResponse
    thread_root_message_id: UUID | None = None


def to_create_request(
    request: AgentChannelTaskCreateRequest,
) -> ServerChannelTaskCreateRequest:
    return ServerChannelTaskCreateRequest(
        title=request.title,
        description=request.description,
        priority=request.priority,
        status=request.status,
    )


def to_status_request(
    request: AgentChannelTaskStatusRequest,
) -> ServerChannelTaskStatusUpdateRequest:
    return ServerChannelTaskStatusUpdateRequest(
        status=request.status,
        position=request.position,
    )


def to_claim_self_request(
    *,
    assignee_preset_id: int,
) -> ServerChannelTaskClaimRequest:
    return ServerChannelTaskClaimRequest(
        assignee_preset_id=assignee_preset_id,
    )
