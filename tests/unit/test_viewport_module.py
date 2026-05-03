"""Unit tests for ViewportModule."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.viewport import SSIMComparisonRequest, ViewportCaptureRequest
from tests.conftest import MockIsaacRestClient


@pytest.fixture
def mock_client():
    return MockIsaacRestClient()


@pytest.fixture
def viewport_module(mock_client):
    return ViewportModule(mock_client)


@pytest.fixture
def meta():
    return OperationMeta(request_id="test", module=ModuleName.VIEWPORT, started_at_epoch_ms=1000)


@pytest.mark.asyncio
async def test_capture_success(viewport_module, meta):
    result = await viewport_module.capture(meta, ViewportCaptureRequest())
    assert result.ok is True
    assert result.data is not None
    assert result.data.artifact_id == "test_img"
    assert "image" in result.artifacts


@pytest.mark.asyncio
async def test_ssim_pass(viewport_module, meta):
    result = await viewport_module.compare_ssim(
        meta,
        SSIMComparisonRequest(
            baseline_artifact_path="/tmp/a.png",
            candidate_artifact_path="/tmp/b.png",
            min_ssim=0.95,
        ),
    )
    assert result.ok is True
    assert result.data is not None
    assert result.data.score == 0.99


@pytest.mark.asyncio
async def test_ssim_fail(viewport_module, meta):
    viewport_module._client.responses["viewport_compare_ssim"] = {
        "score": 0.50,
        "passed": False,
    }
    result = await viewport_module.compare_ssim(
        meta,
        SSIMComparisonRequest(
            baseline_artifact_path="/tmp/a.png",
            candidate_artifact_path="/tmp/b.png",
            min_ssim=0.95,
        ),
    )
    assert result.ok is False
    assert result.data is not None
    assert result.data.score == 0.50
