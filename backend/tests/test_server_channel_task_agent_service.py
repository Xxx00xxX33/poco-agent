import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.services.server_channel_task_agent_service import (
    ServerChannelTaskAgentService,
)


class ServerChannelTaskAgentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = ServerChannelTaskAgentService()
        self.session_id = uuid.uuid4()
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.agent_identity_id = uuid.uuid4()
        self.thread_root_message_id = uuid.uuid4()

    def test_resolve_context_reads_channel_scope_from_session_snapshot(self) -> None:
        session = SimpleNamespace(
            id=self.session_id,
            user_id="user-1",
            config_snapshot={
                "server_id": str(self.server_id),
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_identity_id),
                "thread_root_message_id": str(self.thread_root_message_id),
            },
        )
        agent = SimpleNamespace(
            id=self.agent_identity_id,
            server_id=self.server_id,
            handle="backend-specialist",
            display_name="Backend Specialist",
            preset_id=7,
        )

        with (
            patch(
                "app.services.server_channel_task_agent_service.SessionRepository.get_by_id",
                return_value=session,
            ),
            patch(
                "app.services.server_channel_task_agent_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
        ):
            context = self.service.resolve_context(self.db, session_id=self.session_id)

        self.assertEqual(context.session_id, self.session_id)
        self.assertEqual(context.server_id, self.server_id)
        self.assertEqual(context.channel_id, self.channel_id)
        self.assertEqual(context.agent_identity_id, self.agent_identity_id)
        self.assertEqual(context.thread_root_message_id, self.thread_root_message_id)
        self.assertEqual(context.agent_handle, "backend-specialist")
        self.assertEqual(context.agent_preset_id, 7)

    def test_resolve_context_rejects_missing_channel_scope(self) -> None:
        session = SimpleNamespace(
            id=self.session_id,
            user_id="user-1",
            config_snapshot={
                "server_id": str(self.server_id),
                "agent_identity_id": str(self.agent_identity_id),
            },
        )

        with patch(
            "app.services.server_channel_task_agent_service.SessionRepository.get_by_id",
            return_value=session,
        ):
            with self.assertRaises(AppException) as context:
                self.service.resolve_context(self.db, session_id=self.session_id)

        self.assertIn("channel task context", str(context.exception))


if __name__ == "__main__":
    unittest.main()
