"""Exception hierarchy for the validation MCP server."""

from __future__ import annotations


class ValidationServerError(Exception):
    """Base exception for all validation server errors."""

    error_code: str = "VALIDATION_SERVER_ERROR"
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code
        if retryable is not None:
            self.retryable = retryable


# --- Transport / Remote ---


class TransportError(ValidationServerError):
    error_code = "TRANSPORT_ERROR"
    retryable = True


class RemoteServiceError(ValidationServerError):
    error_code = "REMOTE_SERVICE_ERROR"
    retryable = False


class RemoteTimeoutError(TransportError):
    error_code = "REMOTE_TIMEOUT"
    retryable = True


class RemoteProtocolError(RemoteServiceError):
    error_code = "REMOTE_PROTOCOL_ERROR"
    retryable = False


class CapabilityNotSupportedError(RemoteServiceError):
    """Raised when Extension returns HTTP 503 with error='*_stack_unavailable'.

    Indicates the capability (robot, character, navigation, ...) is not
    supported by the currently-active Kit app profile. Caller should treat
    this as "not supported for this session's profile", not as transient
    failure.
    """

    error_code = "CAPABILITY_NOT_SUPPORTED"
    retryable = False

    def __init__(self, detail: dict) -> None:
        message = detail.get("message", "Capability not supported for this app profile")
        super().__init__(message)
        self.detail = detail
        self.required_extensions = detail.get("required_extensions", [])
        self.capability = detail.get("error", "unknown")


# --- Stage ---


class StageError(ValidationServerError):
    error_code = "STAGE_ERROR"


class StageSnapshotError(StageError):
    error_code = "STAGE_SNAPSHOT_ERROR"


class PrimNotFoundError(StageError):
    error_code = "PRIM_NOT_FOUND"


class PropertyAssertionError(StageError):
    error_code = "PROPERTY_ASSERTION_FAILED"


# --- Viewport ---


class ViewportError(ValidationServerError):
    error_code = "VIEWPORT_ERROR"


class ViewportCaptureError(ViewportError):
    error_code = "VIEWPORT_CAPTURE_ERROR"


class ViewportComparisonError(ViewportError):
    error_code = "VIEWPORT_COMPARISON_FAILED"


# --- Lakehouse ---


class LakehouseError(ValidationServerError):
    error_code = "LAKEHOUSE_ERROR"


class LakehouseQueryError(LakehouseError):
    error_code = "LAKEHOUSE_QUERY_ERROR"


class LakehouseResponseDecodeError(LakehouseError):
    error_code = "LAKEHOUSE_RESPONSE_DECODE_ERROR"


# --- Extension ---


class ExtensionError(ValidationServerError):
    error_code = "EXTENSION_ERROR"


class ExtensionBusyError(ExtensionError):
    error_code = "EXTENSION_BUSY"
    retryable = True


class ExtensionTriggerError(ExtensionError):
    error_code = "EXTENSION_TRIGGER_ERROR"


class ExtensionResetError(ExtensionError):
    error_code = "EXTENSION_RESET_ERROR"


# --- Scenario Engine ---


class ScenarioError(ValidationServerError):
    error_code = "SCENARIO_ERROR"


class ScenarioSchemaError(ScenarioError):
    error_code = "SCENARIO_SCHEMA_ERROR"


class ScenarioCompileError(ScenarioError):
    error_code = "SCENARIO_COMPILE_ERROR"


class StepExecutionError(ScenarioError):
    error_code = "STEP_EXECUTION_ERROR"


class StepTimeoutError(ScenarioError):
    error_code = "STEP_TIMEOUT"


class ScenarioTimeoutError(ScenarioError):
    error_code = "SCENARIO_TIMEOUT"


# --- Simulation ---


class SimulationError(ValidationServerError):
    error_code = "SIMULATION_ERROR"


class SimulationControlError(SimulationError):
    error_code = "SIMULATION_CONTROL_ERROR"


# --- Stage Write ---


class StageWriteError(StageError):
    error_code = "STAGE_WRITE_ERROR"


class StageLoadError(StageWriteError):
    error_code = "STAGE_LOAD_ERROR"


class StagePropertyError(StageWriteError):
    error_code = "STAGE_PROPERTY_ERROR"


class PrimCreateError(StageWriteError):
    error_code = "PRIM_CREATE_ERROR"


class PrimDeleteError(StageWriteError):
    error_code = "PRIM_DELETE_ERROR"
