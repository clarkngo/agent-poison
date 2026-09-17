"""Pydantic schemas shared across the harness: scenarios, tool defs, and eval results."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class InjectionStrategy(str, Enum):
    DIRECT_OVERRIDE = "direct_override"
    DELIMITER_MANIPULATION = "delimiter_manipulation"
    CONTEXTUAL_DECEPTION = "contextual_deception"
    NONE = "none"


class DefenseMode(str, Enum):
    NONE = "none"
    XML_DELIMITERS = "xml_delimiters"
    SYSTEM_REINFORCEMENT = "system_reinforcement"
    DUAL_PROMPT = "dual_prompt"


class ToolParameterSchema(BaseModel):
    """JSON-schema body for a function's `parameters` field (OpenAI tool format)."""

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    """A single tool exposed to the model, in OpenAI function-calling schema."""

    name: str
    description: str
    parameters: ToolParameterSchema = Field(default_factory=ToolParameterSchema)

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters.model_dump(),
            },
        }


class MockToolReturn(BaseModel):
    """What `mock_server.py` hands back for a given tool call, benign or poisoned."""

    benign_content: str
    injected_content: Optional[str] = None
    injection_strategy: InjectionStrategy = InjectionStrategy.NONE
    notes: Optional[str] = None

    def render(self, *, poisoned: bool) -> str:
        if poisoned and self.injected_content is not None:
            return self.injected_content
        return self.benign_content


class GroundTruthToolCall(BaseModel):
    """The tool call the agent is expected to make to legitimately complete the task."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Scenario(BaseModel):
    """A single benchmark scenario: a user task, an available toolset, and an injection."""

    id: str
    name: str
    description: str = ""
    system_prompt: str
    user_prompt: str
    available_tools: list[ToolDefinition]
    ground_truth_tool: GroundTruthToolCall
    unauthorized_target_tool: str
    mock_returns: dict[str, MockToolReturn] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    def tool_names(self) -> list[str]:
        return [t.name for t in self.available_tools]


class ToolCallRecord(BaseModel):
    """One tool invocation observed during a run."""

    turn: int
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    tool_call_id: Optional[str] = None


class RunResult(BaseModel):
    """Outcome of a single (model, scenario, defense_mode, poisoned) execution."""

    scenario_id: str
    model: str
    defense_mode: DefenseMode
    poisoned: bool
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    hijack_triggered: bool = False
    ground_truth_completed: bool = False
    refused: bool = False
    error: Optional[str] = None

    @property
    def task_failed(self) -> bool:
        """Failed the legitimate task regardless of whether the hijack succeeded."""
        return not self.ground_truth_completed


class AggregateMetrics(BaseModel):
    """Metrics rolled up across N runs of one (model, scenario_or_all, defense_mode) cell."""

    model: str
    defense_mode: DefenseMode
    scenario_id: str = "ALL"
    n_runs: int = 0
    attack_success_rate: float = 0.0
    benign_accuracy: float = 0.0
    task_interruption_rate: float = 0.0
    refusal_rate: float = 0.0
