import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.agent_identity import (
    AgentIdentityCreateRequest,
    AgentIdentityResponse,
    ChannelAgentMemberCreateRequest,
    ChannelAgentMemberResponse,
)
from app.schemas.response import Response, ResponseSchema
from app.services.agent_identity_service import AgentIdentityService

router = APIRouter(prefix="/servers/{server_id}/agents", tags=["server-agents"])
channel_router = APIRouter(
    prefix="/servers/{server_id}/channels/{channel_id}/agents",
    tags=["server-channel-agents"],
)

service = AgentIdentityService()


@router.get("", response_model=ResponseSchema[list[AgentIdentityResponse]])
async def list_server_agents(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_agents(db, current_user, server_id)
    return Response.success(data=result, message="Server agents retrieved successfully")


@router.post("", response_model=ResponseSchema[AgentIdentityResponse])
async def create_server_agent(
    server_id: uuid.UUID,
    request: AgentIdentityCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_agent(db, current_user, server_id, request)
    return Response.success(data=result, message="Server agent created successfully")


@router.get("/{agent_identity_id}", response_model=ResponseSchema[AgentIdentityResponse])
async def get_server_agent(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_agent(db, current_user, server_id, agent_identity_id)
    return Response.success(data=result, message="Server agent retrieved successfully")


@channel_router.get("", response_model=ResponseSchema[list[AgentIdentityResponse]])
async def list_channel_agents(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_channel_agents(db, current_user, server_id, channel_id)
    return Response.success(data=result, message="Channel agents retrieved successfully")


@channel_router.post("", response_model=ResponseSchema[ChannelAgentMemberResponse])
async def add_agent_to_channel(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    request: ChannelAgentMemberCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.add_agent_to_channel(
        db,
        current_user,
        server_id,
        channel_id,
        request,
    )
    return Response.success(data=result, message="Channel agent added successfully")
