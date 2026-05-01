"""Pydantic models for Extension UI introspection / invocation (Phase D)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class UiInvokeRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    widget_path: str = Field(
        description="Widget path, e.g. 'Window Title//Frame/VStack[0]/Button[1]'."
    )
    action: Literal["click", "double_click", "type", "select", "check", "uncheck"] = Field(
        default="click",
        description="click|double_click|type|select|check|uncheck",
    )
    value: Any = Field(
        default=None,
        description="Text for 'type', integer index for 'select', ignored for click/check/uncheck.",
    )
