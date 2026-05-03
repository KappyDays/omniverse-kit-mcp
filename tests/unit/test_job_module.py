"""Unit tests for JobModule — async job status polling (Phase B)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.job_module import JobModule
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.job import JobStatus


def _meta() -> OperationMeta:
    return OperationMeta(request_id="test", module=ModuleName.JOB, started_at_epoch_ms=0)


@pytest.mark.asyncio
async def test_job_status_done():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = JobModule(client)
    result = await module.status(_meta(), "job_test_0001")

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, JobStatus)
    assert result.data.status == "done"
    assert result.data.progress == 1.0
    assert result.data.result is not None


@pytest.mark.asyncio
async def test_job_status_running_then_done():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    # First poll returns running, subsequent returns done
    client.responses["job_status"] = {
        "job_id": "j1",
        "status": "running",
        "progress": 0.5,
        "result": None,
        "error": None,
        "created_at_epoch_ms": 1000,
        "updated_at_epoch_ms": 1500,
    }
    module = JobModule(client)
    result = await module.status(_meta(), "j1")

    assert result.ok
    assert result.data.status == "running"
    assert result.data.progress == 0.5


@pytest.mark.asyncio
async def test_job_status_error_is_still_ok_result():
    """Job failure is a valid terminal state — JobModule returns ok=True with
    status='error' data so the runner can surface the error message."""
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["job_status"] = {
        "job_id": "j_err",
        "status": "error",
        "progress": 0.3,
        "result": None,
        "error": "RuntimeError: Prim not found",
        "created_at_epoch_ms": 1000,
        "updated_at_epoch_ms": 2000,
    }
    module = JobModule(client)
    result = await module.status(_meta(), "j_err")

    assert result.ok
    assert result.data.status == "error"
    assert "Prim not found" in (result.data.error or "")


@pytest.mark.asyncio
async def test_job_status_transport_error():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def job_status(self, job_id):  # type: ignore[override]
            raise ConnectionError("connection refused")

    module = JobModule(FailingClient())
    result = await module.status(_meta(), "j1")

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "JOB_STATUS_ERROR"


@pytest.mark.asyncio
async def test_job_cancel_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = JobModule(client)
    result = await module.cancel(_meta(), "j_cancel_me")

    assert result.ok
    assert isinstance(result.data, JobStatus)
    assert result.data.status == "canceled"
    cancel_calls = [c for c in client.calls if c[0] == "job_cancel"]
    assert len(cancel_calls) == 1
    assert cancel_calls[0][1]["job_id"] == "j_cancel_me"


@pytest.mark.asyncio
async def test_job_cancel_unknown_id_surfaces_404():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def job_cancel(self, job_id):  # type: ignore[override]
            raise KeyError(f"Unknown job_id: {job_id}")

    module = JobModule(FailingClient())
    result = await module.cancel(_meta(), "j_ghost")

    assert not result.ok
    assert result.error_code == "JOB_CANCEL_ERROR"
    assert "j_ghost" in (result.message or "")
