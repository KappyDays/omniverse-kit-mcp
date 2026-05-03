"""Base validation module with shared helpers."""

from __future__ import annotations

import time
import uuid

from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, ModuleResult, OperationMeta


def make_meta(
    module: ModuleName,
    *,
    scenario_id: str | None = None,
    step_id: str | None = None,
) -> OperationMeta:
    return OperationMeta(
        request_id=uuid.uuid4().hex[:12],
        scenario_id=scenario_id,
        step_id=step_id,
        module=module,
        started_at_epoch_ms=int(time.time() * 1000),
    )


def ok_result[T](data: T, *, started_ms: int, artifacts: dict[str, str] | None = None) -> ModuleResult[T]:
    return ModuleResult(
        ok=True,
        status=ExecutionStatus.PASSED,
        data=data,
        duration_ms=int(time.time() * 1000) - started_ms,
        artifacts=artifacts or {},
    )


def fail_result[T](
    message: str,
    *,
    started_ms: int,
    error_code: str = "ASSERTION_FAILED",
    data: T | None = None,
) -> ModuleResult[T]:
    return ModuleResult(
        ok=False,
        status=ExecutionStatus.FAILED,
        data=data,
        message=message,
        error_code=error_code,
        duration_ms=int(time.time() * 1000) - started_ms,
    )


def error_result[T](
    message: str,
    *,
    started_ms: int,
    error_code: str = "MODULE_ERROR",
    exc: BaseException | None = None,
) -> ModuleResult[T]:
    """Build an error ModuleResult.

    When `exc` is a `CapabilityNotSupportedError` (extension returned HTTP 503
    with *_stack_unavailable body), the error_code is forced to
    `CAPABILITY_NOT_SUPPORTED` regardless of the module-specific default —
    this gives Claude Code one stable signal for "this app profile does not
    support this capability" without every module hand-wiring an extra except
    branch.
    """
    if exc is not None:
        from omniverse_kit_mcp.exceptions import CapabilityNotSupportedError
        if isinstance(exc, CapabilityNotSupportedError):
            error_code = "CAPABILITY_NOT_SUPPORTED"
    return ModuleResult(
        ok=False,
        status=ExecutionStatus.ERROR,
        data=None,
        message=message,
        error_code=error_code,
        duration_ms=int(time.time() * 1000) - started_ms,
    )
