"""Scenario execution state machine."""

from __future__ import annotations

from omniverse_kit_mcp.types.scenario import ScenarioState

STATE_TRANSITIONS: dict[ScenarioState, set[ScenarioState]] = {
    ScenarioState.START: {ScenarioState.SCENARIO_LOADED, ScenarioState.ERROR},
    ScenarioState.SCENARIO_LOADED: {ScenarioState.SCHEMA_VALIDATED, ScenarioState.ERROR},
    ScenarioState.SCHEMA_VALIDATED: {ScenarioState.COMPILED, ScenarioState.ERROR},
    ScenarioState.COMPILED: {ScenarioState.ARRANGE_RUNNING, ScenarioState.ERROR},
    ScenarioState.ARRANGE_RUNNING: {
        ScenarioState.ARRANGE_DONE,
        ScenarioState.CLEANUP_RUNNING,
        ScenarioState.ERROR,
        ScenarioState.TIMEOUT,
        ScenarioState.CANCELED,
    },
    ScenarioState.ARRANGE_DONE: {
        ScenarioState.ACT_RUNNING,
        ScenarioState.CLEANUP_RUNNING,
    },
    ScenarioState.ACT_RUNNING: {
        ScenarioState.ACT_DONE,
        ScenarioState.CLEANUP_RUNNING,
        ScenarioState.ERROR,
        ScenarioState.TIMEOUT,
        ScenarioState.CANCELED,
    },
    ScenarioState.ACT_DONE: {
        ScenarioState.ASSERT_RUNNING,
        ScenarioState.CLEANUP_RUNNING,
    },
    ScenarioState.ASSERT_RUNNING: {
        ScenarioState.ASSERT_DONE,
        ScenarioState.CLEANUP_RUNNING,
        ScenarioState.ERROR,
        ScenarioState.TIMEOUT,
        ScenarioState.CANCELED,
    },
    ScenarioState.ASSERT_DONE: {ScenarioState.CLEANUP_RUNNING},
    ScenarioState.CLEANUP_RUNNING: {
        ScenarioState.CLEANUP_DONE,
        ScenarioState.ERROR,
        ScenarioState.TIMEOUT,
    },
    ScenarioState.CLEANUP_DONE: {
        ScenarioState.PASSED,
        ScenarioState.FAILED,
        ScenarioState.ERROR,
        ScenarioState.TIMEOUT,
        ScenarioState.CANCELED,
    },
}

TERMINAL_STATES = {
    ScenarioState.PASSED,
    ScenarioState.FAILED,
    ScenarioState.ERROR,
    ScenarioState.TIMEOUT,
    ScenarioState.CANCELED,
}


def can_transition(current: ScenarioState, target: ScenarioState) -> bool:
    allowed = STATE_TRANSITIONS.get(current, set())
    return target in allowed
