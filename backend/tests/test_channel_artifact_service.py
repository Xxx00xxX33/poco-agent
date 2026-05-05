import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.agent_session import AgentSession
from app.services.channel_artifact_service import ChannelArtifactService


class ChannelArtifactServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = ChannelArtifactService()
        self.session_id = uuid.uuid4()
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.agent_identity_id = uuid.uuid4()
        self.session = AgentSession(
            id=self.session_id,
            user_id="user-1",
            sdk_session_id=None,
            config_snapshot={
                "server_id": str(self.server_id),
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_identity_id),
                "agent_runtime_mode": "persistent",
            },
            workspace_files_prefix="workspaces/user-1/session/files",
            workspace_manifest_key="workspaces/user-1/session/manifest.json",
            workspace_export_status="ready",
            status="completed",
        )

    def test_sync_session_workspace_artifacts_publishes_manifest_files(self) -> None:
        manifest = {
            "files": [
                {
                    "path": "plans/rate-limit-plan.md",
                    "key": "workspaces/user-1/session/files/plans/rate-limit-plan.md",
                    "mimeType": "text/markdown",
                    "size": 1200,
                },
                {
                    "path": "notes/api-checklist.txt",
                    "key": "workspaces/user-1/session/files/notes/api-checklist.txt",
                    "mimeType": "text/plain",
                    "size": 200,
                },
            ]
        }

        with (
            patch.object(
                self.service._storage,
                "get_manifest",
                return_value=manifest,
            ),
            patch(
                "app.services.channel_artifact_service.ChannelArtifactRepository.upsert_many"
            ) as upsert_many,
        ):
            count = self.service.sync_session_workspace_artifacts(self.db, self.session)

        self.assertEqual(count, 2)
        upsert_many.assert_called_once()
        rows = upsert_many.call_args.kwargs["artifacts"]
        self.assertEqual(rows[0].channel_id, self.channel_id)
        self.assertEqual(rows[0].agent_identity_id, self.agent_identity_id)
        self.assertEqual(rows[0].logical_path, "/plans/rate-limit-plan.md")
        self.assertEqual(rows[1].display_name, "api-checklist.txt")

    def test_list_channel_artifact_nodes_groups_files_by_agent(self) -> None:
        artifacts = [
            SimpleNamespace(
                id=uuid.uuid4(),
                channel_id=self.channel_id,
                agent_identity_id=self.agent_identity_id,
                publisher_user_id=None,
                logical_path="/plans/rate-limit-plan.md",
                display_name="rate-limit-plan.md",
                mime_type="text/markdown",
                object_key="objects/plan.md",
                source_session_id=self.session_id,
            )
        ]

        with (
            patch(
                "app.services.channel_artifact_service.ChannelArtifactRepository.list_by_channel",
                return_value=artifacts,
            ),
            patch(
                "app.services.channel_artifact_service.AgentIdentityRepository.get_by_id",
                return_value=SimpleNamespace(
                    id=self.agent_identity_id,
                    display_name="api-specialist",
                    handle="api-specialist",
                ),
            ),
            patch.object(
                self.service._storage,
                "presign_get",
                return_value="https://example.com/rate-limit-plan.md",
            ),
            patch(
                "app.services.channel_artifact_service.require_server_member",
                return_value=object(),
            ),
        ):
            nodes = self.service.list_channel_artifact_nodes(
                self.db,
                current_user=SimpleNamespace(id="user-1"),
                server_id=self.server_id,
                channel_id=self.channel_id,
            )

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name, "api-specialist")
        self.assertEqual(nodes[0].children[0].name, "plans")
        self.assertEqual(nodes[0].children[0].children[0].name, "rate-limit-plan.md")
        self.assertEqual(
            nodes[0].children[0].children[0].url,
            "https://example.com/rate-limit-plan.md",
        )


if __name__ == "__main__":
    unittest.main()
