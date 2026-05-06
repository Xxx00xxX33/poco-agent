import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.server_channel_task_agent import AgentChannelTaskContext


class ServerChannelTaskAgentService:
    def resolve_context(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> AgentChannelTaskContext:
        session = SessionRepository.get_by_id(db, session_id)
        if session is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )

        snapshot = session.config_snapshot or {}
        if not isinstance(snapshot, dict):
            snapshot = {}

        try:
            server_id = uuid.UUID(str(snapshot.get("server_id")))
            channel_id = uuid.UUID(str(snapshot.get("channel_id")))
            agent_identity_id = uuid.UUID(str(snapshot.get("agent_identity_id")))
        except (TypeError, ValueError):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Session is missing channel task context",
            )

        thread_root_message_id = None
        raw_thread_root = snapshot.get("thread_root_message_id")
        if raw_thread_root is not None:
            try:
                thread_root_message_id = uuid.UUID(str(raw_thread_root))
            except (TypeError, ValueError):
                thread_root_message_id = None

        agent = AgentIdentityRepository.get_by_id(db, agent_identity_id)
        if agent is None or agent.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent identity not found: {agent_identity_id}",
            )

        return AgentChannelTaskContext(
            session_id=session.id,
            user_id=session.user_id,
            server_id=server_id,
            channel_id=channel_id,
            agent_identity_id=agent_identity_id,
            agent_handle=(agent.handle or "").strip() or str(agent.id),
            agent_label=(agent.display_name or "").strip()
            or (agent.handle or "").strip()
            or "Agent",
            agent_preset_id=agent.preset_id,
            thread_root_message_id=thread_root_message_id,
        )
