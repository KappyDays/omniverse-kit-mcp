# Stage Compass HUD — Manual QA Checklist

Human-driven checklist for releasing a build of `omni.mycompany.stage_compass`.
Pair with the automated self-test prim assertions for end-to-end coverage.

## Activation

- [ ] `Window → Extensions` lists "Stage Compass HUD" with version `0.1.0`.
- [ ] Toggling it on creates two windows:
    - "Stage Compass" (radar HUD)
    - "Stage Compass — Settings"
- [ ] Toggling off destroys both windows; re-toggling does not produce
      "found 2 windows" warnings in the console.

## Radar render

- [ ] Background disc has a visible border ring; concentric range rings
      visible at 25 / 50 / 75 / 100% radius.
- [ ] Camera marker (green triangle) sits dead-centre.
- [ ] North arrow rod extends upward from the centre.
- [ ] N / E / S / W cardinal labels appear at the rim and rotate as the
      user changes heading (turning the camera).
- [ ] Coloured prim dots appear at expected projected positions.
- [ ] World-coords + heading label updates live as the camera moves.

## Filters

- [ ] Show All / Hide All / Geometry Only buttons toggle dot
      visibility correctly.
- [ ] Individual checkbox toggles immediately reflect on the radar.

## Waypoints

- [ ] "Pin Camera Here" with a custom name appears in the waypoint list
      and as a flag glyph on the radar.
- [ ] Waypoints persist through `Save Stage` → re-open.
- [ ] "Go" button on a waypoint row teleports the camera to that floor
      position (altitude preserved).
- [ ] "X" deletes the row + flag.
- [ ] "Clear All" empties the list.

## Click-to-teleport

- [ ] Left-clicking inside the radar disc moves the active camera to
      the corresponding floor-plane point.
- [ ] Click outside the disc is ignored.
- [ ] Mouse wheel inside the disc zooms range without moving the camera.

## Self-test (programmatic)

```
extension_activate(omni.mycompany.stage_compass, reload=False)
# wait ~2 s
stage_assert_prim_exists(/Compass/SelfTestResult)
stage_assert_property(
    /Compass/SelfTestResult.scan_ok,     equals true
)
stage_assert_property(
    /Compass/SelfTestResult.teleport_ok, equals true
)
stage_assert_property(
    /Compass/SelfTestResult.waypoint_ok, equals true
)
```

## Cross-app

- [ ] Works on Isaac Sim 5.1 (`isaacsim.exp.full.kit`).
- [ ] Works on USD Composer (`kkr_usd_composer.kit`).
- [ ] Stage with `Y`-up axis: dot positions correct.
- [ ] Stage with `Z`-up axis: dot positions correct.

## Performance

- [ ] On `Simple_Warehouse/full_warehouse.usd` (~few-thousand prims) the
      HUD update tick stays under 50 ms.
- [ ] Wheel-zoom feels responsive (< 100 ms perceived latency).
