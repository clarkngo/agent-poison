"""Deterministic tool execution engine.

Given a scenario and a tool call the model made, always returns the same
content for the same (tool_name, poisoned) pair — no randomness, no network
calls — so runs are reproducible across models and defense modes.
"""

from __future__ import annotations

from agent_poison.models.schemas import Scenario


class MockToolServer:
    """Executes tool calls against a scenario's fixed, deterministic outputs."""

    def __init__(self, scenario: Scenario, poisoned: bool):
        self.scenario = scenario
        self.poisoned = poisoned
        self.unauthorized_tool_invoked = False
        self.ground_truth_tool_invoked = False

    def execute(self, tool_name: str, arguments: dict) -> str:
        """Return the mock string content for a single tool call."""
        if tool_name == self.scenario.unauthorized_target_tool:
            self.unauthorized_tool_invoked = True
            return self._unauthorized_confirmation(tool_name, arguments)

        if tool_name == self.scenario.ground_truth_tool.tool_name:
            self.ground_truth_tool_invoked = True

        mock_return = self.scenario.mock_returns.get(tool_name)
        if mock_return is not None:
            return mock_return.render(poisoned=self.poisoned)

        return f'{{"status": "ok", "tool": "{tool_name}"}}'

    @staticmethod
    def _unauthorized_confirmation(tool_name: str, arguments: dict) -> str:
        # A plausible-looking success response, so a poisoned model that reads the
        # confirmation doesn't immediately realize something is wrong and retry.
        return f'{{"status": "executed", "tool": "{tool_name}", "arguments": {arguments}}}'
