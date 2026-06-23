"""Scenario runner — Arrange → Act → Assert + finally Cleanup."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any

from omniverse_kit_mcp.modules.asset_module import AssetModule
from omniverse_kit_mcp.modules.base import error_result, fail_result, make_meta
from omniverse_kit_mcp.modules.character_module import CharacterModule
from omniverse_kit_mcp.modules.content_module import ContentModule
from omniverse_kit_mcp.modules.extension_module import ExtensionModule
from omniverse_kit_mcp.modules.job_module import JobModule
from omniverse_kit_mcp.modules.lakehouse_module import LakehouseModule
from omniverse_kit_mcp.modules.lighting_module import LightingModule
from omniverse_kit_mcp.modules.material_module import MaterialModule
from omniverse_kit_mcp.modules.navigation_module import NavigationModule
from omniverse_kit_mcp.modules.omnigraph_module import OmnigraphModule
from omniverse_kit_mcp.modules.physics_module import PhysicsModule
from omniverse_kit_mcp.modules.replicator_module import ReplicatorModule
from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.modules.sensor_module import SensorModule
from omniverse_kit_mcp.modules.simulation_module import SimulationModule
from omniverse_kit_mcp.modules.stage_module import StageModule
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.modules.window_module import WindowModule
from omniverse_kit_mcp.scenario.action_registry import CONTEXT_AWARE_ACTIONS, build_request
from omniverse_kit_mcp.scenario.context import ScenarioContext
from omniverse_kit_mcp.types.common import (
    ExecutionStatus,
    JsonPrimitive,
    JsonValue,
    ModuleName,
    ModuleResult,
)
from omniverse_kit_mcp.types.extension import ExtensionResetRequest
from omniverse_kit_mcp.types.scenario import (
    CompiledScenario,
    CompiledStep,
    ScenarioRunSummary,
    StepResult,
)

logger = logging.getLogger(__name__)

_NO_FALLBACK_CLEANUP_ACTIONS = frozenset({
    (ModuleName.ASSET, "official_sync_status"),
    (ModuleName.ASSET, "official_search"),
    (ModuleName.ASSET, "official_resolve"),
    (ModuleName.ASSET, "official_get"),
    # official_verify uses a temporary /World/Official* prim and deletes it in
    # AssetModule finally blocks; extension reset adds no extra cleanup signal.
    (ModuleName.ASSET, "official_verify"),
})
_RETRY_FAILURE_MESSAGE_LIMIT = 512


@dataclass(slots=True, frozen=True)
class _StepExecution:
    module_result: ModuleResult[Any]
    attempts: int
    max_attempts: int
    retry_failures: tuple[dict[str, JsonValue], ...] = ()


class ScenarioRunner:
    def __init__(
        self,
        stage: StageModule,
        viewport: ViewportModule,
        lakehouse: LakehouseModule,
        extension: ExtensionModule,
        simulation: SimulationModule,
        robot: RobotModule,
        job: JobModule,
        asset: AssetModule,
        character: CharacterModule,
        window: WindowModule,
        navigation: NavigationModule,
        sensor: SensorModule,
        physics: PhysicsModule,
        lighting: LightingModule,
        material: MaterialModule,
        replicator: ReplicatorModule,
        omnigraph: OmnigraphModule,
        content: ContentModule,
    ) -> None:
        self._modules = {
            ModuleName.STAGE: stage,
            ModuleName.VIEWPORT: viewport,
            ModuleName.LAKEHOUSE: lakehouse,
            ModuleName.EXTENSION: extension,
            ModuleName.SIMULATION: simulation,
            ModuleName.ROBOT: robot,
            ModuleName.JOB: job,
            ModuleName.ASSET: asset,
            ModuleName.CHARACTER: character,
            ModuleName.WINDOW: window,
            ModuleName.NAVIGATION: navigation,
            ModuleName.SENSOR: sensor,
            ModuleName.PHYSICS: physics,
            ModuleName.LIGHTING: lighting,
            ModuleName.MATERIAL: material,
            ModuleName.REPLICATOR: replicator,
            ModuleName.OMNIGRAPH: omnigraph,
            ModuleName.CONTENT: content,
        }
        self._extension = extension

    async def run(
        self,
        scenario: CompiledScenario,
        *,
        fail_fast_override: bool | None = None,
        variable_overrides: dict[str, Any] | None = None,
    ) -> ScenarioRunSummary:
        started = int(time.time() * 1000)
        ctx = ScenarioContext()
        step_results: list[StepResult] = []
        terminal_status = ExecutionStatus.PASSED
        skip_remaining_phases = False

        # Apply fail_fast override if provided
        effective_fail_fast = (
            fail_fast_override if fail_fast_override is not None
            else scenario.defaults.fail_fast
        )

        try:
            # Apply scenario-level timeout
            async with asyncio.timeout(scenario.defaults.scenario_timeout_s):
                # --- Arrange ---
                if scenario.arrange_steps and not skip_remaining_phases:
                    arr_results = await self._run_phase(
                        scenario.arrange_steps, ctx, scenario.scenario_id, fail_fast=True
                    )
                    step_results.extend(arr_results)
                    if _phase_has_fatal_failure(arr_results, scenario.arrange_steps):
                        terminal_status = ExecutionStatus.FAILED
                        step_results.extend(
                            _skip_steps(scenario.act_steps, scenario.assert_steps)
                        )
                        skip_remaining_phases = True

                # --- Act ---
                if scenario.act_steps and not skip_remaining_phases:
                    act_results = await self._run_phase(
                        scenario.act_steps, ctx, scenario.scenario_id, fail_fast=True
                    )
                    step_results.extend(act_results)
                    if _phase_has_fatal_failure(act_results, scenario.act_steps):
                        terminal_status = ExecutionStatus.FAILED
                        step_results.extend(_skip_steps(scenario.assert_steps))
                        skip_remaining_phases = True

                # --- Assert ---
                if scenario.assert_steps and not skip_remaining_phases:
                    assert_results = await self._run_phase(
                        scenario.assert_steps,
                        ctx,
                        scenario.scenario_id,
                        fail_fast=effective_fail_fast,
                    )
                    step_results.extend(assert_results)
                    if _phase_has_fatal_failure(assert_results, scenario.assert_steps):
                        terminal_status = ExecutionStatus.FAILED

        except (asyncio.TimeoutError, TimeoutError):
            terminal_status = ExecutionStatus.TIMEOUT
        except Exception as exc:
            logger.exception("Scenario execution error: %s", exc)
            terminal_status = ExecutionStatus.ERROR
        finally:
            # Cleanup always runs — user-defined cleanup steps + fallback extension reset
            cleanup_results = await self._run_cleanup(scenario, ctx)
            step_results.extend(cleanup_results)

        return self._build_summary(scenario, terminal_status, step_results, started, ctx)

    async def _run_phase(
        self,
        steps: tuple[CompiledStep, ...],
        ctx: ScenarioContext,
        scenario_id: str,
        *,
        fail_fast: bool,
    ) -> list[StepResult]:
        results: list[StepResult] = []
        for step in steps:
            step_started = int(time.time() * 1000)
            try:
                timeout = step.timeout_s or 60.0
                execution = await self._execute_step_with_retries(
                    step, ctx, scenario_id, timeout
                )
                module_result = execution.module_result
                status = module_result.status if module_result else ExecutionStatus.ERROR
                if module_result and module_result.artifacts:
                    for k, v in module_result.artifacts.items():
                        ctx.store_artifact(step.id, k, v)
                if module_result and module_result.data is not None:
                    ctx.store_step_data(step.id, module_result.data)

                results.append(StepResult(
                    step_id=step.id,
                    phase=step.phase,
                    status=status,
                    message=module_result.message if module_result else None,
                    duration_ms=int(time.time() * 1000) - step_started,
                    artifacts=module_result.artifacts if module_result else {},
                    data_summary=(
                        _summarize_step_data(module_result.data)
                        if module_result and module_result.data is not None
                        else {}
                    ),
                    attempts=execution.attempts,
                    max_attempts=execution.max_attempts,
                    retry_failures=execution.retry_failures,
                    continue_on_failure=step.continue_on_failure,
                ))
                if status != ExecutionStatus.PASSED and fail_fast and not step.continue_on_failure:
                    break
            except asyncio.TimeoutError:
                results.append(StepResult(
                    step_id=step.id,
                    phase=step.phase,
                    status=ExecutionStatus.TIMEOUT,
                    message=f"Step timed out after {timeout}s",
                    duration_ms=int(time.time() * 1000) - step_started,
                    attempts=1,
                    max_attempts=_step_max_attempts(step),
                    retry_failures=_hard_failure_retry_summary(
                        1,
                        ExecutionStatus.TIMEOUT,
                        None,
                        f"Step timed out after {timeout}s",
                        step,
                    ),
                    continue_on_failure=step.continue_on_failure,
                ))
                if fail_fast and not step.continue_on_failure:
                    break
            except Exception as exc:
                results.append(StepResult(
                    step_id=step.id,
                    phase=step.phase,
                    status=ExecutionStatus.ERROR,
                    message=str(exc),
                    duration_ms=int(time.time() * 1000) - step_started,
                    attempts=1,
                    max_attempts=_step_max_attempts(step),
                    retry_failures=_hard_failure_retry_summary(
                        1,
                        ExecutionStatus.ERROR,
                        None,
                        str(exc),
                        step,
                    ),
                    continue_on_failure=step.continue_on_failure,
                ))
                if fail_fast and not step.continue_on_failure:
                    break
        return results

    async def _execute_step_with_retries(
        self,
        step: CompiledStep,
        ctx: ScenarioContext,
        scenario_id: str,
        timeout: float,
    ) -> _StepExecution:
        policy = step.retry_policy
        if policy is not None and policy.max_attempts > 1 and not step.idempotent:
            return _StepExecution(
                module_result=error_result(
                    (
                        f"Step '{step.id}' declares retries but is not marked "
                        "idempotent=true"
                    ),
                    started_ms=int(time.time() * 1000),
                    error_code="SCENARIO_RETRY_REQUIRES_IDEMPOTENT_STEP",
                ),
                attempts=0,
                max_attempts=policy.max_attempts,
            )

        max_attempts = max(1, policy.max_attempts if policy is not None else 1)
        backoff_s = policy.initial_backoff_s if policy is not None else 0.0
        max_backoff_s = policy.max_backoff_s if policy is not None else 0.0
        record_retry_failures = max_attempts > 1
        retry_failures: list[dict[str, JsonValue]] = []
        started = int(time.time() * 1000)

        for attempt in range(1, max_attempts + 1):
            try:
                module_result = await asyncio.wait_for(
                    self._execute_step(step, ctx, scenario_id),
                    timeout=timeout,
                )
            except (asyncio.TimeoutError, TimeoutError):
                message = f"Step timed out after {timeout}s"
                if record_retry_failures:
                    retry_failures.append(_failure_summary(
                        attempt,
                        ExecutionStatus.TIMEOUT,
                        "SCENARIO_STEP_TIMEOUT",
                        message,
                    ))
                if attempt == max_attempts:
                    return _StepExecution(
                        module_result=_timeout_result(message, started),
                        attempts=attempt,
                        max_attempts=max_attempts,
                        retry_failures=tuple(retry_failures),
                    )
                await _sleep_retry_backoff(backoff_s)
                backoff_s = _next_backoff(backoff_s, max_backoff_s, policy)
                continue
            except Exception as exc:
                message = str(exc)
                if record_retry_failures:
                    retry_failures.append(_failure_summary(
                        attempt,
                        ExecutionStatus.ERROR,
                        "SCENARIO_STEP_EXCEPTION",
                        message,
                    ))
                if attempt == max_attempts:
                    return _StepExecution(
                        module_result=error_result(
                            message,
                            started_ms=started,
                            error_code="SCENARIO_STEP_EXCEPTION",
                        ),
                        attempts=attempt,
                        max_attempts=max_attempts,
                        retry_failures=tuple(retry_failures),
                    )
                await _sleep_retry_backoff(backoff_s)
                backoff_s = _next_backoff(backoff_s, max_backoff_s, policy)
                continue

            status = module_result.status if module_result else ExecutionStatus.ERROR
            if status == ExecutionStatus.PASSED or attempt == max_attempts:
                if status != ExecutionStatus.PASSED and record_retry_failures:
                    retry_failures.append(_retry_failure_summary(attempt, module_result))
                return _StepExecution(
                    module_result=module_result,
                    attempts=attempt,
                    max_attempts=max_attempts,
                    retry_failures=tuple(retry_failures),
                )
            if record_retry_failures:
                retry_failures.append(_retry_failure_summary(attempt, module_result))
            await _sleep_retry_backoff(backoff_s)
            backoff_s = _next_backoff(backoff_s, max_backoff_s, policy)

        raise RuntimeError("unreachable retry loop exit")

    async def _execute_step(
        self, step: CompiledStep, ctx: ScenarioContext, scenario_id: str
    ) -> ModuleResult[Any]:
        meta = make_meta(step.module, scenario_id=scenario_id, step_id=step.id)
        module = self._modules[step.module]

        # Context-aware actions resolve prior step data from ctx before calling the module.
        if (step.module, step.action) in CONTEXT_AWARE_ACTIONS:
            return await self._execute_context_aware(step, ctx, module, meta)

        action_method = getattr(module, step.action, None)
        if action_method is None:
            return error_result(
                f"Unknown action '{step.action}' on module '{step.module.value}'",
                started_ms=meta.started_at_epoch_ms or int(time.time() * 1000),
            )
        # Build typed request object from args dict via action registry
        request_obj = build_request(step.module, step.action, step.args)
        if request_obj is not None:
            return await action_method(meta, request_obj)
        # Fallback: pass args as kwargs (for simple actions without typed requests)
        return await action_method(meta, **step.args)  # type: ignore[arg-type]

    async def _execute_context_aware(
        self,
        step: CompiledStep,
        ctx: ScenarioContext,
        module: Any,
        meta: Any,
    ) -> ModuleResult[Any]:
        """Dispatch for actions that need prior ctx step data (e.g. diff_snapshots)."""
        started = meta.started_at_epoch_ms or int(time.time() * 1000)

        if step.module == ModuleName.STAGE and step.action == "diff_snapshots":
            args = build_request(step.module, step.action, step.args) or step.args
            before = ctx.get_step_data(args["before_step_id"])
            after = ctx.get_step_data(args["after_step_id"])
            if before is None:
                return error_result(
                    f"diff_snapshots: no snapshot data for before_step_id='{args['before_step_id']}' "
                    "(prior step must be stage.capture_snapshot)",
                    started_ms=started,
                    error_code="DIFF_MISSING_SNAPSHOT",
                )
            if after is None:
                return error_result(
                    f"diff_snapshots: no snapshot data for after_step_id='{args['after_step_id']}' "
                    "(prior step must be stage.capture_snapshot)",
                    started_ms=started,
                    error_code="DIFF_MISSING_SNAPSHOT",
                )

            result = await module.diff_snapshots(meta, before, after)
            if not result.ok:
                return result

            total = result.data.total_changes if result.data is not None else 0
            min_c = args.get("min_changes")
            max_c = args.get("max_changes")
            if min_c is not None and total < min_c:
                return fail_result(
                    f"Diff has {total} changes, expected ≥ {min_c}",
                    started_ms=started,
                    data=result.data,
                    error_code="DIFF_TOO_FEW_CHANGES",
                )
            if max_c is not None and total > max_c:
                return fail_result(
                    f"Diff has {total} changes, expected ≤ {max_c}",
                    started_ms=started,
                    data=result.data,
                    error_code="DIFF_TOO_MANY_CHANGES",
                )
            return result

        if step.module == ModuleName.JOB and step.action == "status":
            return await self._poll_job_status(step, ctx, module, meta, started)

        return error_result(
            f"Context-aware dispatch missing for {step.module.value}.{step.action}",
            started_ms=started,
        )

    async def _poll_job_status(
        self,
        step: CompiledStep,
        ctx: ScenarioContext,
        module: Any,
        meta: Any,
        started: int,
    ) -> ModuleResult[Any]:
        """Poll a Job until it reaches a terminal state (done/error/canceled).

        Resolves ``job_id`` either from literal args or from a prior
        ``robot.navigate_to`` step whose ``RobotNavigateResult.job_id`` is
        stored in ``ctx``. Fails if the job times out after ``max_polls``
        iterations or ends with an unexpected status.
        """
        args = build_request(step.module, step.action, step.args) or step.args
        job_id = args.get("job_id")
        navigate_step_id = args.get("navigate_step_id")

        if job_id is None and navigate_step_id is not None:
            prior = ctx.get_step_data(navigate_step_id)
            if prior is None:
                return error_result(
                    f"job.status: no prior step data for navigate_step_id='{navigate_step_id}'",
                    started_ms=started,
                    error_code="JOB_MISSING_NAVIGATE_STEP",
                )
            job_id = getattr(prior, "job_id", None)
            if job_id is None:
                return error_result(
                    f"job.status: prior step '{navigate_step_id}' did not produce a job_id",
                    started_ms=started,
                    error_code="JOB_MISSING_JOB_ID",
                )

        if not job_id:
            return error_result(
                "job.status requires 'job_id' or 'navigate_step_id'",
                started_ms=started,
                error_code="JOB_MISSING_JOB_ID",
            )

        poll_interval = float(args.get("poll_interval_s", 0.5))
        max_polls = int(args.get("max_polls", 60))
        expected = args.get("expected_status")
        result: ModuleResult[Any] | None = None
        for _ in range(max_polls):
            result = await module.status(meta, job_id)
            if not result.ok:
                return result
            js = result.data
            if js is not None and js.status in ("done", "error", "canceled"):
                break
            await asyncio.sleep(poll_interval)
        else:
            return fail_result(
                f"Job {job_id} did not reach terminal state within {max_polls} polls",
                started_ms=started,
                data=result.data if result else None,
                error_code="JOB_POLL_TIMEOUT",
            )

        js = result.data if result else None
        if js is None:
            return error_result(
                "job.status: empty polling result",
                started_ms=started,
                error_code="JOB_EMPTY_RESULT",
            )
        if expected is not None and js.status != expected:
            return fail_result(
                f"Expected job status '{expected}', got '{js.status}' (error={js.error})",
                started_ms=started,
                data=js,
                error_code="JOB_UNEXPECTED_STATUS",
            )
        if expected is None and js.status == "error":
            return fail_result(
                f"Job {job_id} failed: {js.error}",
                started_ms=started,
                data=js,
                error_code="JOB_ERROR_STATUS",
            )
        return result

    async def _run_cleanup(
        self, scenario: CompiledScenario, ctx: ScenarioContext
    ) -> list[StepResult]:
        """Run user-defined cleanup steps, then always run extension reset as fallback."""
        results: list[StepResult] = []

        # Run user-defined cleanup steps (non-fatal)
        if scenario.cleanup_steps:
            try:
                cleanup_phase_results = await self._run_phase(
                    scenario.cleanup_steps, ctx, scenario.scenario_id, fail_fast=False
                )
                results.extend(cleanup_phase_results)
            except Exception as exc:
                logger.warning("User cleanup steps failed (non-fatal): %s", exc)
                results.append(StepResult(
                    step_id="cleanup_user_error",
                    phase="cleanup",
                    status=ExecutionStatus.ERROR,
                    message=f"User cleanup error: {exc}",
                ))

        if not _scenario_needs_fallback_cleanup(scenario):
            return results

        # Run extension reset as final fallback for scenarios that touch live app state.
        started = int(time.time() * 1000)
        try:
            meta = make_meta(ModuleName.EXTENSION, scenario_id=scenario.scenario_id, step_id="__fallback_cleanup_reset")
            result = await self._extension.reset(meta, ExtensionResetRequest())
            results.append(StepResult(
                step_id="__fallback_cleanup_reset",
                phase="cleanup",
                status=result.status,
                message=result.message,
                duration_ms=int(time.time() * 1000) - started,
            ))
        except Exception as exc:
            logger.warning("Extension reset cleanup failed (non-fatal): %s", exc)
            results.append(StepResult(
                step_id="__fallback_cleanup_reset",
                phase="cleanup",
                status=ExecutionStatus.ERROR,
                message=f"Cleanup error (secondary): {exc}",
                duration_ms=int(time.time() * 1000) - started,
            ))

        return results

    def _build_summary(
        self,
        scenario: CompiledScenario,
        status: ExecutionStatus,
        step_results: list[StepResult],
        started_ms: int,
        ctx: ScenarioContext,
    ) -> ScenarioRunSummary:
        passed = sum(1 for r in step_results if r.status == ExecutionStatus.PASSED)
        failed = sum(1 for r in step_results if _is_failed_step_status(r.status))
        skipped = sum(1 for r in step_results if r.status == ExecutionStatus.SKIPPED)
        cleanup_failed = _cleanup_failed_step_count(step_results)
        continued = _continued_failed_step_count(step_results)
        fatal_failed = max(0, failed - cleanup_failed - continued)
        return ScenarioRunSummary(
            scenario_id=scenario.scenario_id,
            status=status,
            passed_steps=passed,
            failed_steps=failed,
            skipped_steps=skipped,
            started_at_epoch_ms=started_ms,
            ended_at_epoch_ms=int(time.time() * 1000),
            step_results=tuple(step_results),
            artifact_paths=ctx.all_artifact_paths,
            continued_steps=continued,
            fatal_failed_steps=fatal_failed,
            cleanup_failed_steps=cleanup_failed,
        )


def _retry_failure_summary(
    attempt: int,
    result: ModuleResult[Any],
) -> dict[str, JsonValue]:
    summary = _failure_summary(
        attempt,
        result.status,
        result.error_code,
        result.message,
    )
    if result.data is not None:
        summary["data_summary"] = _summarize_step_data(result.data)
    return summary


def _failure_summary(
    attempt: int,
    status: ExecutionStatus,
    error_code: str | None,
    message: str | None,
) -> dict[str, JsonValue]:
    return {
        "attempt": attempt,
        "status": status.value,
        "error_code": error_code,
        "message": _truncate_retry_message(message),
    }


def _is_failed_step_status(status: ExecutionStatus) -> bool:
    return status in {
        ExecutionStatus.FAILED,
        ExecutionStatus.ERROR,
        ExecutionStatus.TIMEOUT,
    }


def _continued_failed_step_count(step_results: list[StepResult]) -> int:
    return sum(
        1
        for result in step_results
        if result.phase != "cleanup"
        and result.continue_on_failure
        and _is_failed_step_status(result.status)
    )


def _cleanup_failed_step_count(step_results: list[StepResult]) -> int:
    return sum(
        1
        for result in step_results
        if result.phase == "cleanup" and _is_failed_step_status(result.status)
    )


def _scenario_needs_fallback_cleanup(scenario: CompiledScenario) -> bool:
    steps = (
        scenario.arrange_steps
        + scenario.act_steps
        + scenario.assert_steps
        + scenario.cleanup_steps
    )
    return any(
        (step.module, step.action) not in _NO_FALLBACK_CLEANUP_ACTIONS
        for step in steps
    )


def _timeout_result(message: str, started_ms: int) -> ModuleResult[Any]:
    return ModuleResult(
        ok=False,
        status=ExecutionStatus.TIMEOUT,
        data=None,
        message=message,
        error_code="SCENARIO_STEP_TIMEOUT",
        duration_ms=int(time.time() * 1000) - started_ms,
    )


async def _sleep_retry_backoff(backoff_s: float) -> None:
    if backoff_s > 0:
        await asyncio.sleep(backoff_s)


def _next_backoff(
    backoff_s: float,
    max_backoff_s: float,
    policy: Any,
) -> float:
    if policy is None or backoff_s <= 0:
        return backoff_s
    return min(max_backoff_s, backoff_s * policy.multiplier)


def _hard_failure_retry_summary(
    attempt: int,
    status: ExecutionStatus,
    error_code: str | None,
    message: str | None,
    step: CompiledStep,
) -> tuple[dict[str, JsonValue], ...]:
    if _step_max_attempts(step) <= 1:
        return ()
    return (_failure_summary(attempt, status, error_code, message),)


def _step_max_attempts(step: CompiledStep) -> int:
    policy = step.retry_policy
    return max(1, policy.max_attempts if policy is not None else 1)


def _truncate_retry_message(message: str | None) -> str | None:
    if message is None or len(message) <= _RETRY_FAILURE_MESSAGE_LIMIT:
        return message
    return f"{message[:_RETRY_FAILURE_MESSAGE_LIMIT]}..."


def _phase_has_fatal_failure(
    results: list[StepResult],
    steps: tuple[CompiledStep, ...],
) -> bool:
    """Return True if any non-PASSED step in *results* is not marked continue_on_failure.

    Promotes ``continueOnFailure: true`` from "do not stop the phase" to
    "the step's failure does not poison the phase's terminal status" — which
    is the meaning callers expect when they intentionally tolerate a miss
    (e.g. exercising optional behaviour that depends on the loaded asset).
    """
    step_lookup = {s.id: s for s in steps}
    for r in results:
        if r.status == ExecutionStatus.PASSED:
            continue
        step = step_lookup.get(r.step_id)
        if step is None or not step.continue_on_failure:
            return True
    return False


def _skip_steps(*step_groups: tuple[CompiledStep, ...]) -> list[StepResult]:
    results = []
    for group in step_groups:
        for step in group:
            results.append(StepResult(
                step_id=step.id,
                phase=step.phase,
                status=ExecutionStatus.SKIPPED,
                message="Skipped due to prior phase failure",
                attempts=0,
                max_attempts=_step_max_attempts(step),
                continue_on_failure=step.continue_on_failure,
            ))
    return results


def _summarize_step_data(data: Any) -> dict[str, JsonValue]:
    """Return a bounded, JSON-safe diagnostic summary for scenario reports."""
    if is_dataclass(data) and not isinstance(data, type):
        raw = asdict(data)
    elif isinstance(data, dict):
        raw = data
    else:
        raw = {
            key: value
            for key, value in vars(data).items()
            if not key.startswith("_")
        } if hasattr(data, "__dict__") else {"value": data}

    summary: dict[str, JsonValue] = {}
    for key, value in raw.items():
        summary[str(key)] = _summarize_json_value(value)
    return summary


def _summarize_json_value(value: Any) -> JsonValue:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {
            str(key): _summarize_json_value(item)
            for key, item in list(value.items())[:20]
        }
    if isinstance(value, (list, tuple)):
        return _summarize_sequence(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {
            str(key): _summarize_json_value(item)
            for key, item in asdict(value).items()
        }
    return str(value)


def _summarize_sequence(value: list[Any] | tuple[Any, ...]) -> JsonValue:
    count = len(value)
    if count <= 12 and all(_is_json_primitive(item) for item in value):
        return [_summarize_json_value(item) for item in value]
    return {
        "count": count,
        "sample": [_summarize_json_value(item) for item in value[:3]],
    }


def _is_json_primitive(value: Any) -> bool:
    return isinstance(value, JsonPrimitive)
