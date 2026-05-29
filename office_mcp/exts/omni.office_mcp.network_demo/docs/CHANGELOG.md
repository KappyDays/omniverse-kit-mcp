# Changelog — omni.office_mcp.network_demo

## [0.1.0]

### Added
- Initial Office-DataCenter Network Demo extension.
- `Load Scene` button + status `Label` UI window (English only — Kit 107 font atlas has no CJK glyphs).
- Deadlock-safe USD load of `office_datacenter.usd` (copies the `run_coroutine` + `CreatePayloadCommand(instanceable=True)` + `_wait_stage_loading` recipe).
- `net:role` / `net:order` customData discovery (path-agnostic).
- Viewport selection-based PC power-button trigger (active only while the timeline is playing — R2).
- Progress-wave transmission: cable emissive lerp + sequential server LED activation, driven by a per-frame update subscription.
- `/OfficeMcp/SelfTestResult` customData self-test stamp.
