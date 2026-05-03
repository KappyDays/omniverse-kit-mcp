"""Compile raw YAML into CompiledScenario with variable substitution."""

from __future__ import annotations

import re
from typing import Any

from omniverse_kit_mcp.exceptions import ScenarioCompileError
from omniverse_kit_mcp.types.common import JsonValue, ModuleName, RetryPolicy
from omniverse_kit_mcp.types.scenario import (
    CompiledScenario,
    CompiledStep,
    ScenarioDefaults,
)


def compile_scenario(raw: dict[str, Any]) -> CompiledScenario:
    """Transform validated YAML into a CompiledScenario."""
    metadata = raw["metadata"]
    spec = raw["spec"]
    variables = spec.get("variables", {})
    defaults_raw = spec.get("defaults", {})
    defaults = ScenarioDefaults(
        step_timeout_s=defaults_raw.get("stepTimeoutSeconds", 60.0),
        scenario_timeout_s=600.0,
        fail_fast=defaults_raw.get("failFast", True),
    )

    def compile_steps(phase: str) -> tuple[CompiledStep, ...]:
        steps_raw = spec.get(phase, [])
        if steps_raw is None:
            return ()
        compiled = []
        for step_raw in steps_raw:
            args = _substitute_variables(step_raw["args"], variables)
            retry = None
            if "retries" in step_raw:
                r = step_raw["retries"]
                retry = RetryPolicy(
                    max_attempts=r.get("maxAttempts", 3),
                    initial_backoff_s=r.get("initialBackoffSeconds", 0.5),
                    max_backoff_s=r.get("maxBackoffSeconds", 5.0),
                )
            try:
                module = ModuleName(step_raw["module"])
            except ValueError as exc:
                raise ScenarioCompileError(
                    f"Unknown module '{step_raw['module']}' in step '{step_raw['id']}'"
                ) from exc
            compiled.append(
                CompiledStep(
                    id=step_raw["id"],
                    phase=phase,
                    module=module,
                    action=step_raw["action"],
                    args=args,
                    timeout_s=step_raw.get("timeoutSeconds", defaults.step_timeout_s),
                    retry_policy=retry,
                    continue_on_failure=step_raw.get("continueOnFailure", False),
                    idempotent=step_raw.get("idempotent", False),
                )
            )
        return tuple(compiled)

    return CompiledScenario(
        scenario_id=metadata["id"],
        name=metadata["name"],
        tags=tuple(metadata.get("tags", [])),
        defaults=defaults,
        variables=variables,
        arrange_steps=compile_steps("arrange"),
        act_steps=compile_steps("act"),
        assert_steps=compile_steps("assert"),
        cleanup_steps=compile_steps("cleanup"),
    )


def _substitute_variables(obj: Any, variables: dict[str, Any]) -> Any:
    """Recursively replace ${variables.key} placeholders."""
    if isinstance(obj, str):
        pattern = re.compile(r"\$\{variables\.(\w+)\}")

        def replacer(match: re.Match) -> str:
            key = match.group(1)
            if key not in variables:
                raise ScenarioCompileError(f"Undefined variable: {key}")
            val = variables[key]
            return str(val)

        result = pattern.sub(replacer, obj)
        # If the entire string was a single variable reference, return the original type
        full_match = pattern.fullmatch(obj)
        if full_match:
            key = full_match.group(1)
            return variables[key]
        return result
    elif isinstance(obj, dict):
        return {k: _substitute_variables(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_variables(item, variables) for item in obj]
    return obj
