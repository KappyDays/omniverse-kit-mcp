"""Tests for BaseAction + run_with_ui_feedback + auto-chain."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from omni.mycompany.isaac_tutorial.actions.base import (
    BaseAction, run_with_ui_feedback,
)


@pytest.mark.asyncio
async def test_run_with_ui_feedback_success():
    ui = MagicMock()

    async def _coro():
        return "done"

    result = await run_with_ui_feedback(ui, _coro(), label="test")
    assert result == "done"
    ui.set_busy.assert_any_call(True, label="test")
    ui.set_busy.assert_any_call(False)
    assert ui.status_label.text == "✓ done"


@pytest.mark.asyncio
async def test_run_with_ui_feedback_captures_exception():
    ui = MagicMock()

    async def _coro():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await run_with_ui_feedback(ui, _coro(), label="test")
    # busy reset on error
    ui.set_busy.assert_any_call(False)
    # notification posted
    ui.post_notification.assert_called()


@pytest.mark.asyncio
async def test_auto_chain_calls_prereq_when_not_done():
    called = []

    class _Act(BaseAction):
        async def run(self):
            called.append("main")

    prereq_ran = []

    async def _prereq():
        prereq_ran.append(True)

    act = _Act(ui=MagicMock(), state=MagicMock(), services=MagicMock())
    await act.run_with_prereqs([(_prereq, lambda: False)])
    assert prereq_ran == [True]
    assert called == ["main"]


@pytest.mark.asyncio
async def test_auto_chain_skips_prereq_when_done():
    prereq_ran = []

    async def _prereq():
        prereq_ran.append(True)

    class _Act(BaseAction):
        async def run(self):
            pass

    act = _Act(ui=MagicMock(), state=MagicMock(), services=MagicMock())
    await act.run_with_prereqs([(_prereq, lambda: True)])
    assert prereq_ran == []  # skipped
