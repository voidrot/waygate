from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CompileAgentRole(StrEnum):
    SOURCE_NORMALIZATION = "source_normalization"
    SOURCE_ANALYSIS = "source_analysis"
    SYNTHESIS = "synthesis"
    REVIEW = "review"
    PUBLISH = "publish"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True)
class CompileAgentLayoutEntry:
    role: CompileAgentRole
    description: str
    execution_boundary: str


DEFAULT_COMPILE_AGENT_LAYOUT: tuple[CompileAgentLayoutEntry, ...] = (
    CompileAgentLayoutEntry(
        role=CompileAgentRole.SOURCE_NORMALIZATION,
        description="Normalize the request and build stable document order.",
        execution_boundary="deterministic",
    ),
    CompileAgentLayoutEntry(
        role=CompileAgentRole.SOURCE_ANALYSIS,
        description="Analyze one source document under supervisor control with specialist subagents.",
        execution_boundary="agentic",
    ),
    CompileAgentLayoutEntry(
        role=CompileAgentRole.SYNTHESIS,
        description="Synthesize the accumulated source analyses into one draft.",
        execution_boundary="agentic",
    ),
    CompileAgentLayoutEntry(
        role=CompileAgentRole.REVIEW,
        description="Review the synthesized draft against the parsed source set.",
        execution_boundary="agentic",
    ),
    CompileAgentLayoutEntry(
        role=CompileAgentRole.PUBLISH,
        description="Render the publish artifact at the deterministic storage boundary.",
        execution_boundary="deterministic",
    ),
    CompileAgentLayoutEntry(
        role=CompileAgentRole.HUMAN_REVIEW,
        description="Build the human-review artifact and interrupt payload.",
        execution_boundary="deterministic",
    ),
)


__all__ = [
    "CompileAgentLayoutEntry",
    "CompileAgentRole",
    "DEFAULT_COMPILE_AGENT_LAYOUT",
]
