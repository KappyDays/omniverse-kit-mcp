<!-- Parent: ../CLAUDE.md → docs/extension-basics.md -->
<!-- Scope: NavMesh Playground User Workflow + Manual QA Checklist -->

# NavMesh Playground — User Workflow + QA Checklist

This extension also works in **Isaac Sim standalone environment (without omniverse-kit-mcp)**.
All callbacks call Kit SDK directly (`omni.kit.commands` / `omni.usd` /
`isaacsim.replicator.agent.core` / `omni.anim.navigation.core` / `pxr.*` etc.) — `omni.mycompany.validation_api` depends 0.

## User Workflow (5 steps)

After opening the NavMesh Playground panel (`Window > NavMesh Playground` or automatically when Extension is enabled):

| # | Action | Result/Caution |
|---|------|-------------|
| 1 | Click **Stage > Load Warehouse** | Load Simple_Warehouse into `/World/Warehouse` (~17-20s S3) |
| 2 | **NavMesh > Bake** — Choose one of 3: | |
|   | • **Bake (Stage)** — Use existing NavMeshVolume | |
|   | • **Bake (New)** — Create a new 30m Include volume + bake. **For quick start** | |
|   | • **Bake (Only Warehouse)** — Bake by preserving the Transform/Scale/Type of stage volumes hand-authored by the user. The properties of each volume are output to the Status Log. **Recommended: Use after placing Include + Exclude directly on Stage** | |
| 3 | **Spawn > Type / Sit / Count settings → Spawn @ Random Walkable** | NavMesh Generate N random people or robots from walkable area |
|   | **Agents panel → Click “Set Cur” next to Start/Goal of each Agent** | Set the current location as Start (or Goal) coordinates. Goal can also be entered directly |
| 4 | **Sim Play (Space key or panel Sim Play button) — optional** | If not executed, Go in Step 5 automatically calls timeline.play(). If you play it in advance, the character runtime register becomes faster so the first Go response is immediate |
| 5 | **Click the “Go” button on each Agent** | People → Walk → Sit FSM. Robot → DifferentialController + Pure Pursuit. Stop with Stop, remove from stage with Remove |

## Edit NavMesh Volume directly (optional)

To exclude a specific area from walkable:
1. Right-click the Stage panel → Create > NavMeshVolume → “Exclude” type
2. Specify exclusion area location + size with xformOp:translate / scale
3. Re-click **Bake (New-Warehouse)** or **Bake (Stage)** on the panel → Apply both Include + Exclude

`Bake (New-Warehouse)` automatically recognizes all NavMeshVolumes in the stage — Include/Exclude ratio is displayed in status log.

## Manual QA Checklist

UI widget behavior can only be verified in the Kit GUI environment (outside the scope of pytest unit tests). Before user demonstration, check the following items by directly clicking the mouse:

### Basic scenario
- The [ ] panel appears in the `Window > NavMesh Playground` menu and opens when clicked.
- [ ] Click **Load Warehouse** → “Warehouse loaded: /World/Warehouse” in Status Log + Add `/World/Warehouse` Xform to Stage panel
- [ ] Click **Bake (New-Warehouse)** → Triangles label is 0 or more (Actual measurement: bake result of warehouse area ≥ 100)
- [ ] Click **Toggle Overlay** → Toggle cyan walkable area in viewport
- [ ] Spawn type=People, count=1, click **Spawn @ Random Walkable** → Add People-01 to Agents section + Show people in viewport
- [ ] Click Start `Set Cur` on the Agent panel → Start coordinate field is updated to the current location
- [ ] Click Goal `Set Cur` on the Agent panel → Same (separate coordinate input is also OK)
- [ ] **Sim Play** (or Space key) → Start timeline playback
- Click **Go** on [ ] Agent → Character starts walk animation in the direction of goal (automatically plays when timeline is not playing)
- [ ] Switch to Sit pose when reaching Goal (variant selected when spawning during SitIdle / SitTalk / SitReading)
- [ ] **Stop** → Character stops (state=Stopped)
- [ ] **Remove** → completely remove prim from stage (both parent + child SkelRoot)

### Robot Scenario
- [ ] Spawn type=Robot, count=1, **Spawn @ Random Walkable** → Add Robot-01 (NovaCarter or Jetbot) to the Robots section.
- [ ] Start/Goal `Set Cur` + **Go** → The robot runs with wheel rotation along the NavMesh path (smoothly without S-curve)
- [ ] When goal is reached or timeout, wheel velocity stops at 0
- [ ] Remove → Completely remove articulation from stage

### Multi-Agent
- Spawn People with [ ] count=3 → Place at 3 different walkable points
- Add Spawn Robot with [ ] count=2 → Simultaneous operation of 5 people and robots possible
- [ ] **Reset All Agents** → Batch cleaning of all agents

### Edit NavMesh Volume
- [ ] Add NavMeshVolume(Exclude) directly in the Stage panel + Re-click Bake (New-Warehouse) → “1 Include + 1 Exclude” is displayed in the Status Log + Random walkable points do not spawn in the Exclude area

## Known limitations- **Mismatched units carb.log_warn**: Character skin (cm) ↔ stage (m) unit difference may cause USD to output an informational warning once. Harmless — USD automatically compensates `xformOp:scale:unitsResolve=(100,100,100)`. negligible
- **Triangle count = 0 in Bake (New) UI button**: NavMesh itself is baked normally (sample_walkable_points verified operation). Due to a UI `iface.get_navmesh().get_triangle_count()` call timing issue, only the display value is 0. No effect on actual behavior.
- **Panel state="Walking" does not automatically switch to "Sitting" (intermittently)**: character runtime world transform polling sometimes misses very close arrivals. The character itself reaches the summit + Sit posture. Diagnosis bug unique to UI label
- **Only mouse clicks are stable (Claude MCP `extension_ui_invoke` is also possible, but the first call requires 1 second for layout settle)** — Automated testing is automatically handled by `validation_api/services/ui_service.py::ui_invoke`'s auto-show

## Related Boundaries

- Code path: `omni/mycompany/navmesh_playground/{ui_panel,people_controller,robot_controller,usd_loader,navmesh_sampler,agent_manager,extension}.py`
- Automatic verification scenario: `scenarios/smoke/navmesh_playground_e2e.yaml` (run with MCP scenario_validate)
- ext_ui_invoke usage guide: `docs/lessons-learned.md` L15