import unittest

from app.core.channel_runtime import (
    CHANNEL_RUNTIME_MCP_SERVER_KEY,
    _format_tool_error,
    _format_tool_result,
    _run_tool,
)


class ChannelRuntimeToolContractTests(unittest.IsolatedAsyncioTestCase):
    def _tool_text(self, result: dict) -> str:
        return result["content"][0]["text"]

    def test_unified_runtime_key_is_stable(self) -> None:
        self.assertEqual(CHANNEL_RUNTIME_MCP_SERVER_KEY, "__poco_channel_runtime")

    def test_format_tool_result_uses_title_and_json_body(self) -> None:
        result = _format_tool_result("read_channel_messages", {"messages": []})

        text = self._tool_text(result)
        self.assertTrue(text.startswith("read_channel_messages\n"))
        self.assertIn('"messages": []', text)

    def test_format_tool_error_includes_error_and_code(self) -> None:
        result = _format_tool_error(
            "read_channel_messages",
            "message_id must be provided",
            code="invalid_arguments",
        )

        text = self._tool_text(result)
        self.assertTrue(text.startswith("read_channel_messages_error\n"))
        self.assertIn('"error": "message_id must be provided"', text)
        self.assertIn('"code": "invalid_arguments"', text)

    async def test_run_tool_converts_exceptions_to_structured_error(self) -> None:
        async def fail() -> None:
            raise RuntimeError("backend unavailable")

        result = await _run_tool("list_channel_agents", fail())

        text = self._tool_text(result)
        self.assertTrue(text.startswith("list_channel_agents_error\n"))
        self.assertIn('"error": "backend unavailable"', text)
        self.assertIn('"code": "runtime_error"', text)


if __name__ == "__main__":
    unittest.main()
